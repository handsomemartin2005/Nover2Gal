from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from typing import Any
from uuid import uuid4


AUTH_LOCK = threading.RLock()
PASSWORD_ITERATIONS = 310_000
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
DEFAULT_AUTH_DB_PATH = (
    Path("/var/lib/novel2gal/auth.sqlite3")
    if os.name != "nt"
    else Path(__file__).resolve().parents[3] / "data" / "auth.sqlite3"
)


def create_user(
    username: str,
    password: str,
    *,
    display_name: str = "",
    role: str = "user",
) -> dict[str, Any]:
    normalized = normalize_username(username)
    validate_password(password)
    clean_display_name = (display_name or username).strip()[:60]
    if role not in {"user", "admin"}:
        raise ValueError("Unsupported role")
    now = time.time()
    user_id = uuid4().hex
    with AUTH_LOCK, _database() as connection:
        try:
            connection.execute(
                """
                INSERT INTO users (
                    user_id, username, display_name, password_hash, role, status,
                    created_at, updated_at, last_login_at
                ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, 0)
                """,
                (user_id, normalized, clean_display_name, _hash_password(password), role, now, now),
            )
        except sqlite3.IntegrityError as exc:
            raise FileExistsError(normalized) from exc
    return get_user_by_id(user_id)


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    try:
        normalized = normalize_username(username)
    except ValueError:
        return None
    with AUTH_LOCK, _database() as connection:
        row = connection.execute("SELECT * FROM users WHERE username = ?", (normalized,)).fetchone()
        if not row or row["status"] != "active" or not _verify_password(password, row["password_hash"]):
            return None
        now = time.time()
        connection.execute(
            "UPDATE users SET last_login_at = ?, updated_at = ? WHERE user_id = ?",
            (now, now, row["user_id"]),
        )
    return get_user_by_id(str(row["user_id"]))


def create_session(user_id: str) -> tuple[str, float]:
    raw_token = secrets.token_urlsafe(48)
    token_hash = _token_hash(raw_token)
    now = time.time()
    expires_at = now + SESSION_TTL_SECONDS
    with AUTH_LOCK, _database() as connection:
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token_hash, user_id, now, expires_at),
        )
    return raw_token, expires_at


def get_session_user(raw_token: str | None) -> dict[str, Any] | None:
    if not raw_token:
        return None
    now = time.time()
    with AUTH_LOCK, _database() as connection:
        row = connection.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.user_id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ? AND users.status = 'active'
            """,
            (_token_hash(raw_token), now),
        ).fetchone()
    return _public_user(row) if row else None


def revoke_session(raw_token: str | None) -> None:
    if not raw_token:
        return
    with AUTH_LOCK, _database() as connection:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(raw_token),))


def revoke_user_sessions(user_id: str) -> None:
    with AUTH_LOCK, _database() as connection:
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def get_user_by_id(user_id: str) -> dict[str, Any]:
    with AUTH_LOCK, _database() as connection:
        row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        raise KeyError(user_id)
    return _public_user(row)


def get_user_by_username(username: str) -> dict[str, Any] | None:
    try:
        normalized = normalize_username(username)
    except ValueError:
        return None
    with AUTH_LOCK, _database() as connection:
        row = connection.execute("SELECT * FROM users WHERE username = ?", (normalized,)).fetchone()
    return _public_user(row) if row else None


def list_users() -> list[dict[str, Any]]:
    with AUTH_LOCK, _database() as connection:
        rows = connection.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    return [_public_user(row) for row in rows]


def update_user(
    user_id: str,
    *,
    display_name: str | None = None,
    role: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if display_name is not None:
        clean = display_name.strip()
        if not clean or len(clean) > 60:
            raise ValueError("Display name must contain 1 to 60 characters")
        updates["display_name"] = clean
    if role is not None:
        if role not in {"user", "admin"}:
            raise ValueError("Unsupported role")
        updates["role"] = role
    if status is not None:
        if status not in {"active", "suspended"}:
            raise ValueError("Unsupported status")
        updates["status"] = status
    if not updates:
        return get_user_by_id(user_id)
    updates["updated_at"] = time.time()
    clause = ", ".join(f"{key} = ?" for key in updates)
    with AUTH_LOCK, _database() as connection:
        cursor = connection.execute(
            f"UPDATE users SET {clause} WHERE user_id = ?",
            (*updates.values(), user_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(user_id)
    if status == "suspended":
        revoke_user_sessions(user_id)
    return get_user_by_id(user_id)


def change_password(user_id: str, current_password: str, new_password: str) -> None:
    validate_password(new_password)
    with AUTH_LOCK, _database() as connection:
        row = connection.execute("SELECT password_hash FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            raise KeyError(user_id)
        if not _verify_password(current_password, row["password_hash"]):
            raise PermissionError("Current password is incorrect")
        connection.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?",
            (_hash_password(new_password), time.time(), user_id),
        )
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def ensure_bootstrap_admin() -> dict[str, Any] | None:
    username = os.environ.get("NOVEL2GAL_ADMIN_USERNAME", "").strip()
    password = os.environ.get("NOVEL2GAL_ADMIN_PASSWORD", "")
    if not username or not password:
        return None
    existing = get_user_by_username(username)
    if existing:
        if existing["role"] != "admin" or existing["status"] != "active":
            return update_user(existing["user_id"], role="admin", status="active")
        return existing
    return create_user(username, password, display_name="站点管理员", role="admin")


def normalize_username(value: str) -> str:
    username = str(value or "").strip().casefold()
    if not 3 <= len(username) <= 32:
        raise ValueError("Username must contain 3 to 32 characters")
    if not all(char.isalnum() or char in {"_", "-", "."} for char in username):
        raise ValueError("Username may only contain letters, numbers, dot, hyphen, and underscore")
    return username


def validate_password(value: str) -> None:
    password = str(value or "")
    if not 8 <= len(password) <= 128:
        raise ValueError("Password must contain 8 to 128 characters")
    if password.isspace():
        raise ValueError("Password cannot contain only spaces")


def _db_path() -> Path:
    return Path(os.environ.get("AUTH_DB_PATH") or DEFAULT_AUTH_DB_PATH)


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            status TEXT NOT NULL DEFAULT 'active',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            last_login_at REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS sessions_user_id_idx ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS sessions_expires_at_idx ON sessions(expires_at);
        """
    )
    return connection


@contextmanager
def _database():
    connection = _connect()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "$".join(
        (
            "pbkdf2_sha256",
            str(PASSWORD_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_value, digest_value = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_value.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _public_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "user_id",
            "username",
            "display_name",
            "role",
            "status",
            "created_at",
            "updated_at",
            "last_login_at",
        )
    }

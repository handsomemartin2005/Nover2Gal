from __future__ import annotations

import json
import os
from pathlib import Path
import threading
from typing import Any


_INITIALIZED = False
_INIT_LOCK = threading.Lock()


def enabled() -> bool:
    return bool(os.environ.get("DATABASE_URL", "").strip())


def healthy() -> bool:
    if not enabled():
        return True
    try:
        with _connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)
    except Exception:
        return False


def initialize() -> None:
    global _INITIALIZED
    if not enabled():
        return
    if _INITIALIZED:
        return
    with _INIT_LOCK:
        if _INITIALIZED:
            return
        with _connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id CHAR(32) PRIMARY KEY,
                owner_id CHAR(32) NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at DOUBLE PRECISION NOT NULL,
                updated_at DOUBLE PRECISION NOT NULL,
                payload JSONB NOT NULL
            );
            CREATE INDEX IF NOT EXISTS projects_owner_updated_idx ON projects(owner_id, updated_at DESC);
            CREATE INDEX IF NOT EXISTS projects_updated_idx ON projects(updated_at DESC);
            """)
        _INITIALIZED = True


def get(project_id: str) -> dict[str, Any] | None:
    if not enabled():
        return None
    initialize()
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT payload FROM projects WHERE project_id = %s", (project_id,))
        row = cursor.fetchone()
    if not row:
        return None
    return row[0] if isinstance(row[0], dict) else json.loads(row[0])


def upsert(project_id: str, project: dict[str, Any]) -> None:
    initialize()
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO projects(project_id,owner_id,title,status,created_at,updated_at,payload)
               VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)
               ON CONFLICT(project_id) DO UPDATE SET owner_id=excluded.owner_id,title=excluded.title,
               status=excluded.status,updated_at=excluded.updated_at,payload=excluded.payload""",
            (project_id, str(project.get("owner_id") or ""), str(project.get("title") or "未命名企划"),
             str(project.get("status") or "draft"), float(project.get("created_at") or 0),
             float(project.get("updated_at") or 0), json.dumps(project, ensure_ascii=False)),
        )


def list_all(owner_id: str | None = None) -> list[dict[str, Any]]:
    if not enabled():
        return []
    initialize()
    with _connect() as connection, connection.cursor() as cursor:
        if owner_id is None:
            cursor.execute("SELECT payload FROM projects ORDER BY updated_at DESC")
        else:
            cursor.execute("SELECT payload FROM projects WHERE owner_id = %s ORDER BY updated_at DESC", (owner_id,))
        rows = cursor.fetchall()
    return [row[0] if isinstance(row[0], dict) else json.loads(row[0]) for row in rows]


def delete(project_id: str) -> bool:
    initialize()
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute("DELETE FROM projects WHERE project_id = %s", (project_id,))
        return cursor.rowcount > 0


def migrate_file_projects(store_dir: Path) -> int:
    if not enabled() or not store_dir.exists():
        return 0
    migrated = 0
    for path in store_dir.glob("*/project.json"):
        try:
            project = json.loads(path.read_text(encoding="utf-8"))
            project_id = str(project.get("project_id") or path.parent.name)
            if get(project_id):
                continue
            upsert(project_id, project)
            migrated += 1
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return migrated


def _connect():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required when DATABASE_URL is configured") from exc
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=10)

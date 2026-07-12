from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import time
from typing import Any
from urllib.parse import urlparse
import urllib.error
import urllib.request

from app.core.config import Settings


SERVICE_TYPES = {"text", "image", "tts"}
API_FORMATS = {
    "text": {"openai", "anthropic", "gemini"},
    "image": {"openai-images"},
    "tts": {"openai-audio"},
}
PROVIDER_PRESETS = {
    "text": [
        {"id": "deepseek", "name": "DeepSeek", "api_format": "openai", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
        {"id": "openai", "name": "OpenAI", "api_format": "openai", "base_url": "https://api.openai.com/v1", "model": "gpt-4.1-mini"},
        {"id": "qwen", "name": "阿里云百炼 / 通义千问", "api_format": "openai", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
        {"id": "siliconflow", "name": "SiliconFlow", "api_format": "openai", "base_url": "https://api.siliconflow.cn/v1", "model": "Qwen/Qwen3-8B"},
        {"id": "moonshot", "name": "Moonshot / Kimi", "api_format": "openai", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
        {"id": "anthropic", "name": "Anthropic Claude", "api_format": "anthropic", "base_url": "https://api.anthropic.com/v1", "model": "claude-sonnet-4-20250514"},
        {"id": "gemini", "name": "Google Gemini", "api_format": "gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta", "model": "gemini-2.5-flash"},
        {"id": "custom", "name": "自定义兼容接口", "api_format": "openai", "base_url": "", "model": ""},
    ],
    "image": [
        {"id": "openai", "name": "OpenAI Images", "api_format": "openai-images", "base_url": "https://api.openai.com/v1", "model": "gpt-image-1"},
        {"id": "glm", "name": "智谱 CogView", "api_format": "openai-images", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "cogview-4"},
        {"id": "siliconflow", "name": "SiliconFlow 生图", "api_format": "openai-images", "base_url": "https://api.siliconflow.cn/v1", "model": "black-forest-labs/FLUX.1-schnell"},
        {"id": "custom", "name": "自定义 OpenAI Images", "api_format": "openai-images", "base_url": "", "model": ""},
    ],
    "tts": [
        {"id": "openai", "name": "OpenAI TTS", "api_format": "openai-audio", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini-tts"},
        {"id": "custom", "name": "自定义 OpenAI Audio", "api_format": "openai-audio", "base_url": "", "model": ""},
    ],
}


def list_provider_presets() -> dict[str, Any]:
    return {"services": PROVIDER_PRESETS, "supported_formats": API_FORMATS}


def list_api_configs(user_id: str) -> list[dict[str, Any]]:
    with _database() as connection:
        rows = connection.execute("SELECT * FROM api_configs WHERE user_id = ? ORDER BY service_type", (user_id,)).fetchall()
    return [_public_config(row) for row in rows]


def get_api_config(user_id: str, service_type: str, *, reveal_secret: bool = False) -> dict[str, Any] | None:
    _validate_service(service_type)
    with _database() as connection:
        row = connection.execute(
            "SELECT * FROM api_configs WHERE user_id = ? AND service_type = ?", (user_id, service_type)
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    if reveal_secret:
        result["api_key"] = _decrypt_secret(str(row["api_key_encrypted"]))
        result["extra_headers"] = json.loads(row["extra_headers"] or "{}")
    return result if reveal_secret else _public_config(row)


def save_api_config(user_id: str, service_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    _validate_service(service_type)
    provider = str(payload.get("provider") or "custom").strip()[:40]
    api_format = str(payload.get("api_format") or "").strip()
    if api_format not in API_FORMATS[service_type]:
        raise ValueError(f"Unsupported {service_type} API format")
    base_url = _normalize_base_url(str(payload.get("base_url") or ""))
    model = str(payload.get("model") or "").strip()[:160]
    if not model:
        raise ValueError("Model is required")
    headers = payload.get("extra_headers") or {}
    if not isinstance(headers, dict) or len(headers) > 12:
        raise ValueError("extra_headers must be an object with at most 12 items")
    safe_headers = {str(k)[:80]: str(v)[:500] for k, v in headers.items() if str(k).lower() not in {"host", "content-length"}}
    existing = get_api_config(user_id, service_type, reveal_secret=True)
    api_key = str(payload.get("api_key") or "")
    if not api_key and existing:
        api_key = str(existing.get("api_key") or "")
    if not api_key:
        raise ValueError("API key is required")
    now = time.time()
    with _database() as connection:
        connection.execute(
            """
            INSERT INTO api_configs (user_id, service_type, provider, api_format, base_url, model,
                api_key_encrypted, extra_headers, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, service_type) DO UPDATE SET
                provider=excluded.provider, api_format=excluded.api_format, base_url=excluded.base_url,
                model=excluded.model, api_key_encrypted=excluded.api_key_encrypted,
                extra_headers=excluded.extra_headers, enabled=excluded.enabled, updated_at=excluded.updated_at
            """,
            (user_id, service_type, provider, api_format, base_url, model, _encrypt_secret(api_key),
             json.dumps(safe_headers, ensure_ascii=False), 1 if payload.get("enabled", True) else 0, now, now),
        )
        connection.commit()
    return get_api_config(user_id, service_type) or {}


def delete_api_config(user_id: str, service_type: str) -> None:
    _validate_service(service_type)
    with _database() as connection:
        connection.execute("DELETE FROM api_configs WHERE user_id = ? AND service_type = ?", (user_id, service_type))
        connection.commit()


def user_text_runtime(user_id: str) -> tuple[Settings, "UniversalTextClient | None"]:
    settings = Settings.from_env()
    config = get_api_config(user_id, "text", reveal_secret=True)
    if not config or not config.get("enabled"):
        return settings, None
    settings = replace(
        settings,
        llm_provider=str(config["provider"]), llm_base_url=str(config["base_url"]),
        llm_api_key=str(config["api_key"]), llm_model=str(config["model"]),
    )
    return settings, UniversalTextClient(user_id, config)


class UniversalTextClient:
    def __init__(self, user_id: str, config: dict[str, Any]):
        self.user_id = user_id
        self.config = config

    def chat(self, messages: list[dict[str, str]], json_output: bool = False) -> str:
        started = time.perf_counter()
        status = "success"
        tokens_in = sum(len(str(item.get("content", ""))) for item in messages) // 4
        tokens_out = 0
        try:
            fmt = self.config["api_format"]
            if fmt == "anthropic":
                data = self._anthropic(messages)
                text = data["content"][0]["text"]
                usage = data.get("usage", {})
                tokens_in = int(usage.get("input_tokens", tokens_in) or 0)
                tokens_out = int(usage.get("output_tokens", len(text) // 4) or 0)
            elif fmt == "gemini":
                data = self._gemini(messages)
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                usage = data.get("usageMetadata", {})
                tokens_in = int(usage.get("promptTokenCount", tokens_in) or 0)
                tokens_out = int(usage.get("candidatesTokenCount", len(text) // 4) or 0)
            else:
                data = self._openai(messages, json_output)
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                tokens_in = int(usage.get("prompt_tokens", tokens_in) or 0)
                tokens_out = int(usage.get("completion_tokens", len(text) // 4) or 0)
            return text
        except Exception:
            status = "failed"
            raise
        finally:
            record_usage(self.user_id, "text", str(self.config["provider"]), str(self.config["model"]),
                         status=status, tokens_input=tokens_in, tokens_output=tokens_out,
                         duration_ms=int((time.perf_counter() - started) * 1000))

    def _openai(self, messages: list[dict[str, str]], json_output: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": self.config["model"], "messages": messages, "temperature": 0.3}
        if json_output:
            payload["response_format"] = {"type": "json_object"}
        return _json_request(_endpoint(self.config["base_url"], "chat/completions"), payload, self.config)

    def _anthropic(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        system = "\n".join(item["content"] for item in messages if item.get("role") == "system")
        body = [item for item in messages if item.get("role") != "system"]
        payload = {"model": self.config["model"], "max_tokens": 4096, "messages": body}
        if system:
            payload["system"] = system
        headers = {"x-api-key": self.config["api_key"], "anthropic-version": "2023-06-01"}
        return _json_request(_endpoint(self.config["base_url"], "messages"), payload, self.config, headers, bearer=False)

    def _gemini(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        contents = [{"role": "model" if m.get("role") == "assistant" else "user", "parts": [{"text": m["content"]}]}
                    for m in messages]
        url = _endpoint(self.config["base_url"], f"models/{self.config['model']}:generateContent")
        joiner = "&" if "?" in url else "?"
        return _json_request(f"{url}{joiner}key={self.config['api_key']}", {"contents": contents}, self.config, bearer=False)


def generate_image(user_id: str, *, prompt: str, size: str, style: str, count: int = 1) -> dict[str, Any]:
    config = _required_config(user_id, "image")
    started = time.perf_counter()
    status = "success"
    try:
        payload = {"model": config["model"], "prompt": prompt, "size": size, "n": max(1, min(count, 4))}
        data = _json_request(_endpoint(config["base_url"], "images/generations"), payload, config)
        images = [{key: item[key] for key in ("url", "b64_json", "revised_prompt") if key in item} for item in data.get("data", [])]
        return {"provider": config["provider"], "model": config["model"], "style": style, "images": images}
    except Exception:
        status = "failed"
        raise
    finally:
        record_usage(user_id, "image", config["provider"], config["model"], status=status,
                     units=max(1, min(count, 4)), duration_ms=int((time.perf_counter() - started) * 1000))


def synthesize_speech(user_id: str, *, text: str, voice: str, response_format: str = "mp3") -> tuple[bytes, str]:
    config = _required_config(user_id, "tts")
    started = time.perf_counter()
    status = "success"
    try:
        payload = {"model": config["model"], "input": text, "voice": voice, "response_format": response_format}
        content = _bytes_request(_endpoint(config["base_url"], "audio/speech"), payload, config)
        return content, {"mp3": "audio/mpeg", "wav": "audio/wav", "opus": "audio/ogg"}.get(response_format, "application/octet-stream")
    except Exception:
        status = "failed"
        raise
    finally:
        record_usage(user_id, "tts", config["provider"], config["model"], status=status, characters=len(text),
                     duration_ms=int((time.perf_counter() - started) * 1000))


def record_usage(user_id: str, service_type: str, provider: str, model: str, *, status: str,
                 tokens_input: int = 0, tokens_output: int = 0, characters: int = 0,
                 units: int = 0, duration_ms: int = 0) -> None:
    with _database() as connection:
        connection.execute(
            "INSERT INTO api_usage (event_id,user_id,service_type,provider,model,status,tokens_input,tokens_output,characters,units,duration_ms,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (secrets.token_hex(16), user_id, service_type, provider, model, status, tokens_input, tokens_output, characters, units, duration_ms, time.time()),
        )
        connection.commit()


def usage_summary(*, user_id: str | None = None, days: int = 30, limit: int = 100) -> dict[str, Any]:
    cutoff = time.time() - max(1, min(days, 365)) * 86400
    where = "created_at >= ?"
    params: list[Any] = [cutoff]
    if user_id:
        where += " AND user_id = ?"
        params.append(user_id)
    with _database() as connection:
        totals = connection.execute(f"SELECT COUNT(*) calls, COALESCE(SUM(tokens_input),0) tokens_input, COALESCE(SUM(tokens_output),0) tokens_output, COALESCE(SUM(characters),0) characters, COALESCE(SUM(units),0) units, COALESCE(SUM(status='failed'),0) failures FROM api_usage WHERE {where}", params).fetchone()
        by_service = connection.execute(f"SELECT service_type, COUNT(*) calls, COALESCE(SUM(tokens_input+tokens_output),0) tokens, COALESCE(SUM(characters),0) characters, COALESCE(SUM(units),0) units FROM api_usage WHERE {where} GROUP BY service_type ORDER BY service_type", params).fetchall()
        events = connection.execute(f"SELECT * FROM api_usage WHERE {where} ORDER BY created_at DESC LIMIT ?", (*params, max(1, min(limit, 500)))).fetchall()
    return {"period_days": days, "totals": dict(totals), "by_service": [dict(row) for row in by_service],
            "events": [dict(row) for row in events]}


def _required_config(user_id: str, service_type: str) -> dict[str, Any]:
    config = get_api_config(user_id, service_type, reveal_secret=True)
    if not config or not config.get("enabled"):
        raise ValueError(f"Please configure and enable the {service_type} API first")
    return config


def _json_request(url: str, payload: dict[str, Any], config: dict[str, Any], extra_headers: dict[str, str] | None = None, bearer: bool = True) -> dict[str, Any]:
    raw = _request(url, payload, config, extra_headers, bearer)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("API returned an invalid JSON response") from exc


def _bytes_request(url: str, payload: dict[str, Any], config: dict[str, Any]) -> bytes:
    return _request(url, payload, config)


def _request(url: str, payload: dict[str, Any], config: dict[str, Any], extra_headers: dict[str, str] | None = None, bearer: bool = True) -> bytes:
    _assert_safe_remote_url(url)
    headers = {"Content-Type": "application/json", "Accept": "application/json", **config.get("extra_headers", {}), **(extra_headers or {})}
    if bearer:
        headers["Authorization"] = f"Bearer {config['api_key']}"
    request = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", errors="replace")
        raise RuntimeError(f"Upstream API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot connect to upstream API: {exc.reason}") from exc


def _endpoint(base_url: str, suffix: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/" + suffix) or base.endswith(suffix):
        return base
    return f"{base}/{suffix}"


def _normalize_base_url(value: str) -> str:
    url = value.strip().rstrip("/")
    _assert_safe_remote_url(url)
    return url


def _assert_safe_remote_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Base URL must be a valid HTTP(S) URL without embedded credentials")
    if parsed.scheme == "http" and os.environ.get("ALLOW_INSECURE_API_URLS", "").lower() not in {"1", "true", "yes"}:
        raise ValueError("API Base URL must use HTTPS")
    if os.environ.get("ALLOW_PRIVATE_API_URLS", "").lower() in {"1", "true", "yes"}:
        return
    host = parsed.hostname.casefold()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("Private or local API addresses are not allowed")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))}
    except socket.gaierror:
        addresses = set()
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("Private or local API addresses are not allowed")


def _validate_service(service_type: str) -> None:
    if service_type not in SERVICE_TYPES:
        raise ValueError("Unsupported service type")


def _db_path() -> Path:
    default = Path("/var/lib/novel2gal/auth.sqlite3") if os.name != "nt" else Path(__file__).resolve().parents[3] / "data" / "auth.sqlite3"
    return Path(os.environ.get("AUTH_DB_PATH") or default)


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS api_configs (
            user_id TEXT NOT NULL, service_type TEXT NOT NULL, provider TEXT NOT NULL,
            api_format TEXT NOT NULL, base_url TEXT NOT NULL, model TEXT NOT NULL,
            api_key_encrypted TEXT NOT NULL, extra_headers TEXT NOT NULL DEFAULT '{}', enabled INTEGER NOT NULL DEFAULT 1,
            created_at REAL NOT NULL, updated_at REAL NOT NULL, PRIMARY KEY(user_id, service_type)
        );
        CREATE TABLE IF NOT EXISTS api_usage (
            event_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, service_type TEXT NOT NULL,
            provider TEXT NOT NULL, model TEXT NOT NULL, status TEXT NOT NULL,
            tokens_input INTEGER NOT NULL DEFAULT 0, tokens_output INTEGER NOT NULL DEFAULT 0,
            characters INTEGER NOT NULL DEFAULT 0, units INTEGER NOT NULL DEFAULT 0,
            duration_ms INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS api_usage_user_created_idx ON api_usage(user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS api_usage_service_created_idx ON api_usage(service_type, created_at DESC);
    """)
    return connection


@contextmanager
def _database():
    connection = _connect()
    try:
        yield connection
    finally:
        connection.close()


def _public_config(row: sqlite3.Row) -> dict[str, Any]:
    return {"service_type": row["service_type"], "provider": row["provider"], "api_format": row["api_format"],
            "base_url": row["base_url"], "model": row["model"], "enabled": bool(row["enabled"]),
            "api_key_masked": "••••" + _decrypt_secret(str(row["api_key_encrypted"]))[-4:], "has_api_key": True,
            "updated_at": row["updated_at"]}


def _secret_key() -> bytes:
    configured = os.environ.get("API_CONFIG_SECRET", "")
    material = configured or f"novel2gal-local:{_db_path().resolve()}"
    return hashlib.sha256(material.encode("utf-8")).digest()


def _encrypt_secret(value: str) -> str:
    nonce = secrets.token_bytes(16)
    key = _secret_key()
    plain = value.encode("utf-8")
    stream = b"".join(hashlib.sha256(key + nonce + index.to_bytes(4, "big")).digest() for index in range((len(plain) + 31) // 32))
    cipher = bytes(a ^ b for a, b in zip(plain, stream))
    tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + tag + cipher).decode("ascii")


def _decrypt_secret(value: str) -> str:
    raw = base64.urlsafe_b64decode(value.encode("ascii"))
    nonce, tag, cipher = raw[:16], raw[16:48], raw[48:]
    key = _secret_key()
    if not hmac.compare_digest(tag, hmac.new(key, nonce + cipher, hashlib.sha256).digest()):
        raise ValueError("Stored API key cannot be decrypted; check API_CONFIG_SECRET")
    stream = b"".join(hashlib.sha256(key + nonce + index.to_bytes(4, "big")).digest() for index in range((len(cipher) + 31) // 32))
    return bytes(a ^ b for a, b in zip(cipher, stream)).decode("utf-8")

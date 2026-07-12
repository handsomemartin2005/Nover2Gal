from __future__ import annotations

import base64
import os
from pathlib import Path
import secrets
from typing import Any


def enabled() -> bool:
    return bool(os.environ.get("S3_BUCKET", "").strip())


def healthy() -> bool:
    if not enabled():
        return True
    try:
        _client().head_bucket(Bucket=os.environ["S3_BUCKET"])
        return True
    except Exception:
        return False


def put_bytes(content: bytes, *, content_type: str, category: str, extension: str) -> dict[str, str]:
    key = f"{category}/{secrets.token_hex(16)}.{extension.lstrip('.')}"
    if enabled():
        _client().put_object(Bucket=os.environ["S3_BUCKET"], Key=key, Body=content, ContentType=content_type)
    else:
        path = _local_root() / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return {"asset_key": key, "url": f"/api/media/assets/{key}"}


def get_bytes(key: str) -> tuple[bytes, str]:
    safe_key = _safe_key(key)
    if enabled():
        response = _client().get_object(Bucket=os.environ["S3_BUCKET"], Key=safe_key)
        return response["Body"].read(), response.get("ContentType") or "application/octet-stream"
    path = _local_root() / safe_key
    if not path.exists():
        raise KeyError(key)
    return path.read_bytes(), _content_type(path.suffix)


def persist_image_item(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("b64_json"):
        content = base64.b64decode(item["b64_json"])
        stored = put_bytes(content, content_type="image/png", category="images", extension="png")
        return {**stored, **({"revised_prompt": item["revised_prompt"]} if item.get("revised_prompt") else {})}
    if item.get("url"):
        import urllib.request
        from app.services.ai_gateway import _assert_safe_remote_url
        _assert_safe_remote_url(str(item["url"]))
        with urllib.request.urlopen(str(item["url"]), timeout=60) as response:
            content = response.read(25 * 1024 * 1024 + 1)
            content_type = response.headers.get_content_type()
        if len(content) > 25 * 1024 * 1024:
            raise ValueError("Generated image is too large")
        extension = "webp" if content_type == "image/webp" else "jpg" if content_type == "image/jpeg" else "png"
        return {**put_bytes(content, content_type=content_type, category="images", extension=extension),
                **({"revised_prompt": item["revised_prompt"]} if item.get("revised_prompt") else {})}
    return item


def _client():
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required when S3_BUCKET is configured") from exc
    return boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None,
                        aws_access_key_id=os.environ.get("S3_ACCESS_KEY_ID") or None,
                        aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY") or None,
                        region_name=os.environ.get("S3_REGION", "us-east-1"))


def ensure_bucket() -> None:
    if not enabled():
        return
    client = _client()
    try:
        client.head_bucket(Bucket=os.environ["S3_BUCKET"])
    except Exception:
        client.create_bucket(Bucket=os.environ["S3_BUCKET"])


def _local_root() -> Path:
    default = Path("/var/lib/novel2gal/media") if os.name != "nt" else Path(__file__).resolve().parents[3] / "data" / "media"
    return Path(os.environ.get("MEDIA_STORE_DIR") or default)


def _safe_key(key: str) -> str:
    value = key.replace("\\", "/").strip("/")
    if not value or ".." in value.split("/"):
        raise KeyError(key)
    return value


def _content_type(suffix: str) -> str:
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
            ".mp3": "audio/mpeg", ".wav": "audio/wav", ".opus": "audio/ogg"}.get(suffix.lower(), "application/octet-stream")

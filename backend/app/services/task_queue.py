from __future__ import annotations

import json
import os
import time
from typing import Any
from uuid import uuid4


QUEUE_KEY = "novel2gal:tasks"
PROCESSING_KEY = "novel2gal:tasks:processing"
JOB_TTL = 7 * 24 * 60 * 60


def enabled() -> bool:
    return bool(os.environ.get("REDIS_URL", "").strip())


def healthy() -> bool:
    try:
        return not enabled() or bool(_client().ping())
    except Exception:
        return False


def enqueue_pipeline(*, owner_id: str, title: str, text: str, pov_character: str,
                     max_scenes: int | None, llm_model: str | None) -> str:
    job_id = uuid4().hex
    now = time.time()
    job = {"job_id": job_id, "owner_id": owner_id, "title": title, "status": "queued",
           "created_at": now, "updated_at": now, "error": "", "result": None}
    client = _client()
    client.setex(_job_key(job_id), JOB_TTL, json.dumps(job, ensure_ascii=False))
    _enqueue(client, {"kind": "pipeline", "job_id": job_id, "owner_id": owner_id, "title": title,
                      "text": text, "pov_character": pov_character, "max_scenes": max_scenes,
                      "llm_model": llm_model})
    return job_id


def enqueue_project(*, project_id: str, owner_id: str) -> None:
    _enqueue(_client(), {"kind": "project", "project_id": project_id, "owner_id": owner_id})


def get_job(job_id: str) -> dict[str, Any] | None:
    raw = _client().get(_job_key(job_id))
    return json.loads(raw) if raw else None


def update_job(job_id: str, **updates: Any) -> None:
    client = _client()
    job = get_job(job_id)
    if not job:
        return
    job.update(updates)
    job["updated_at"] = time.time()
    client.setex(_job_key(job_id), JOB_TTL, json.dumps(job, ensure_ascii=False))


def pop_task(timeout: int = 5) -> dict[str, Any] | None:
    raw = _client().brpoplpush(QUEUE_KEY, PROCESSING_KEY, timeout=timeout)
    if not raw:
        return None
    try:
        task = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        task = {"kind": "invalid", "error": "Malformed queue payload"}
    task["_queue_raw"] = raw
    return task


def acknowledge(task: dict[str, Any]) -> None:
    raw = task.get("_queue_raw")
    if raw:
        _client().lrem(PROCESSING_KEY, 1, raw)


def requeue_processing() -> int:
    client = _client()
    moved = 0
    while True:
        raw = client.rpoplpush(PROCESSING_KEY, QUEUE_KEY)
        if not raw:
            return moved
        moved += 1


def _enqueue(client, payload: dict[str, Any]) -> None:
    client.lpush(QUEUE_KEY, json.dumps(payload, ensure_ascii=False))


def _job_key(job_id: str) -> str:
    return f"novel2gal:job:{job_id}"


def _client():
    try:
        import redis
    except ImportError as exc:
        raise RuntimeError("redis is required when REDIS_URL is configured") from exc
    return redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True, socket_timeout=10)

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import threading
import time
from typing import Any
from uuid import uuid4

from app.importers.document_importer import import_document_bytes
from app.parser.chapter_splitter import split_chapters
from app.schemas.story import to_api_payload
from app.services.novel_pipeline import run_pipeline


PROJECT_LOCK = threading.Lock()
DEFAULT_PROJECT_STORE_DIR = Path("/var/lib/novel2gal/projects") if os.name != "nt" else Path(__file__).resolve().parents[3] / "data" / "projects"
DEFAULT_MAX_CHAPTER_CHARS = 60_000
PROJECT_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
PROJECT_EDITABLE_FIELDS = {
    "title",
    "filename",
    "pov_character",
    "llm_model",
    "max_scenes",
    "status",
    "result",
    "ui_state",
    "current_scene_id",
}


def create_project(
    *,
    title: str,
    source_text: str = "",
    filename: str = "",
    pov_character: str = "",
    max_scenes: int | None = None,
    llm_model: str | None = None,
    result: dict[str, Any] | None = None,
    status: str = "draft",
) -> dict[str, Any]:
    project_id = uuid4().hex
    now = time.time()
    project = {
        "project_id": project_id,
        "title": title.strip() or "未命名企划",
        "filename": filename,
        "source_type": Path(filename).suffix.lstrip(".") or "text",
        "pov_character": pov_character,
        "llm_model": llm_model,
        "max_scenes": max_scenes,
        "status": status,
        "created_at": now,
        "updated_at": now,
        "last_saved_at": now,
        "total_chapters": 0,
        "completed_chapters": 0,
        "failed_chapters": 0,
        "current_chapter": "",
        "current_scene_id": "",
        "error": "",
        "chapters": [],
        "versions": [],
        "ui_state": {},
        "result": result,
    }
    _write_source(project_id, source_text)
    _write_project(project_id, project)
    return public_project_payload(project_id)


def create_project_from_upload(
    filename: str,
    content: bytes,
    *,
    title: str | None = None,
    pov_character: str = "",
    max_scenes: int | None = None,
    llm_model: str | None = None,
) -> dict[str, Any]:
    document = import_document_bytes(filename, content)
    chapters = split_chapters(document.text)
    project_id = uuid4().hex
    project_dir = _project_dir(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    source_path = project_dir / "source.txt"
    source_path.write_text(document.text, encoding="utf-8")
    now = time.time()
    project = {
        "project_id": project_id,
        "title": title or document.title,
        "filename": filename,
        "source_type": document.source_type,
        "pov_character": pov_character,
        "llm_model": llm_model,
        "max_scenes": max_scenes,
        "status": "queued",
        "created_at": now,
        "updated_at": now,
        "total_chapters": len(chapters),
        "completed_chapters": 0,
        "failed_chapters": 0,
        "current_chapter": "",
        "error": "",
        "chapters": [
            {
                "index": chapter.index,
                "title": chapter.title,
                "char_count": len(chapter.text),
                "status": "queued",
                "error": "",
            }
            for chapter in chapters
        ],
        "result": None,
    }
    _write_project(project_id, project)
    return public_project_payload(project_id)


def run_project(project_id: str) -> None:
    project = _read_project(project_id)
    if not project:
        return
    _update_project(project_id, status="running", current_chapter="")
    source_text = (_project_dir(project_id) / "source.txt").read_text(encoding="utf-8")
    chapters = split_chapters(source_text)
    max_chapter_chars = _env_int("PROJECT_MAX_CHAPTER_CHARS", DEFAULT_MAX_CHAPTER_CHARS)
    scene_budget = _normalize_scene_budget(project.get("max_scenes"))
    used_scenes = 0
    merged_result: dict[str, Any] | None = None
    renpy_parts: list[str] = []
    markdown_parts: list[str] = []
    adaptation_scenes: list[dict[str, Any]] = []
    consistency_reports: list[dict[str, Any]] = []
    source_scenes: list[dict[str, Any]] = []
    source_chunks: list[dict[str, Any]] = []

    for chapter in chapters:
        if scene_budget is not None and used_scenes >= scene_budget:
            _mark_chapter(project_id, chapter.index, "skipped")
            continue
        _mark_chapter(project_id, chapter.index, "running", current_chapter=chapter.title)
        chapter_budget = 1 if scene_budget is None else max(1, min(3, scene_budget - used_scenes))
        chapter_text = chapter.text[:max_chapter_chars].rstrip()
        try:
            result = run_pipeline(
                project["title"],
                chapter_text,
                str(project.get("pov_character") or ""),
                max_scenes=chapter_budget,
                llm_model=project.get("llm_model") or None,
            )
            payload = to_api_payload(result)
            chapter_source_scenes = payload.get("source_scenes", [])
            chapter_source_chunks = payload.get("source_chunks", [])
            chapter_adaptation_scenes = payload.get("adaptation_scenes", [])
            chapter_reports = payload.get("consistency_reports", [])
            used_scenes += payload["stats"]["adaptation_scenes"]
            if merged_result is None:
                merged_result = payload
                merged_result["chapters"] = []
                merged_result["source_scenes"] = []
                merged_result["source_chunks"] = []
                merged_result["adaptation_scenes"] = []
                merged_result["consistency_reports"] = []
                merged_result["exports"] = {"markdown": "", "renpy": ""}
            source_scenes.extend(chapter_source_scenes)
            source_chunks.extend(chapter_source_chunks)
            adaptation_scenes.extend(chapter_adaptation_scenes)
            consistency_reports.extend(chapter_reports)
            renpy_parts.append(payload.get("exports", {}).get("renpy", ""))
            markdown_parts.append(payload.get("exports", {}).get("markdown", ""))
            _mark_chapter(project_id, chapter.index, "done")
        except Exception as exc:
            _mark_chapter(project_id, chapter.index, "failed", error=str(exc))

    project = _read_project(project_id) or {}
    if merged_result is None:
        _update_project(project_id, status="failed", error="No chapter was generated.")
        return
    merged_result["chapters"] = project.get("chapters", [])
    merged_result["source_scenes"] = source_scenes
    merged_result["source_chunks"] = source_chunks
    merged_result["adaptation_scenes"] = adaptation_scenes
    merged_result["consistency_reports"] = consistency_reports
    merged_result["exports"] = {
        "markdown": "\n\n".join(part for part in markdown_parts if part),
        "renpy": "\n\n".join(part for part in renpy_parts if part),
    }
    merged_result["stats"].update(
        {
            "chapters": project.get("total_chapters", len(chapters)),
            "source_scenes": len(source_scenes),
            "source_chunks": len(source_chunks),
            "adaptation_scenes": len(adaptation_scenes),
        }
    )
    _update_project(project_id, status="done", current_chapter="", result=merged_result)


def public_project_payload(project_id: str) -> dict[str, Any]:
    project = _read_project(project_id)
    if not project:
        raise KeyError(project_id)
    payload = dict(project)
    source_path = _project_dir(project_id) / "source.txt"
    payload["source_text"] = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
    return payload


def list_projects() -> list[dict[str, Any]]:
    root = _store_dir()
    if not root.exists():
        return []
    projects = []
    for path in root.glob("*/project.json"):
        try:
            project = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        summary = {key: project.get(key) for key in [
            "project_id",
            "title",
            "filename",
            "pov_character",
            "llm_model",
            "max_scenes",
            "status",
            "created_at",
            "updated_at",
            "last_saved_at",
            "total_chapters",
            "completed_chapters",
            "failed_chapters",
            "current_scene_id",
        ]}
        result = project.get("result") or {}
        stats = result.get("stats") or {}
        summary["scene_count"] = stats.get("adaptation_scenes", 0)
        summary["progress"] = _project_progress(project)
        summary["has_result"] = bool(project.get("result"))
        summary["version_count"] = len(project.get("versions") or [])
        projects.append(summary)
    return sorted(projects, key=lambda item: item.get("updated_at") or 0, reverse=True)


def update_project(project_id: str, updates: dict[str, Any], *, version_note: str = "自动快照") -> dict[str, Any]:
    clean_updates = {key: value for key, value in updates.items() if key in PROJECT_EDITABLE_FIELDS}
    source_text = updates.get("source_text")
    with PROJECT_LOCK:
        project = _read_project_unlocked(project_id)
        if not project:
            raise KeyError(project_id)
        previous_result = project.get("result")
        next_result = clean_updates.get("result")
        if next_result is not None and previous_result and next_result != previous_result:
            versions = list(project.get("versions") or [])
            versions.append({
                "version_id": uuid4().hex,
                "created_at": time.time(),
                "note": version_note,
                "result": previous_result,
            })
            project["versions"] = versions[-12:]
        project.update(clean_updates)
        project["updated_at"] = time.time()
        project["last_saved_at"] = project["updated_at"]
        _write_project_unlocked(project_id, project)
        if isinstance(source_text, str):
            _write_source_unlocked(project_id, source_text)
    return public_project_payload(project_id)


def delete_project(project_id: str) -> None:
    project_dir = _project_dir(project_id)
    if not project_dir.exists():
        raise KeyError(project_id)
    with PROJECT_LOCK:
        shutil.rmtree(project_dir)


def duplicate_project(project_id: str) -> dict[str, Any]:
    source = public_project_payload(project_id)
    return create_project(
        title=f"{source.get('title') or '未命名企划'} · 副本",
        source_text=source.get("source_text") or "",
        filename=source.get("filename") or "",
        pov_character=source.get("pov_character") or "",
        max_scenes=source.get("max_scenes"),
        llm_model=source.get("llm_model"),
        result=source.get("result"),
        status="done" if source.get("result") else "draft",
    )


def list_project_versions(project_id: str) -> list[dict[str, Any]]:
    project = _read_project(project_id)
    if not project:
        raise KeyError(project_id)
    return [
        {key: version.get(key) for key in ("version_id", "created_at", "note")}
        for version in reversed(project.get("versions") or [])
    ]


def rollback_project_version(project_id: str, version_id: str) -> dict[str, Any]:
    project = _read_project(project_id)
    if not project:
        raise KeyError(project_id)
    version = next((item for item in project.get("versions") or [] if item.get("version_id") == version_id), None)
    if not version:
        raise KeyError(version_id)
    return update_project(project_id, {"result": version.get("result"), "status": "done"}, version_note="回滚前快照")


def publish_sample(project_id: str, sample_data: dict[str, Any]) -> dict[str, Any]:
    project = public_project_payload(project_id)
    sample_id = uuid4().hex
    now = time.time()
    sample = {
        "sample_id": sample_id,
        "project_id": project_id,
        "title": str(sample_data.get("title") or project.get("title") or "未命名样例").strip(),
        "description": str(sample_data.get("description") or ""),
        "category": str(sample_data.get("category") or "其他"),
        "cover": str(sample_data.get("cover") or ""),
        "visibility": "public" if sample_data.get("visibility") == "public" else "private",
        "allow_clone": bool(sample_data.get("allow_clone", True)),
        "include_source": bool(sample_data.get("include_source", False)),
        "include_script": bool(sample_data.get("include_script", True)),
        "created_at": now,
        "updated_at": now,
        "pov_character": project.get("pov_character") or "",
        "llm_model": project.get("llm_model"),
        "source_text": project.get("source_text") if sample_data.get("include_source") else "",
        "result": project.get("result") if sample_data.get("include_script", True) else None,
    }
    path = _sample_path(sample_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    return sample


def list_samples() -> list[dict[str, Any]]:
    root = _sample_store_dir()
    if not root.exists():
        return []
    samples = []
    for path in root.glob("*.json"):
        try:
            sample = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        payload = {key: sample.get(key) for key in (
            "sample_id", "title", "description", "category", "cover", "visibility",
            "allow_clone", "include_source", "include_script", "created_at", "updated_at",
            "pov_character", "llm_model",
        )}
        stats = (sample.get("result") or {}).get("stats") or {}
        payload["scene_count"] = stats.get("adaptation_scenes", 0)
        samples.append(payload)
    return sorted(samples, key=lambda item: item.get("updated_at") or 0, reverse=True)


def get_sample(sample_id: str) -> dict[str, Any]:
    path = _sample_path(sample_id)
    if not path.exists():
        raise KeyError(sample_id)
    return json.loads(path.read_text(encoding="utf-8"))


def clone_sample(sample_id: str) -> dict[str, Any]:
    sample = get_sample(sample_id)
    if not sample.get("allow_clone", False):
        raise PermissionError(sample_id)
    return create_project(
        title=f"{sample.get('title') or '样例'} · 改编",
        source_text=sample.get("source_text") or "",
        pov_character=sample.get("pov_character") or "",
        llm_model=sample.get("llm_model"),
        result=sample.get("result"),
        status="done" if sample.get("result") else "draft",
    )


def delete_sample(sample_id: str) -> None:
    path = _sample_path(sample_id)
    if not path.exists():
        raise KeyError(sample_id)
    path.unlink()


def _mark_chapter(
    project_id: str,
    chapter_index: int,
    status: str,
    *,
    current_chapter: str | None = None,
    error: str = "",
) -> None:
    with PROJECT_LOCK:
        project = _read_project_unlocked(project_id)
        if not project:
            return
        for chapter in project["chapters"]:
            if chapter["index"] == chapter_index:
                chapter["status"] = status
                chapter["error"] = error
                break
        project["completed_chapters"] = sum(1 for chapter in project["chapters"] if chapter["status"] == "done")
        project["failed_chapters"] = sum(1 for chapter in project["chapters"] if chapter["status"] == "failed")
        project["updated_at"] = time.time()
        if current_chapter is not None:
            project["current_chapter"] = current_chapter
        _write_project_unlocked(project_id, project)


def _update_project(project_id: str, **updates: Any) -> None:
    with PROJECT_LOCK:
        project = _read_project_unlocked(project_id)
        if not project:
            return
        project.update(updates)
        project["updated_at"] = time.time()
        _write_project_unlocked(project_id, project)


def _read_project(project_id: str) -> dict[str, Any] | None:
    with PROJECT_LOCK:
        return _read_project_unlocked(project_id)


def _read_project_unlocked(project_id: str) -> dict[str, Any] | None:
    path = _project_dir(project_id) / "project.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_project(project_id: str, project: dict[str, Any]) -> None:
    with PROJECT_LOCK:
        _write_project_unlocked(project_id, project)


def _write_project_unlocked(project_id: str, project: dict[str, Any]) -> None:
    path = _project_dir(project_id) / "project.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_source(project_id: str, source_text: str) -> None:
    with PROJECT_LOCK:
        _write_source_unlocked(project_id, source_text)


def _write_source_unlocked(project_id: str, source_text: str) -> None:
    path = _project_dir(project_id) / "source.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source_text, encoding="utf-8")


def _project_dir(project_id: str) -> Path:
    if not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise KeyError(project_id)
    return _store_dir() / project_id


def _store_dir() -> Path:
    return Path(os.environ.get("PROJECT_STORE_DIR") or DEFAULT_PROJECT_STORE_DIR)


def _sample_store_dir() -> Path:
    explicit = os.environ.get("SAMPLE_STORE_DIR")
    if explicit:
        return Path(explicit)
    project_override = os.environ.get("PROJECT_STORE_DIR")
    if project_override:
        return Path(project_override) / "_samples"
    return DEFAULT_PROJECT_STORE_DIR.parent / "samples"


def _sample_path(sample_id: str) -> Path:
    if not PROJECT_ID_PATTERN.fullmatch(sample_id):
        raise KeyError(sample_id)
    return _sample_store_dir() / f"{sample_id}.json"


def _project_progress(project: dict[str, Any]) -> int:
    if project.get("status") == "done":
        return 100
    total = int(project.get("total_chapters") or 0)
    completed = int(project.get("completed_chapters") or 0)
    if total:
        return max(0, min(99, round(completed / total * 100)))
    return 0


def _normalize_scene_budget(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default

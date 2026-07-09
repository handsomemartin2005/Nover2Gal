from __future__ import annotations

import json
import os
from pathlib import Path
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
    return project


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
        projects.append({key: project.get(key) for key in [
            "project_id",
            "title",
            "status",
            "created_at",
            "updated_at",
            "total_chapters",
            "completed_chapters",
            "failed_chapters",
        ]})
    return sorted(projects, key=lambda item: item.get("updated_at") or 0, reverse=True)


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


def _project_dir(project_id: str) -> Path:
    return _store_dir() / project_id


def _store_dir() -> Path:
    return Path(os.environ.get("PROJECT_STORE_DIR") or DEFAULT_PROJECT_STORE_DIR)


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

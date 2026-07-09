from __future__ import annotations

import os
from pathlib import Path
import threading
import time
from typing import Literal
from uuid import uuid4

import anyio
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.importers.document_importer import import_document_bytes
from app.core.config import Settings
from app.media.providers import build_image_generation_plan, build_tts_plan, provider_status
from app.services.project_queue import create_project_from_upload, list_projects, public_project_payload, run_project
from app.services.novel_pipeline import run_pipeline
from app.schemas.story import to_api_payload


class PipelineRunRequest(BaseModel):
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    pov_character: str = ""
    max_scenes: int | None = Field(default=None, ge=1)
    llm_model: Literal["deepseek-v4-pro", "deepseek-v4-flash"] | None = None


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1)
    scene_id: str = ""
    style: Literal["anime", "real"] = "anime"


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
    voice: str = "default"


app = FastAPI(title="Novel2Gal Backend", version="0.1.0")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SPA_ROUTES = {"create", "templates", "projects"}
DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
DEFAULT_MAX_PIPELINE_TEXT_CHARS = 1_200_000
DEFAULT_MAX_PIPELINE_PROCESS_CHARS = 120_000
PIPELINE_JOBS: dict[str, dict] = {}
PIPELINE_JOB_LOCK = threading.Lock()

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def frontend_index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/pipeline/run")
def run_pipeline_endpoint(request: PipelineRunRequest) -> dict:
    _validate_text_size(request.text)
    text = _prepare_pipeline_text(request.text)
    result = run_pipeline(
        request.title,
        text,
        request.pov_character,
        max_scenes=request.max_scenes,
        llm_model=request.llm_model,
    )
    return to_api_payload(result)


@app.post("/api/pipeline/run/jobs")
def run_pipeline_job_endpoint(request: PipelineRunRequest, background_tasks: BackgroundTasks) -> dict:
    _validate_text_size(request.text)
    text = _prepare_pipeline_text(request.text)
    job_id = _create_pipeline_job(title=request.title)
    background_tasks.add_task(
        _execute_pipeline_job,
        job_id,
        request.title,
        text,
        request.pov_character,
        request.max_scenes,
        request.llm_model,
    )
    return _job_public_payload(job_id)


@app.post("/api/pipeline/upload")
async def upload_pipeline_endpoint(
    pov_character: str = Form(""),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    max_scenes: int | None = Form(None),
    llm_model: str | None = Form(None),
) -> dict:
    content = await _read_upload_file(file)
    try:
        document = import_document_bytes(file.filename or "document", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _validate_text_size(document.text)
    text = _prepare_pipeline_text(document.text)
    result = await anyio.to_thread.run_sync(
        lambda: run_pipeline(
            title or document.title,
            text,
            pov_character,
            max_scenes=max_scenes,
            llm_model=_validate_upload_model(llm_model),
        )
    )
    return to_api_payload(result)


@app.post("/api/pipeline/upload/jobs")
async def upload_pipeline_job_endpoint(
    background_tasks: BackgroundTasks,
    pov_character: str = Form(""),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    max_scenes: int | None = Form(None),
    llm_model: str | None = Form(None),
) -> dict:
    content = await _read_upload_file(file)
    try:
        document = import_document_bytes(file.filename or "document", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _validate_text_size(document.text)
    text = _prepare_pipeline_text(document.text)
    normalized_model = _validate_upload_model(llm_model)
    job_id = _create_pipeline_job(title=title or document.title)
    background_tasks.add_task(
        _execute_pipeline_job,
        job_id,
        title or document.title,
        text,
        pov_character,
        max_scenes,
        normalized_model,
    )
    return _job_public_payload(job_id)


@app.get("/api/pipeline/jobs/{job_id}")
def pipeline_job_status_endpoint(job_id: str) -> dict:
    return _job_public_payload(job_id)


@app.post("/api/projects/upload")
async def upload_project_endpoint(
    background_tasks: BackgroundTasks,
    pov_character: str = Form(""),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    max_scenes: int | None = Form(None),
    llm_model: str | None = Form(None),
) -> dict:
    content = await _read_upload_file(file)
    try:
        project = create_project_from_upload(
            file.filename or "document",
            content,
            title=title,
            pov_character=pov_character,
            max_scenes=max_scenes,
            llm_model=_validate_upload_model(llm_model),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(run_project, project["project_id"])
    return project


@app.get("/api/projects")
def list_projects_endpoint() -> dict:
    return {"projects": list_projects()}


@app.get("/api/projects/{project_id}")
def project_status_endpoint(project_id: str) -> dict:
    try:
        return public_project_payload(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


def _validate_upload_model(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    if value not in {"deepseek-v4-pro", "deepseek-v4-flash"}:
        raise HTTPException(status_code=422, detail="Unsupported llm_model")
    return value


def _create_pipeline_job(title: str) -> str:
    job_id = uuid4().hex
    now = time.time()
    with PIPELINE_JOB_LOCK:
        _trim_pipeline_jobs()
        PIPELINE_JOBS[job_id] = {
            "job_id": job_id,
            "title": title,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "error": "",
            "result": None,
        }
    return job_id


def _execute_pipeline_job(
    job_id: str,
    title: str,
    text: str,
    pov_character: str,
    max_scenes: int | None,
    llm_model: str | None,
) -> None:
    _update_pipeline_job(job_id, status="running")
    try:
        result = run_pipeline(
            title,
            text,
            pov_character,
            max_scenes=max_scenes,
            llm_model=llm_model,
        )
        _update_pipeline_job(job_id, status="done", result=to_api_payload(result))
    except Exception as exc:
        _update_pipeline_job(job_id, status="failed", error=str(exc))


def _update_pipeline_job(
    job_id: str,
    *,
    status: str,
    result: dict | None = None,
    error: str = "",
) -> None:
    with PIPELINE_JOB_LOCK:
        job = PIPELINE_JOBS.get(job_id)
        if not job:
            return
        job["status"] = status
        job["updated_at"] = time.time()
        if result is not None:
            job["result"] = result
        if error:
            job["error"] = error


def _job_public_payload(job_id: str) -> dict:
    with PIPELINE_JOB_LOCK:
        job = PIPELINE_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Pipeline job not found")
        return {
            "job_id": job["job_id"],
            "title": job["title"],
            "status": job["status"],
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
            "error": job["error"],
            "result": job["result"],
        }


def _trim_pipeline_jobs(max_jobs: int = 20) -> None:
    if len(PIPELINE_JOBS) < max_jobs:
        return
    removable = sorted(PIPELINE_JOBS.values(), key=lambda item: item["updated_at"])
    for job in removable[: max(1, len(PIPELINE_JOBS) - max_jobs + 1)]:
        PIPELINE_JOBS.pop(job["job_id"], None)


async def _read_upload_file(file: UploadFile) -> bytes:
    max_bytes = _env_int("MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES)
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if max_bytes > 0 and total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Uploaded file is too large. Limit is {max_bytes} bytes.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _validate_text_size(text: str) -> None:
    max_chars = _env_int("MAX_PIPELINE_TEXT_CHARS", DEFAULT_MAX_PIPELINE_TEXT_CHARS)
    if max_chars > 0 and len(text) > max_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Novel text is too large for this server. Limit is {max_chars} characters.",
        )


def _prepare_pipeline_text(text: str) -> str:
    max_chars = _env_int("MAX_PIPELINE_PROCESS_CHARS", DEFAULT_MAX_PIPELINE_PROCESS_CHARS)
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip()


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@app.get("/api/media/providers")
def media_providers_endpoint() -> dict:
    return provider_status(Settings.from_env())


@app.post("/api/media/image/plan")
def image_generation_plan_endpoint(request: ImageGenerationRequest) -> dict:
    return build_image_generation_plan(
        prompt=request.prompt,
        scene_id=request.scene_id,
        style=request.style,
        settings=Settings.from_env(),
    )


@app.post("/api/media/tts/plan")
def tts_plan_endpoint(request: TTSRequest) -> dict:
    return build_tts_plan(text=request.text, voice=request.voice, settings=Settings.from_env())


@app.get("/{full_path:path}")
def frontend_spa_fallback(full_path: str) -> FileResponse:
    if full_path.startswith(("api/", "static/")):
        raise HTTPException(status_code=404, detail="Not found")
    if full_path.strip("/") not in SPA_ROUTES:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(FRONTEND_DIR / "index.html")

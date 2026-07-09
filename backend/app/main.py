from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import anyio
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.importers.document_importer import import_document_bytes
from app.core.config import Settings
from app.media.providers import build_image_generation_plan, build_tts_plan, provider_status
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
    result = run_pipeline(
        request.title,
        request.text,
        request.pov_character,
        max_scenes=request.max_scenes,
        llm_model=request.llm_model,
    )
    return to_api_payload(result)


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
    result = await anyio.to_thread.run_sync(
        lambda: run_pipeline(
            title or document.title,
            document.text,
            pov_character,
            max_scenes=max_scenes,
            llm_model=_validate_upload_model(llm_model),
        )
    )
    return to_api_payload(result)


def _validate_upload_model(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    if value not in {"deepseek-v4-pro", "deepseek-v4-flash"}:
        raise HTTPException(status_code=422, detail="Unsupported llm_model")
    return value


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

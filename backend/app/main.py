from __future__ import annotations

from pathlib import Path
from typing import Literal

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
    content = await file.read()
    document = import_document_bytes(file.filename or "document", content)
    result = run_pipeline(
        title or document.title,
        document.text,
        pov_character,
        max_scenes=max_scenes,
        llm_model=_validate_upload_model(llm_model),
    )
    return to_api_payload(result)


def _validate_upload_model(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    if value not in {"deepseek-v4-pro", "deepseek-v4-flash"}:
        raise HTTPException(status_code=422, detail="Unsupported llm_model")
    return value


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

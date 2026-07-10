from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
import threading
import time
from typing import Any, Literal
from uuid import uuid4

import anyio
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.importers.document_importer import import_document_bytes
from app.core.config import Settings
from app.media.providers import build_image_generation_plan, build_tts_plan, provider_status
from app.services.auth_store import (
    authenticate_user,
    change_password,
    create_session,
    create_user,
    ensure_bootstrap_admin,
    get_session_user,
    get_user_by_id,
    list_users,
    revoke_session,
    update_user,
)
from app.services.project_queue import (
    assign_project_owner,
    assign_sample_owner,
    claim_legacy_content,
    clone_sample,
    create_project,
    create_project_from_upload,
    delete_project,
    delete_sample,
    duplicate_project,
    get_sample,
    list_project_versions,
    list_projects,
    list_samples,
    project_owner_id,
    public_project_payload,
    publish_sample,
    rollback_project_version,
    run_project,
    sample_access,
    update_sample,
    update_project,
)
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


class ProjectCreateRequest(BaseModel):
    title: str = Field(default="未命名企划", max_length=160)
    source_text: str = ""
    filename: str = ""
    pov_character: str = Field(default="", max_length=120)
    max_scenes: int | None = Field(default=None, ge=1)
    llm_model: Literal["deepseek-v4-pro", "deepseek-v4-flash"] | None = None


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    filename: str | None = None
    source_text: str | None = None
    pov_character: str | None = Field(default=None, max_length=120)
    max_scenes: int | None = Field(default=None, ge=1)
    llm_model: Literal["deepseek-v4-pro", "deepseek-v4-flash"] | None = None
    status: Literal["draft", "queued", "running", "done", "failed", "cancelled"] | None = None
    result: dict[str, Any] | None = None
    ui_state: dict[str, Any] | None = None
    current_scene_id: str | None = None
    version_note: str = "自动快照"


class SamplePublishRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    category: str = Field(default="其他", max_length=80)
    cover: str = ""
    include_source: bool = False
    include_script: bool = True
    visibility: Literal["private", "public"] = "private"
    allow_clone: bool = True


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    display_name: str = Field(default="", max_length=60)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class SampleUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    category: str | None = Field(default=None, max_length=80)
    cover: str | None = None
    visibility: Literal["private", "public"] | None = None
    allow_clone: bool | None = None


class AdminUserUpdateRequest(BaseModel):
    role: Literal["user", "admin"] | None = None
    status: Literal["active", "suspended"] | None = None


class AdminSampleUpdateRequest(BaseModel):
    visibility: Literal["private", "public"]


class AdminOwnerUpdateRequest(BaseModel):
    owner_id: str = Field(min_length=32, max_length=32)


SESSION_COOKIE_NAME = "novel2gal_session"


@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    admin = ensure_bootstrap_admin()
    if admin and os.environ.get("NOVEL2GAL_CLAIM_LEGACY_TO_ADMIN", "").lower() in {"1", "true", "yes"}:
        claim_legacy_content(admin["user_id"])
    yield


app = FastAPI(title="Novel2Gal Backend", version="0.1.0", lifespan=app_lifespan)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SPA_ROUTES = {"create", "templates", "projects", "account", "admin"}
DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
DEFAULT_MAX_PIPELINE_TEXT_CHARS = 1_200_000
DEFAULT_MAX_PIPELINE_PROCESS_CHARS = 120_000
PIPELINE_JOBS: dict[str, dict] = {}
PIPELINE_JOB_LOCK = threading.Lock()
AUTH_ATTEMPTS: dict[str, list[float]] = {}
AUTH_ATTEMPT_LOCK = threading.Lock()
INDEX_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "X-Novel2Gal-Build": "20260710-auth6",
}

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def optional_user(request: Request) -> dict[str, Any] | None:
    return get_session_user(request.cookies.get(SESSION_COOKIE_NAME))


def require_user(user: dict[str, Any] | None = Depends(optional_user)) -> dict[str, Any]:
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def require_admin(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


@app.post("/api/auth/register", status_code=201)
def register_endpoint(payload: RegisterRequest, request: Request, response: Response) -> dict:
    _check_auth_rate_limit(request)
    try:
        user = create_user(
            payload.username,
            payload.password,
            display_name=payload.display_name,
        )
    except FileExistsError as exc:
        _record_auth_failure(request)
        raise HTTPException(status_code=409, detail="用户名已被使用") from exc
    except ValueError as exc:
        _record_auth_failure(request)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _clear_auth_failures(request)
    _start_user_session(response, request, user)
    return {"user": user}


@app.post("/api/auth/login")
def login_endpoint(payload: LoginRequest, request: Request, response: Response) -> dict:
    _check_auth_rate_limit(request)
    user = authenticate_user(payload.username, payload.password)
    if not user:
        _record_auth_failure(request)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    _clear_auth_failures(request)
    _start_user_session(response, request, user)
    return {"user": user}


@app.post("/api/auth/logout")
def logout_endpoint(request: Request, response: Response) -> dict:
    revoke_session(request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", samesite="lax")
    return {"logged_out": True}


@app.get("/api/auth/me")
def current_user_endpoint(user: dict[str, Any] | None = Depends(optional_user)) -> dict:
    return {"user": user}


@app.patch("/api/auth/profile")
def update_profile_endpoint(payload: ProfileUpdateRequest, user: dict[str, Any] = Depends(require_user)) -> dict:
    try:
        return {"user": update_user(user["user_id"], display_name=payload.display_name)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/auth/password")
def change_password_endpoint(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    user: dict[str, Any] = Depends(require_user),
) -> dict:
    try:
        change_password(user["user_id"], payload.current_password, payload.new_password)
    except PermissionError as exc:
        raise HTTPException(status_code=422, detail="当前密码不正确") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _start_user_session(response, request, user)
    return {"changed": True}


@app.get("/")
def frontend_index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html", headers=INDEX_CACHE_HEADERS)


@app.post("/api/pipeline/run")
def run_pipeline_endpoint(request: PipelineRunRequest, _user: dict[str, Any] = Depends(require_user)) -> dict:
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
def run_pipeline_job_endpoint(
    request: PipelineRunRequest,
    background_tasks: BackgroundTasks,
    user: dict[str, Any] = Depends(require_user),
) -> dict:
    _validate_text_size(request.text)
    text = _prepare_pipeline_text(request.text)
    job_id = _create_pipeline_job(title=request.title, owner_id=user["user_id"])
    background_tasks.add_task(
        _execute_pipeline_job,
        job_id,
        request.title,
        text,
        request.pov_character,
        request.max_scenes,
        request.llm_model,
    )
    return _job_public_payload(job_id, user["user_id"])


@app.post("/api/pipeline/upload")
async def upload_pipeline_endpoint(
    pov_character: str = Form(""),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    max_scenes: int | None = Form(None),
    llm_model: str | None = Form(None),
    _user: dict[str, Any] = Depends(require_user),
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
    user: dict[str, Any] = Depends(require_user),
) -> dict:
    content = await _read_upload_file(file)
    try:
        document = import_document_bytes(file.filename or "document", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _validate_text_size(document.text)
    text = _prepare_pipeline_text(document.text)
    normalized_model = _validate_upload_model(llm_model)
    job_id = _create_pipeline_job(title=title or document.title, owner_id=user["user_id"])
    background_tasks.add_task(
        _execute_pipeline_job,
        job_id,
        title or document.title,
        text,
        pov_character,
        max_scenes,
        normalized_model,
    )
    return _job_public_payload(job_id, user["user_id"])


@app.get("/api/pipeline/jobs/{job_id}")
def pipeline_job_status_endpoint(job_id: str, user: dict[str, Any] = Depends(require_user)) -> dict:
    return _job_public_payload(job_id, user["user_id"], is_admin=user.get("role") == "admin")


@app.post("/api/projects/upload")
async def upload_project_endpoint(
    background_tasks: BackgroundTasks,
    pov_character: str = Form(""),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    max_scenes: int | None = Form(None),
    llm_model: str | None = Form(None),
    user: dict[str, Any] = Depends(require_user),
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
            owner_id=user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(run_project, project["project_id"])
    return project


@app.get("/api/projects")
def list_projects_endpoint(user: dict[str, Any] = Depends(require_user)) -> dict:
    return {"projects": list_projects(owner_id=user["user_id"])}


@app.post("/api/projects")
def create_project_endpoint(request: ProjectCreateRequest, user: dict[str, Any] = Depends(require_user)) -> dict:
    _validate_text_size(request.source_text)
    return create_project(**request.model_dump(), owner_id=user["user_id"])


@app.get("/api/projects/{project_id}")
def project_status_endpoint(project_id: str, user: dict[str, Any] = Depends(require_user)) -> dict:
    _require_project_access(project_id, user)
    try:
        return public_project_payload(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@app.patch("/api/projects/{project_id}")
def update_project_endpoint(
    project_id: str,
    request: ProjectUpdateRequest,
    user: dict[str, Any] = Depends(require_user),
) -> dict:
    _require_project_access(project_id, user)
    updates = request.model_dump(exclude_unset=True)
    version_note = str(updates.pop("version_note", "自动快照"))
    if isinstance(updates.get("source_text"), str):
        _validate_text_size(updates["source_text"])
    try:
        return update_project(project_id, updates, version_note=version_note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@app.delete("/api/projects/{project_id}")
def delete_project_endpoint(project_id: str, user: dict[str, Any] = Depends(require_user)) -> dict:
    _require_project_access(project_id, user)
    try:
        delete_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    return {"deleted": True, "project_id": project_id}


@app.post("/api/projects/{project_id}/duplicate")
def duplicate_project_endpoint(project_id: str, user: dict[str, Any] = Depends(require_user)) -> dict:
    _require_project_access(project_id, user)
    try:
        return duplicate_project(project_id, owner_id=user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@app.get("/api/projects/{project_id}/versions")
def list_project_versions_endpoint(project_id: str, user: dict[str, Any] = Depends(require_user)) -> dict:
    _require_project_access(project_id, user)
    try:
        return {"versions": list_project_versions(project_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@app.post("/api/projects/{project_id}/versions/{version_id}/rollback")
def rollback_project_version_endpoint(
    project_id: str,
    version_id: str,
    user: dict[str, Any] = Depends(require_user),
) -> dict:
    _require_project_access(project_id, user)
    try:
        return rollback_project_version(project_id, version_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project or version not found") from exc


@app.post("/api/projects/{project_id}/samples")
def publish_sample_endpoint(
    project_id: str,
    request: SamplePublishRequest,
    user: dict[str, Any] = Depends(require_user),
) -> dict:
    _require_project_access(project_id, user)
    if request.visibility == "public" and request.include_source:
        raise HTTPException(status_code=422, detail="Public samples cannot include the full source text")
    try:
        return publish_sample(project_id, request.model_dump(), owner_id=user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@app.get("/api/samples")
def list_samples_endpoint(user: dict[str, Any] | None = Depends(optional_user)) -> dict:
    return {"samples": list_samples(viewer_id=user["user_id"] if user else None)}


@app.get("/api/samples/{sample_id}")
def get_sample_endpoint(sample_id: str, user: dict[str, Any] | None = Depends(optional_user)) -> dict:
    _require_sample_view(sample_id, user)
    try:
        return get_sample(sample_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Sample not found") from exc


@app.post("/api/samples/{sample_id}/clone")
def clone_sample_endpoint(sample_id: str, user: dict[str, Any] = Depends(require_user)) -> dict:
    _require_sample_view(sample_id, user)
    try:
        return clone_sample(sample_id, owner_id=user["user_id"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="This sample cannot be cloned") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Sample not found") from exc


@app.delete("/api/samples/{sample_id}")
def delete_sample_endpoint(sample_id: str, user: dict[str, Any] = Depends(require_user)) -> dict:
    _require_sample_manage(sample_id, user)
    try:
        delete_sample(sample_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Sample not found") from exc
    return {"deleted": True, "sample_id": sample_id}


@app.patch("/api/samples/{sample_id}")
def update_sample_endpoint(
    sample_id: str,
    payload: SampleUpdateRequest,
    user: dict[str, Any] = Depends(require_user),
) -> dict:
    _require_sample_manage(sample_id, user)
    updates = payload.model_dump(exclude_unset=True)
    try:
        return update_sample(sample_id, updates)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Sample not found") from exc


@app.get("/api/admin/overview")
def admin_overview_endpoint(_admin: dict[str, Any] = Depends(require_admin)) -> dict:
    projects = list_projects()
    samples = list_samples(include_all=True)
    users = list_users()
    return {
        "users": len(users),
        "active_users": sum(1 for user in users if user["status"] == "active"),
        "projects": len(projects),
        "unowned_projects": sum(1 for project in projects if not project.get("owner_id")),
        "samples": len(samples),
        "public_samples": sum(1 for sample in samples if sample.get("visibility") == "public"),
        "private_samples": sum(1 for sample in samples if sample.get("visibility") != "public"),
    }


@app.get("/api/admin/users")
def admin_users_endpoint(_admin: dict[str, Any] = Depends(require_admin)) -> dict:
    projects = list_projects()
    samples = list_samples(include_all=True)
    project_counts: dict[str, int] = {}
    sample_counts: dict[str, int] = {}
    for project in projects:
        owner_id = str(project.get("owner_id") or "")
        project_counts[owner_id] = project_counts.get(owner_id, 0) + 1
    for sample in samples:
        owner_id = str(sample.get("owner_id") or "")
        sample_counts[owner_id] = sample_counts.get(owner_id, 0) + 1
    users = []
    for user in list_users():
        users.append({
            **user,
            "project_count": project_counts.get(user["user_id"], 0),
            "sample_count": sample_counts.get(user["user_id"], 0),
        })
    return {"users": users}


@app.patch("/api/admin/users/{user_id}")
def admin_update_user_endpoint(
    user_id: str,
    payload: AdminUserUpdateRequest,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict:
    if user_id == admin["user_id"] and (payload.role == "user" or payload.status == "suspended"):
        raise HTTPException(status_code=422, detail="不能停用或降级当前管理员账号")
    try:
        return {"user": update_user(user_id, **payload.model_dump(exclude_unset=True))}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/admin/projects")
def admin_projects_endpoint(_admin: dict[str, Any] = Depends(require_admin)) -> dict:
    users = {user["user_id"]: user for user in list_users()}
    projects = []
    for project in list_projects():
        owner = users.get(str(project.get("owner_id") or ""))
        projects.append({
            **project,
            "owner_username": owner["username"] if owner else "未归属",
            "owner_display_name": owner["display_name"] if owner else "旧数据",
        })
    return {"projects": projects}


@app.patch("/api/admin/projects/{project_id}/owner")
def admin_assign_project_endpoint(
    project_id: str,
    payload: AdminOwnerUpdateRequest,
    _admin: dict[str, Any] = Depends(require_admin),
) -> dict:
    try:
        get_user_by_id(payload.owner_id)
        project = assign_project_owner(project_id, payload.owner_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project or user not found") from exc
    return {"project": project}


@app.delete("/api/admin/projects/{project_id}")
def admin_delete_project_endpoint(project_id: str, _admin: dict[str, Any] = Depends(require_admin)) -> dict:
    try:
        delete_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    return {"deleted": True, "project_id": project_id}


@app.get("/api/admin/samples")
def admin_samples_endpoint(_admin: dict[str, Any] = Depends(require_admin)) -> dict:
    users = {user["user_id"]: user for user in list_users()}
    samples = []
    for sample in list_samples(include_all=True):
        owner = users.get(str(sample.get("owner_id") or ""))
        samples.append({**sample, "owner_username": owner["username"] if owner else "未归属"})
    return {"samples": samples}


@app.patch("/api/admin/samples/{sample_id}")
def admin_update_sample_endpoint(
    sample_id: str,
    payload: AdminSampleUpdateRequest,
    _admin: dict[str, Any] = Depends(require_admin),
) -> dict:
    try:
        update_sample(sample_id, {"visibility": payload.visibility})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Sample not found") from exc
    summary = next(
        (sample for sample in list_samples(include_all=True) if sample.get("sample_id") == sample_id),
        None,
    )
    return {"sample": summary}


@app.patch("/api/admin/samples/{sample_id}/owner")
def admin_assign_sample_endpoint(
    sample_id: str,
    payload: AdminOwnerUpdateRequest,
    _admin: dict[str, Any] = Depends(require_admin),
) -> dict:
    try:
        get_user_by_id(payload.owner_id)
        sample = assign_sample_owner(sample_id, payload.owner_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Sample or user not found") from exc
    return {"sample": sample}


@app.delete("/api/admin/samples/{sample_id}")
def admin_delete_sample_endpoint(sample_id: str, _admin: dict[str, Any] = Depends(require_admin)) -> dict:
    try:
        delete_sample(sample_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Sample not found") from exc
    return {"deleted": True, "sample_id": sample_id}


def _require_project_access(project_id: str, user: dict[str, Any]) -> None:
    try:
        owner_id = project_owner_id(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    # The management APIs deliberately expose metadata only.  Even an
    # administrator must not use the regular project API to read a member's
    # private source text.
    if owner_id != user["user_id"]:
        raise HTTPException(status_code=404, detail="Project not found")


def _require_sample_view(sample_id: str, user: dict[str, Any] | None) -> None:
    try:
        access = sample_access(sample_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Sample not found") from exc
    if access["visibility"] == "public":
        return
    if user and access["owner_id"] == user["user_id"]:
        return
    raise HTTPException(status_code=404, detail="Sample not found")


def _require_sample_manage(sample_id: str, user: dict[str, Any]) -> None:
    try:
        access = sample_access(sample_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Sample not found") from exc
    if access["owner_id"] == user["user_id"]:
        return
    raise HTTPException(status_code=404, detail="Sample not found")


def _validate_upload_model(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    if value not in {"deepseek-v4-pro", "deepseek-v4-flash"}:
        raise HTTPException(status_code=422, detail="Unsupported llm_model")
    return value


def _create_pipeline_job(title: str, owner_id: str) -> str:
    job_id = uuid4().hex
    now = time.time()
    with PIPELINE_JOB_LOCK:
        _trim_pipeline_jobs()
        PIPELINE_JOBS[job_id] = {
            "job_id": job_id,
            "owner_id": owner_id,
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


def _job_public_payload(job_id: str, user_id: str, *, is_admin: bool = False) -> dict:
    with PIPELINE_JOB_LOCK:
        job = PIPELINE_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Pipeline job not found")
        if not is_admin and job.get("owner_id") != user_id:
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


def _start_user_session(response: Response, request: Request, user: dict[str, Any]) -> None:
    raw_token, _expires_at = create_session(user["user_id"])
    secure_override = os.environ.get("SESSION_COOKIE_SECURE", "").strip().lower()
    if secure_override:
        secure = secure_override in {"1", "true", "yes"}
    else:
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        secure = request.url.scheme == "https" or forwarded_proto == "https"
    response.set_cookie(
        SESSION_COOKIE_NAME,
        raw_token,
        max_age=30 * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _auth_rate_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def _check_auth_rate_limit(request: Request) -> None:
    key = _auth_rate_key(request)
    cutoff = time.time() - 10 * 60
    with AUTH_ATTEMPT_LOCK:
        attempts = [timestamp for timestamp in AUTH_ATTEMPTS.get(key, []) if timestamp > cutoff]
        AUTH_ATTEMPTS[key] = attempts
        if len(attempts) >= 8:
            raise HTTPException(status_code=429, detail="登录尝试过多，请稍后再试")


def _record_auth_failure(request: Request) -> None:
    key = _auth_rate_key(request)
    with AUTH_ATTEMPT_LOCK:
        AUTH_ATTEMPTS.setdefault(key, []).append(time.time())


def _clear_auth_failures(request: Request) -> None:
    with AUTH_ATTEMPT_LOCK:
        AUTH_ATTEMPTS.pop(_auth_rate_key(request), None)


@app.get("/api/media/providers")
def media_providers_endpoint(_user: dict[str, Any] = Depends(require_user)) -> dict:
    return provider_status(Settings.from_env())


@app.post("/api/media/image/plan")
def image_generation_plan_endpoint(
    request: ImageGenerationRequest,
    _user: dict[str, Any] = Depends(require_user),
) -> dict:
    return build_image_generation_plan(
        prompt=request.prompt,
        scene_id=request.scene_id,
        style=request.style,
        settings=Settings.from_env(),
    )


@app.post("/api/media/tts/plan")
def tts_plan_endpoint(request: TTSRequest, _user: dict[str, Any] = Depends(require_user)) -> dict:
    return build_tts_plan(text=request.text, voice=request.voice, settings=Settings.from_env())


@app.get("/{full_path:path}")
def frontend_spa_fallback(full_path: str) -> FileResponse:
    if full_path.startswith(("api/", "static/")):
        raise HTTPException(status_code=404, detail="Not found")
    if full_path.strip("/") not in SPA_ROUTES:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(FRONTEND_DIR / "index.html", headers=INDEX_CACHE_HEADERS)

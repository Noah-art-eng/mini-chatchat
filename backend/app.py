from fastapi import Depends, FastAPI, File, UploadFile, Form, HTTPException, Request, Response
from starlette.background import BackgroundTask
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
import json
import os
import asyncio
import queue
import sqlite3
import shutil
import tempfile
import threading
import uuid
import re
import time
from model_config import (
    get_openai_client,
    get_llm_provider,
    get_llm_base_url,
    get_deepseek_api_key,
    get_openai_api_key,
    get_default_chat_model,
    get_default_temperature,
    get_default_max_tokens,
    get_embedding_model_name
)
from services.document_loader import load_file
from services.kb_service import MiniKBService
from services.kb_import_export_service import (
    export_kb,
    import_kb
)
from services.mcp_adapter import (
    list_mcp_servers,
    list_mcp_tools,
    run_mcp_tool,
    shutdown_mcp_server,
)
from services.tools import list_all_tools, run_tool
from chat_service import (
    create_temp_kb_from_upload,
    run_local_kb_chat,
    run_temp_kb_chat,
    run_kb_chat
)
from agent_service import (
    decide_tool_call,
    get_available_tool_specs,
    run_agent,
    run_agent_multi_step_persisted,
    run_agent_planner_persisted,
    run_agent_planner_stream_persisted,
    run_agent_once,
    run_agent_persisted
)
from db import (
    init_db,
    create_default_kb,
    list_kbs,
    list_file_docs,
    create_kb,
    delete_file_record,
    delete_file_docs,
    delete_kb_record,
    delete_files_by_kb,
    delete_file_docs_by_kb,
    update_message_feedback,
    upsert_file_record,
    update_file_status,
    list_conversations,
    get_conversation,
    get_conversation_messages,
    update_conversation_title,
    delete_conversation,
    get_connection,
    user_owns_kb,
    create_email_user,
    get_user_auth_by_email,
    get_user_by_id,
    public_user_dict,
    get_user_preferences,
    upsert_user_preferences,
    update_user_account
)
from user_scope import get_user_kb_root, migrate_legacy_demo_files
from auth.config import get_access_token_expire_minutes
from auth.config import get_cors_origins
from auth.config import is_production_environment
from auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    get_request_user_id,
    require_permission,
)
from auth.jwt import create_access_token
from auth.models import CurrentUser
from auth.password import hash_password, verify_password
from auth.permissions import Permission, has_permission
from auth.session import (
    create_login_session,
    get_refresh_token_from_request,
    list_public_user_sessions,
    logout_all_sessions,
    logout_other_sessions,
    logout_refresh_session,
    refresh_login_session,
    revoke_user_session,
)
from auth.oauth import (
    complete_oauth_callback,
    create_oauth_authorization,
    oauth_error_redirect,
    oauth_success_redirect,
    public_provider_status,
    unlink_oauth_provider,
)
from auth.security import (
    check_auth_rate_limit,
    clear_auth_failures,
    record_auth_failure,
    validate_production_auth_config,
    verify_allowed_origin,
)
from observability import (
    configure_logging,
    get_runtime_metadata,
    log_json,
    new_request_id,
)


load_dotenv()
configure_logging()
validate_production_auth_config()

SUPPORTED_EXTS = [".txt", ".pdf", ".docx", ".md", ".csv"]
MAX_TOP_K = 20
MAX_RERANK_TOP_N = 20
SERVICE_NAME = "mini-chatchat"
SERVICE_VERSION = "1.0.0-rc.1"
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("MINI_CHATCHAT_DATA_ROOT", os.path.join(BACKEND_DIR, "data"))
UPLOADS_DIR = os.getenv(
    "MINI_CHATCHAT_UPLOADS_DIR",
    os.path.join(BACKEND_DIR, "uploads"),
)

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI()
init_db()
migrate_legacy_demo_files()
create_default_kb()
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_and_access_log(request: Request, call_next):
    """负责 request_id_and_access_log 的函数职责。"""
    started_at = time.perf_counter()
    request_id = request.headers.get("x-request-id") or new_request_id()
    request.state.request_id = request_id

    try:
        response = await call_next(request)
    except Exception:
        log_json(
            "request_error",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
        )
        raise

    response.headers["X-Request-ID"] = request_id
    log_json(
        "request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
    )
    return response

client = get_openai_client()
kb_service = MiniKBService()
current_kb_by_scope = {}

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
MAX_DISPLAY_NAME_LENGTH = 80


class ChatRequest(BaseModel):
    """负责 ChatRequest 的类职责。"""
    question: str
    conversation_id: int | None = None
    top_k: int = Field(default=3, ge=1, le=MAX_TOP_K)
    score_threshold: float = Field(default=0.8, ge=0)
    prompt_name: str = "default"
    return_direct: bool = False
    model: str = get_default_chat_model()
    temperature: float = get_default_temperature()
    max_tokens: int | None = get_default_max_tokens()
    stream: bool = False

class CreateKBRequest(BaseModel):
    """负责 CreateKBRequest 的类职责。"""
    kb_name: str

class SwitchKBRequest(BaseModel):
    """负责 SwitchKBRequest 的类职责。"""
    kb_name: str

class SearchDocsRequest(BaseModel):
    """负责 SearchDocsRequest 的类职责。"""
    query: str
    top_k: int = Field(default=3, ge=1, le=MAX_TOP_K)
    file_name: str | None = None

class ReindexFileRequest(BaseModel):
    """负责 ReindexFileRequest 的类职责。"""
    chunk_size: int = Field(default=300, gt=0)
    chunk_overlap: int = Field(default=50, ge=0)

class FileChatRequest(BaseModel):
    """负责 FileChatRequest 的类职责。"""
    query: str
    temp_kb_id: str
    top_k: int = Field(default=3, ge=1, le=MAX_TOP_K)
    score_threshold: float = Field(default=0.8, ge=0)
    prompt_name: str = "default"
    stream: bool = False

class KBChatRequest(BaseModel):
    """负责 KBChatRequest 的类职责。"""
    query: str
    mode: str = "local_kb"
    kb_name: str = "default"
    temp_kb_id: str | None = None
    top_k: int = Field(default=3, ge=1, le=MAX_TOP_K)
    score_threshold: float = Field(default=0.8, ge=0)
    prompt_name: str = "default"
    stream: bool = False
    model: str = get_default_chat_model()
    temperature: float = get_default_temperature()
    max_tokens: int | None = get_default_max_tokens()
    return_direct: bool = False
    conversation_id: int | None = None
    rerank: bool = False
    rerank_top_n: int = Field(default=3, ge=1, le=MAX_RERANK_TOP_N)
    file_name: str | None = None
    source: str | None = None
    metadata_filter: dict | None = None

class OpenAIChatCompletionRequest(BaseModel):
    """负责 OpenAIChatCompletionRequest 的类职责。"""
    model: str = get_default_chat_model()
    messages: list
    stream: bool = False
    temperature: float = get_default_temperature()
    max_tokens: int | None = get_default_max_tokens()
    extra_body: dict | None = None

class FeedbackRequest(BaseModel):
    """负责 FeedbackRequest 的类职责。"""
    message_id: int
    score: int
    reason: str | None = None

class ConversationUpdateRequest(BaseModel):
    """负责 ConversationUpdateRequest 的类职责。"""
    title: str

class ToolRunRequest(BaseModel):
    """负责 ToolRunRequest 的类职责。"""
    arguments: dict = {}

class AgentToolCallRequest(BaseModel):
    """负责 AgentToolCallRequest 的类职责。"""
    query: str
    kb_name: str | None = "default"
    tools: list[str] | None = None
    conversation_id: int | None = None
    max_steps: int = 3

class AuthEmailPasswordRequest(BaseModel):
    """负责 AuthEmailPasswordRequest 的类职责。"""
    email: str
    password: str
    display_name: str | None = None

class AuthPreferencesUpdateRequest(BaseModel):
    """负责 AuthPreferencesUpdateRequest 的类职责。"""
    language: str | None = None
    developer_mode: bool | None = None
    onboarding_completed: bool | None = None
    theme: str | None = None
    preferred_model: str | None = None

class AuthAccountUpdateRequest(BaseModel):
    """负责 AuthAccountUpdateRequest 的类职责。"""
    display_name: str | None = None

    class Config:
        """负责 Config 的类职责。"""
        extra = "forbid"

# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────


def get_configured_provider():
    """负责 get_configured_provider 的函数职责。"""
    if get_deepseek_api_key():
        return "deepseek"

    if get_openai_api_key():
        return "openai"

    return "none"


def normalize_email(email: str):
    """负责 normalize_email 的函数职责。"""
    return (email or "").strip().lower()


def validate_email_password(email: str, password: str):
    """负责 validate_email_password 的函数职责。"""
    normalized_email = normalize_email(email)

    if not EMAIL_PATTERN.match(normalized_email):
        raise HTTPException(status_code=400, detail="invalid email or password")

    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail="invalid email or password")

    return normalized_email


def validate_display_name(display_name: str | None):
    """负责 validate_display_name 的函数职责。"""
    value = (display_name or "").strip()

    if not value:
        raise HTTPException(status_code=400, detail="display name is required")

    if len(value) > MAX_DISPLAY_NAME_LENGTH:
        raise HTTPException(status_code=400, detail="display name is too long")

    return value


def build_token_response(user, request: Request, response: Response):
    """负责 build_token_response 的函数职责。"""
    token, expires_in, session_id = create_login_session(user, request, response)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "session_id": session_id,
        "user": public_user_dict(user),
    }


def get_scope_key(current_user: CurrentUser):
    """负责 get_scope_key 的函数职责。"""
    return "demo" if current_user.is_guest else f"user:{current_user.id}"


def get_scoped_user_id(current_user: CurrentUser):
    """负责 get_scoped_user_id 的函数职责。"""
    return get_request_user_id(current_user)


def get_current_kb_name(current_user: CurrentUser):
    """负责 get_current_kb_name 的函数职责。"""
    return current_kb_by_scope.get(get_scope_key(current_user), "default")


def set_current_kb_name(current_user: CurrentUser, kb_name: str):
    """负责 set_current_kb_name 的函数职责。"""
    current_kb_by_scope[get_scope_key(current_user)] = kb_name


def get_scoped_kb_service(
    current_user: CurrentUser,
    kb_name: str | None = None,
):
    """负责 get_scoped_kb_service 的函数职责。"""
    user_id = get_scoped_user_id(current_user)
    resolved_kb_name = kb_name or get_current_kb_name(current_user)
    return MiniKBService(resolved_kb_name, user_id=user_id)


def validate_chunk_settings(chunk_size: int, chunk_overlap: int) -> None:
    """在写入文件前拒绝无效分块配置，避免留下失败的上传记录。"""
    if chunk_overlap >= chunk_size:
        raise HTTPException(
            status_code=422,
            detail="chunk_overlap must be smaller than chunk_size",
        )


def process_uploaded_document(
    scoped_service,
    upload_path: str,
    txt_path: str,
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    """同步解析与重建工作；由上传接口放入线程池执行。"""
    text = load_file(upload_path)

    with open(txt_path, "w", encoding="utf-8") as file:
        file.write(text)

    scoped_service.chunk_size = chunk_size
    scoped_service.chunk_overlap = chunk_overlap
    scoped_service.rebuild_index()


def ensure_kb_owned_or_404(kb_name: str, current_user: CurrentUser):
    """负责 ensure_kb_owned_or_404 的函数职责。"""
    if not user_owns_kb(kb_name, user_id=get_scoped_user_id(current_user)):
        raise HTTPException(status_code=404, detail="knowledge base not found")


def public_current_user(current_user: CurrentUser):
    """负责 public_current_user 的函数职责。"""
    if current_user.is_guest:
        return {
            "id": "guest",
            "email": None,
            "display_name": "Guest",
            "avatar_url": None,
            "auth_provider": "guest",
            "is_guest": True,
            "is_active": True,
        }

    return public_user_dict(get_user_by_id(int(current_user.id)))


def current_session_id(current_user: CurrentUser):
    """负责 current_session_id 的函数职责。"""
    return (current_user.metadata or {}).get("session_id")


def check_database():
    """负责 check_database 的函数职责。"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        return "ok"
    except sqlite3.Error:
        return "error"


def build_dependency_checks():
    """负责 build_dependency_checks 的函数职责。"""
    provider = get_configured_provider()
    embedding_model = get_embedding_model_name()

    return {
        "database": check_database(),
        "data_dir": "ok" if os.path.isdir(DATA_DIR) else "error",
        "uploads_dir": "ok" if os.path.isdir(UPLOADS_DIR) else "error",
        "chat_provider": "ok" if provider != "none" else "error",
        "embedding_model": "ok" if embedding_model else "error",
    }


def get_runtime_stats():
    """负责 get_runtime_stats 的函数职责。"""
    stats = {
        "knowledge_bases": None,
        "documents": None,
        "conversations": None,
        "active_sessions": None,
    }

    try:
        conn = get_connection()
        cursor = conn.cursor()
        for key, query in (
            ("knowledge_bases", "SELECT COUNT(*) FROM knowledge_base"),
            ("documents", "SELECT COUNT(*) FROM knowledge_file"),
            ("conversations", "SELECT COUNT(*) FROM conversation"),
            (
                "active_sessions",
                "SELECT COUNT(*) FROM auth_sessions WHERE is_active = 1 AND revoked_at IS NULL",
            ),
        ):
            cursor.execute(query)
            stats[key] = cursor.fetchone()[0]
        conn.close()
    except sqlite3.Error:
        return stats

    return stats


def should_expose_health_details(current_user: CurrentUser):
    """负责 should_expose_health_details 的函数职责。"""
    if os.getenv("HEALTH_DEPS_PUBLIC_DETAILS", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return True

    if is_production_environment():
        return (
            not current_user.is_guest
            and has_permission(current_user, Permission.CAN_ENABLE_DEVELOPER_MODE)
        )

    return True


@app.get("/health")
def health():
    """负责 health 的函数职责。"""
    runtime = get_runtime_metadata()
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": runtime["version"],
        "provider": get_configured_provider(),
        "started_at": runtime["started_at"],
        "uptime_seconds": runtime["uptime_seconds"],
        "environment": runtime["environment"],
    }


@app.get("/health/deps")
def health_deps(
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 health_deps 的函数职责。"""
    checks = build_dependency_checks()
    status = (
        "ok"
        if all(value == "ok" for value in checks.values())
        else "degraded"
    )

    payload = {
        "status": status,
        "checks": checks,
    }

    if should_expose_health_details(current_user):
        payload.update({
            "runtime": get_runtime_metadata(),
            "models": {
                "provider": get_llm_provider(),
                "chat_model": get_default_chat_model(),
                "embedding_model": get_embedding_model_name(),
            },
            "stats": get_runtime_stats(),
        })

    return payload


@app.post("/auth/register")
def auth_register(
    payload: AuthEmailPasswordRequest,
    http_request: Request,
    response: Response,
):
    """负责 auth_register 的函数职责。"""
    verify_allowed_origin(http_request)
    email = validate_email_password(payload.email, payload.password)
    check_auth_rate_limit("register", http_request, email)

    if get_user_auth_by_email(email):
        record_auth_failure("register", http_request, email)
        raise HTTPException(status_code=400, detail="invalid email or password")

    user = create_email_user(
        email,
        hash_password(payload.password),
        display_name=(payload.display_name or email).strip() or email,
    )
    create_default_kb(user_id=user["id"])
    clear_auth_failures("register", http_request, email)

    return build_token_response(user, http_request, response)


@app.post("/auth/login")
def auth_login(
    payload: AuthEmailPasswordRequest,
    http_request: Request,
    response: Response,
):
    """负责 auth_login 的函数职责。"""
    verify_allowed_origin(http_request)
    email = normalize_email(payload.email)
    check_auth_rate_limit("login", http_request, email)
    user = get_user_auth_by_email(email)

    if (
        user is None
        or user.get("auth_provider") != "email"
        or not user.get("is_active")
        or not verify_password(payload.password, user.get("password_hash"))
    ):
        record_auth_failure("login", http_request, email)
        raise HTTPException(status_code=401, detail="invalid email or password")

    clear_auth_failures("login", http_request, email)
    return build_token_response(user, http_request, response)


@app.post("/auth/logout")
def auth_logout(request: Request, response: Response):
    """负责 auth_logout 的函数职责。"""
    verify_allowed_origin(request)
    logout_refresh_session(request, response)
    return {
        "message": "logged out"
    }


@app.post("/auth/logout-all")
def auth_logout_all(
    request: Request,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_logout_all 的函数职责。"""
    verify_allowed_origin(request)
    revoked = logout_all_sessions(int(current_user.id), response)
    return {
        "message": "logged out all sessions",
        "revoked_sessions": revoked,
    }


@app.post("/auth/refresh")
def auth_refresh(request: Request, response: Response):
    """负责 auth_refresh 的函数职责。"""
    verify_allowed_origin(request)
    check_auth_rate_limit("refresh", request, None)
    refresh_token = get_refresh_token_from_request(request)
    try:
        result = refresh_login_session(refresh_token, response)
    except HTTPException:
        record_auth_failure("refresh", request, None)
        raise

    clear_auth_failures("refresh", request, None)
    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
        "expires_in": result["expires_in"],
        "session_id": result["session_id"],
        "user": public_user_dict(result["user"]),
    }


@app.get("/auth/me")
def auth_me(current_user: CurrentUser = Depends(get_current_user_optional)):
    """负责 auth_me 的函数职责。"""
    return {
        "user": public_current_user(current_user),
        "authenticated": not current_user.is_guest,
    }


@app.get("/auth/preferences")
def auth_preferences(current_user: CurrentUser = Depends(get_current_user)):
    """负责 auth_preferences 的函数职责。"""
    preferences = get_user_preferences(int(current_user.id))
    return {
        "preferences": preferences
    }


@app.patch("/auth/preferences")
def auth_update_preferences(
    request: AuthPreferencesUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_update_preferences 的函数职责。"""
    current = get_user_preferences(int(current_user.id)) or {}
    preferences = upsert_user_preferences(
        int(current_user.id),
        language=(
            request.language
            if request.language is not None
            else current.get("language")
        ),
        developer_mode=(
            request.developer_mode
            if request.developer_mode is not None
            else bool(current.get("developer_mode", False))
        ),
        onboarding_completed=(
            request.onboarding_completed
            if request.onboarding_completed is not None
            else bool(current.get("onboarding_completed", False))
        ),
        theme=request.theme if request.theme is not None else current.get("theme", "light"),
        preferred_model=(
            request.preferred_model
            if request.preferred_model is not None
            else current.get("preferred_model")
        ),
    )
    return {
        "preferences": preferences
    }


@app.get("/auth/account")
def auth_account(current_user: CurrentUser = Depends(get_current_user)):
    """负责 auth_account 的函数职责。"""
    return {
        "user": public_current_user(current_user)
    }


@app.patch("/auth/account")
def auth_update_account(
    request: AuthAccountUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_update_account 的函数职责。"""
    display_name = validate_display_name(request.display_name)
    user = update_user_account(int(current_user.id), display_name)

    if not user:
        raise HTTPException(status_code=404, detail="account not found")

    return {
        "user": public_user_dict(user)
    }


@app.get("/auth/sessions")
def auth_sessions(current_user: CurrentUser = Depends(get_current_user)):
    """负责 auth_sessions 的函数职责。"""
    return {
        "sessions": list_public_user_sessions(
            int(current_user.id),
            current_session_id(current_user),
        )
    }


@app.delete("/auth/sessions/{session_id}")
def auth_revoke_session(
    session_id: str,
    request: Request,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_revoke_session 的函数职责。"""
    verify_allowed_origin(request)
    revoked = revoke_user_session(int(current_user.id), session_id)

    if not revoked:
        raise HTTPException(status_code=404, detail="session not found")

    if session_id == current_session_id(current_user):
        logout_refresh_session(request, response)

    return {
        "message": "session revoked",
        "revoked": True,
        "revoked_current": session_id == current_session_id(current_user),
    }


@app.post("/auth/logout-others")
def auth_logout_others(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_logout_others 的函数职责。"""
    verify_allowed_origin(request)
    session_id = current_session_id(current_user)

    if not session_id:
        raise HTTPException(status_code=401, detail="missing token session")

    revoked = logout_other_sessions(int(current_user.id), session_id)
    return {
        "message": "logged out other sessions",
        "revoked_sessions": revoked,
    }


@app.get("/auth/oauth/providers")
def auth_oauth_providers(
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 auth_oauth_providers 的函数职责。"""
    user_id = None if current_user.is_guest else int(current_user.id)
    return {
        "providers": public_provider_status(user_id)
    }


@app.get("/auth/oauth/{provider}")
def auth_oauth_start(provider: str):
    """负责 auth_oauth_start 的函数职责。"""
    authorization = create_oauth_authorization(provider, mode="login")
    return RedirectResponse(authorization["authorization_url"], status_code=302)


@app.get("/auth/oauth/{provider}/callback")
def auth_oauth_callback(
    provider: str,
    request: Request,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """负责 auth_oauth_callback 的函数职责。"""
    if error:
        return RedirectResponse(
            oauth_error_redirect("oauth authorization was cancelled"),
            status_code=302,
        )

    if not code:
        return RedirectResponse(
            oauth_error_redirect("oauth authorization code missing"),
            status_code=302,
        )

    try:
        result = complete_oauth_callback(provider, code, state, request, response)
    except HTTPException as exc:
        return RedirectResponse(
            oauth_error_redirect(str(exc.detail)),
            status_code=302,
        )

    redirect = RedirectResponse(
        oauth_success_redirect(result["mode"]),
        status_code=302,
    )
    for header in response.raw_headers:
        if header[0].lower() == b"set-cookie":
            redirect.raw_headers.append(header)
    return redirect


@app.post("/auth/oauth/link/{provider}")
def auth_oauth_link(
    provider: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_oauth_link 的函数职责。"""
    verify_allowed_origin(request)
    authorization = create_oauth_authorization(
        provider,
        mode="link",
        user_id=int(current_user.id),
    )
    return {
        "authorization_url": authorization["authorization_url"],
        "provider": provider,
    }


@app.delete("/auth/oauth/link/{provider}")
def auth_oauth_unlink(
    provider: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_oauth_unlink 的函数职责。"""
    verify_allowed_origin(request)
    unlinked = unlink_oauth_provider(int(current_user.id), provider)
    return {
        "message": "oauth account unlinked",
        "provider": provider,
        "unlinked": unlinked,
    }


@app.get("/agent/tools")
def get_agent_tools():
    """负责 get_agent_tools 的函数职责。"""
    return {
        "tools": list_all_tools()
    }


@app.post("/agent/tools/{tool_name}/run")
def run_agent_tool(
    tool_name: str,
    request: ToolRunRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 run_agent_tool 的函数职责。"""
    if tool_name in {"filesystem_readonly_read", "sqlite_readonly_query"}:
        require_permission(
            current_user,
            (
                Permission.CAN_USE_FILESYSTEM
                if tool_name == "filesystem_readonly_read"
                else Permission.CAN_USE_SQLITE
            ),
        )

    arguments = dict(request.arguments or {})
    if tool_name == "kb_search":
        arguments["_user_id"] = get_scoped_user_id(current_user)

    result = run_tool(tool_name, arguments)
    return result.to_dict()


@app.get("/agent/mcp/tools")
def get_agent_mcp_tools(current_user: CurrentUser = Depends(get_current_user_optional)):
    """负责 get_agent_mcp_tools 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_MCP)
    return {
        "tools": list_mcp_tools(),
        "enabled": True,
        "provider": "mcp",
    }


@app.get("/agent/mcp/servers")
def get_agent_mcp_servers(current_user: CurrentUser = Depends(get_current_user_optional)):
    """负责 get_agent_mcp_servers 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_MCP)
    return {
        "servers": list_mcp_servers(),
    }


@app.post("/agent/mcp/servers/{server_name}/shutdown")
def stop_agent_mcp_server(
    server_name: str,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 stop_agent_mcp_server 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_MCP)
    return {
        "server": shutdown_mcp_server(server_name),
    }


@app.post("/agent/mcp/tools/{tool_name}/run")
def run_agent_mcp_tool(
    tool_name: str,
    request: ToolRunRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 run_agent_mcp_tool 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_MCP)
    result = run_mcp_tool(tool_name, request.arguments)
    return result.to_dict()


@app.post("/agent/decide")
def agent_decide(
    request: AgentToolCallRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_decide 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    available_tools, error = get_available_tool_specs(request.tools)

    if error:
        return {
            "tool_call": None,
            "raw_model_output": "",
            "error": error,
        }

    return decide_tool_call(
        request.query,
        available_tools,
    )


@app.post("/agent/run_once")
def agent_run_once(
    request: AgentToolCallRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_run_once 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    return run_agent_once(
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
        user_id=get_scoped_user_id(current_user),
    )


@app.post("/agent/run")
async def agent_run(
    request: AgentToolCallRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_run 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    # Agent 内含同步 LLM/Tool 调用；单独线程避免占用 ASGI 请求处理路径。
    return await asyncio.to_thread(
        run_agent_persisted,
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
        conversation_id=request.conversation_id,
        user_id=get_scoped_user_id(current_user),
    )


@app.post("/agent/run_multi")
def agent_run_multi(
    request: AgentToolCallRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_run_multi 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    return run_agent_multi_step_persisted(
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
        max_steps=request.max_steps,
        conversation_id=request.conversation_id,
        user_id=get_scoped_user_id(current_user),
    )


@app.post("/agent/plan_run")
def agent_plan_run(
    request: AgentToolCallRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_plan_run 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    return run_agent_planner_persisted(
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
        max_steps=request.max_steps,
        conversation_id=request.conversation_id,
        user_id=get_scoped_user_id(current_user),
    )


def encode_sse(event):
    """负责 encode_sse 的函数职责。"""
    event_type = event.get("type", "message")
    payload = json.dumps(event, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


@app.post("/agent/plan_run_stream")
async def agent_plan_run_stream(
    request: AgentToolCallRequest,
    http_request: Request,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_plan_run_stream 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    events: queue.Queue = queue.Queue()
    stop_event = threading.Event()
    user_id = get_scoped_user_id(current_user)

    def put_event(event):
        """负责 put_event 的函数职责。"""
        events.put(event)

    def run_agent_worker():
        """负责 run_agent_worker 的函数职责。"""
        try:
            result = run_agent_planner_stream_persisted(
                request.query,
                kb_name=request.kb_name,
                tools=request.tools,
                max_steps=request.max_steps,
                conversation_id=request.conversation_id,
                event_sink=put_event,
                should_stop=stop_event.is_set,
                user_id=user_id,
            )
            events.put({
                "type": "done",
                "result": result,
            })
        except Exception as exc:
            events.put({
                "type": "error",
                "error": str(exc),
            })
        finally:
            events.put(None)

    async def event_stream():
        """负责 event_stream 的函数职责。"""
        worker = threading.Thread(target=run_agent_worker, daemon=True)
        worker.start()

        while True:
            if await http_request.is_disconnected():
                stop_event.set()
                break

            try:
                event = events.get(timeout=0.1)
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue

            if event is None:
                break

            yield encode_sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )


@app.post("/kb_chat")
def kb_chat(
    request: KBChatRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 kb_chat 的函数职责。"""
    result = run_kb_chat(
        request,
        client,
        user_id=get_scoped_user_id(current_user),
    )

    if isinstance(result, dict) and result.get("error") in {
        "knowledge base not found",
        "temp knowledge base not found",
        "conversation not found",
    }:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@app.get("/models")
def get_models():
    """负责 get_models 的函数职责。"""
    return {
        "chat": {
            "provider": get_llm_provider(),
            "default_model": get_default_chat_model(),
            "base_url": get_llm_base_url(),
            "temperature": get_default_temperature(),
            "max_tokens": get_default_max_tokens()
        },
        "embedding": {
            "default_model": get_embedding_model_name()
        }
    }

def get_last_user_message(messages):
    """负责 get_last_user_message 的函数职责。"""
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")

    return ""


def build_kb_chat_request_from_openai(request: OpenAIChatCompletionRequest):
    """负责 build_kb_chat_request_from_openai 的函数职责。"""
    extra_body = request.extra_body or {}
    query = get_last_user_message(request.messages)

    try:
        return KBChatRequest(
            query=query,
            mode=extra_body.get("mode", "local_kb"),
            kb_name=extra_body.get("kb_name", "default"),
            temp_kb_id=extra_body.get("temp_kb_id"),
            top_k=extra_body.get("top_k", 3),
            score_threshold=extra_body.get("score_threshold", 0.8),
            prompt_name=extra_body.get("prompt_name", "default"),
            stream=request.stream,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            return_direct=extra_body.get("return_direct", False),
            conversation_id=extra_body.get("conversation_id"),
            rerank=extra_body.get("rerank", False),
            rerank_top_n=extra_body.get("rerank_top_n", 3),
            file_name=extra_body.get("file_name"),
            source=extra_body.get("source"),
            metadata_filter=extra_body.get("metadata_filter"),
        )
    except ValidationError as exc:
        # OpenAI 兼容入口手工构造请求模型，需显式保留 422 语义。
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


def build_openai_completion_response(completion_id, model, result):
    """负责 build_openai_completion_response 的函数职责。"""
    return {
        "id": completion_id,
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.get("answer", "")
                },
                "finish_reason": "stop"
            }
        ],
        "sources": result.get("sources", []),
        "assistant_message_id": result.get("assistant_message_id")
    }


def build_openai_streaming_response(completion_id, model, internal_response):
    """负责 build_openai_streaming_response 的函数职责。"""
    async def event_stream():
        """负责 event_stream 的函数职责。"""
        buffer = ""

        async for chunk in internal_response.body_iterator:
            if isinstance(chunk, bytes):
                buffer += chunk.decode("utf-8")
            else:
                buffer += str(chunk)

            events = buffer.split("\n\n")
            buffer = events.pop()

            for event_text in events:
                lines = [
                    line
                    for line in event_text.split("\n")
                    if line.startswith("data:")
                ]

                for line in lines:
                    payload = line.replace("data:", "", 1).strip()

                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    if event.get("type") == "token":
                        chunk_data = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "model": model,
                            "choices": [
                                {
                                    "delta": {
                                        "content": event.get("content", "")
                                    },
                                    "index": 0,
                                    "finish_reason": None
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"

                    if event.get("type") == "done":
                        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


def build_openai_static_streaming_response(completion_id, model, result):
    """负责 build_openai_static_streaming_response 的函数职责。"""
    async def event_stream():
        """负责 event_stream 的函数职责。"""
        content = result.get("answer", "")

        if content:
            chunk_data = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [
                    {
                        "delta": {
                            "content": content
                        },
                        "index": 0,
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


@app.post("/chat/completions")
def chat_completions(
    request: OpenAIChatCompletionRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 chat_completions 的函数职责。"""
    query = get_last_user_message(request.messages)

    if not query:
        return {
            "error": "messages must contain at least one user message"
        }

    completion_id = f"chatcmpl-{uuid.uuid4()}"
    kb_request = build_kb_chat_request_from_openai(request)
    result = run_kb_chat(
        kb_request,
        client,
        user_id=get_scoped_user_id(current_user),
    )

    if request.stream and isinstance(result, StreamingResponse):
        return build_openai_streaming_response(
            completion_id,
            request.model,
            result
        )

    if request.stream:
        return build_openai_static_streaming_response(
            completion_id,
            request.model,
            result
        )

    return build_openai_completion_response(
        completion_id,
        request.model,
        result
    )


@app.post("/chat/feedback")
def chat_feedback(
    request: FeedbackRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 chat_feedback 的函数职责。"""
    if request.score not in [1, -1]:
        return {
            "error": "score must be 1 or -1"
        }

    updated = update_message_feedback(
        request.message_id,
        request.score,
        request.reason,
        user_id=get_scoped_user_id(current_user),
    )

    if not updated:
        raise HTTPException(status_code=404, detail="message not found")

    return {
        "message": "feedback saved",
        "message_id": request.message_id,
        "feedback_score": request.score,
        "feedback_reason": request.reason
    }


@app.get("/conversations")
def get_conversations(current_user: CurrentUser = Depends(get_current_user_optional)):
    """负责 get_conversations 的函数职责。"""
    return {
        "conversations": list_conversations(user_id=get_scoped_user_id(current_user))
    }


@app.get("/conversations/{conversation_id}/messages")
def get_conversation_history(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 get_conversation_history 的函数职责。"""
    user_id = get_scoped_user_id(current_user)

    if get_conversation(conversation_id, user_id=user_id) is None:
        raise HTTPException(status_code=404, detail="conversation not found")

    return {
        "conversation_id": conversation_id,
        "messages": get_conversation_messages(
            conversation_id,
            user_id=user_id,
        )
    }


@app.patch("/conversations/{conversation_id}")
def update_conversation(
    conversation_id: int,
    request: ConversationUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 update_conversation 的函数职责。"""
    title = request.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="title cannot be empty"
        )

    conversation = update_conversation_title(
        conversation_id,
        title,
        user_id=get_scoped_user_id(current_user),
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="conversation not found"
        )

    return {
        "conversation": conversation
    }


@app.delete("/conversations/{conversation_id}")
def remove_conversation(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 remove_conversation 的函数职责。"""
    deleted = delete_conversation(
        conversation_id,
        user_id=get_scoped_user_id(current_user),
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="conversation not found"
        )

    return {
        "message": "conversation deleted",
        "conversation_id": conversation_id
    }


@app.post("/chat")
def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 chat 的函数职责。"""
    scoped_service = get_scoped_kb_service(current_user)
    return run_local_kb_chat(
        request,
        scoped_service,
        client,
        user_id=get_scoped_user_id(current_user),
    )

@app.post("/search_docs")
def search_docs(
    request: SearchDocsRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 search_docs 的函数职责。"""
    scoped_service = get_scoped_kb_service(current_user)
    results = scoped_service.search_docs(
        request.query,
        top_k=request.top_k,
        # 文件过滤必须在候选检索阶段应用，不能在全局 top_k 后再过滤。
        metadata_filter=(
            {"source": request.file_name}
            if request.file_name
            else None
        ),
    )

    return {
        "query": request.query,
        "results": results
    }

@app.post("/switch_kb")
def switch_kb(
    request: SwitchKBRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 switch_kb 的函数职责。"""
    global kb_service

    if not user_owns_kb(request.kb_name, user_id=get_scoped_user_id(current_user)):
        raise HTTPException(status_code=404, detail="knowledge base not found")

    set_current_kb_name(current_user, request.kb_name)

    if current_user.is_guest:
        kb_service = MiniKBService(request.kb_name)

    return {
        "current_kb": request.kb_name
    }

@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    override: bool = Form(True),
    chunk_size: int = Form(300, gt=0),
    chunk_overlap: int = Form(50, ge=0),
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 upload 的函数职责。"""
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    validate_chunk_settings(chunk_size, chunk_overlap)
    scoped_service = get_scoped_kb_service(current_user)
    user_id = get_scoped_user_id(current_user)
    content = await file.read()
    filename = file.filename or "uploaded.txt"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTS:
        return {"message": "Only .txt, .pdf, .docx, .md and .csv files are supported."}

    upload_path = os.path.join(
        scoped_service.upload_path,
        filename
    )
    txt_filename = f"{os.path.splitext(filename)[0]}.txt"
    txt_path = os.path.join(
        scoped_service.content_path,
        txt_filename
    )

    if (
        not override
        and (
            os.path.exists(upload_path)
            or os.path.exists(txt_path)
        )
    ):
        return {
            "error": f"{filename} already exists"
        }

    if override:
        delete_file_record(
            scoped_service.kb_name,
            txt_filename,
            user_id=user_id,
        )
        delete_file_docs(
            scoped_service.kb_name,
            txt_filename,
            user_id=user_id,
        )

    with open(upload_path, "wb") as f:
        f.write(content)

    upsert_file_record(
        scoped_service.kb_name,
        txt_filename,
        os.path.getsize(upload_path),
        0,
        status="uploaded",
        error=None,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        content_path=txt_path,
        upload_path=upload_path,
        user_id=user_id,
    )

    try:
        # 解析、embedding、FAISS/BM25 重建均可能耗时，不占用 async 事件循环。
        await asyncio.to_thread(
            process_uploaded_document,
            scoped_service,
            upload_path,
            txt_path,
            chunk_size,
            chunk_overlap,
        )

        txt_size = os.path.getsize(txt_path)

        scoped_service.save_file_record(
            os.path.basename(txt_path),
            txt_size,
            status="indexed",
            error=None,
            content_path=txt_path,
            upload_path=upload_path,
        )
    except Exception as exc:
        error_message = str(exc)
        update_file_status(
            scoped_service.kb_name,
            txt_filename,
            "failed",
            error_message,
            user_id=user_id,
        )
        return {
            "error": error_message,
            "message": f"{filename} upload failed"
        }

    return {"message": f"{filename} uploaded and indexed successfully"}


@app.post("/temp_upload")
async def temp_upload(
    file: UploadFile = File(...),
    chunk_size: int = Form(300, gt=0),
    chunk_overlap: int = Form(50, ge=0),
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 temp_upload 的函数职责。"""
    validate_chunk_settings(chunk_size, chunk_overlap)
    content = await file.read()
    return await asyncio.to_thread(
        create_temp_kb_from_upload,
        content,
        file.filename,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        user_id=get_scoped_user_id(current_user),
    )


@app.post("/file_chat")
def file_chat(
    request: FileChatRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 file_chat 的函数职责。"""
    return run_temp_kb_chat(
        request,
        client,
        user_id=get_scoped_user_id(current_user),
    )


@app.get("/documents")
def list_documents(current_user: CurrentUser = Depends(get_current_user_optional)):
    """负责 list_documents 的函数职责。"""
    scoped_service = get_scoped_kb_service(current_user)
    return {"files": scoped_service.list_documents()}


def is_safe_filename(filename: str):
    """负责 is_safe_filename 的函数职责。"""
    return ".." not in filename and "/" not in filename and "\\" not in filename


def get_content_txt_filename(filename: str):
    """负责 get_content_txt_filename 的函数职责。"""
    return (
        filename
        if filename.endswith(".txt")
        else f"{os.path.splitext(filename)[0]}.txt"
    )


def find_reindex_source_file(filename: str, scoped_service: MiniKBService):
    """负责 find_reindex_source_file 的函数职责。"""
    upload_path = os.path.join(
        scoped_service.upload_path,
        filename
    )

    if os.path.exists(upload_path):
        return upload_path

    content_filename = get_content_txt_filename(filename)
    content_path = os.path.join(
        scoped_service.content_path,
        content_filename
    )

    if os.path.exists(content_path):
        return content_path

    direct_content_path = os.path.join(
        scoped_service.content_path,
        filename
    )

    if os.path.exists(direct_content_path):
        return direct_content_path

    return None


@app.get("/documents/{filename}/download")
def download_document(
    filename: str,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 download_document 的函数职责。"""
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    scoped_service = get_scoped_kb_service(current_user)

    if not is_safe_filename(filename):
        raise HTTPException(status_code=400, detail="invalid filename")

    upload_path = os.path.join(
        scoped_service.upload_path,
        filename
    )

    txt_filename = (
        filename
        if filename.endswith(".txt")
        else f"{os.path.splitext(filename)[0]}.txt"
    )
    content_path = os.path.join(
        scoped_service.content_path,
        txt_filename
    )

    if os.path.exists(upload_path):
        return FileResponse(
            upload_path,
            filename=filename
        )

    if os.path.exists(content_path):
        return FileResponse(
            content_path,
            filename=txt_filename
        )

    raise HTTPException(status_code=404, detail="file not found")


@app.post("/documents/{filename}/reindex")
def reindex_document(
    filename: str,
    request: ReindexFileRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 reindex_document 的函数职责。"""
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    validate_chunk_settings(request.chunk_size, request.chunk_overlap)
    scoped_service = get_scoped_kb_service(current_user)
    user_id = get_scoped_user_id(current_user)

    if not is_safe_filename(filename):
        raise HTTPException(status_code=400, detail="invalid filename")

    source_path = find_reindex_source_file(filename, scoped_service)

    if source_path is None:
        raise HTTPException(status_code=404, detail="file not found")

    txt_filename = get_content_txt_filename(filename)
    txt_path = os.path.join(
        scoped_service.content_path,
        txt_filename
    )

    try:
        update_file_status(
            scoped_service.kb_name,
            txt_filename,
            "uploaded",
            None,
            user_id=user_id,
        )

        text = load_file(source_path)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        scoped_service.chunk_size = request.chunk_size
        scoped_service.chunk_overlap = request.chunk_overlap

        delete_file_docs(
            scoped_service.kb_name,
            txt_filename,
            user_id=user_id,
        )

        scoped_service.rebuild_index()

        scoped_service.save_file_record(
            txt_filename,
            os.path.getsize(txt_path),
            status="indexed",
            error=None,
            content_path=txt_path,
            upload_path=source_path,
        )

        return {
            "message": f"{filename} reindexed successfully",
            "filename": txt_filename
        }
    except Exception as exc:
        error_message = str(exc)
        update_file_status(
            scoped_service.kb_name,
            txt_filename,
            "failed",
            error_message,
            user_id=user_id,
        )
        return {
            "error": error_message,
            "message": f"{filename} reindex failed"
        }


@app.delete("/documents/{filename}")
def delete_document(
    filename: str,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 delete_document 的函数职责。"""
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    result = get_scoped_kb_service(current_user).delete_document(filename)

    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])

    return result

@app.get("/stats")
def get_stats(current_user: CurrentUser = Depends(get_current_user_optional)):
    """负责 get_stats 的函数职责。"""
    return get_scoped_kb_service(current_user).get_stats()

@app.post("/reload")
def reload_index(current_user: CurrentUser = Depends(get_current_user_optional)):
    """Manually trigger a full index rebuild without restarting the server."""
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    scoped_service = get_scoped_kb_service(current_user)
    scoped_service.rebuild_index()
    return scoped_service.get_stats()

@app.get("/knowledge_bases")
def get_knowledge_bases(current_user: CurrentUser = Depends(get_current_user_optional)):
    """负责 get_knowledge_bases 的函数职责。"""
    return {
        "knowledge_bases": list_kbs(user_id=get_scoped_user_id(current_user))
    }

@app.delete("/knowledge_bases/{kb_name}")
def delete_knowledge_base(
    kb_name: str,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 delete_knowledge_base 的函数职责。"""
    global kb_service
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    user_id = get_scoped_user_id(current_user)

    if kb_name == "default":
        return {
            "error": "default knowledge base cannot be deleted"
        }

    if ".." in kb_name or "/" in kb_name or "\\" in kb_name:
        raise HTTPException(status_code=400, detail="invalid knowledge base name")

    if not user_owns_kb(kb_name, user_id=user_id):
        raise HTTPException(status_code=404, detail="knowledge base not found")

    delete_file_docs_by_kb(kb_name, user_id=user_id)
    delete_files_by_kb(kb_name, user_id=user_id)
    delete_kb_record(kb_name, user_id=user_id)

    kb_path = os.path.join(get_user_kb_root(user_id), kb_name)

    if os.path.exists(kb_path):
        shutil.rmtree(kb_path)

    if current_user.is_guest and kb_service.kb_name == kb_name:
        kb_service = MiniKBService("default")

    if get_current_kb_name(current_user) == kb_name:
        set_current_kb_name(current_user, "default")

    return {
        "message": f"{kb_name} deleted"
    }

@app.get("/knowledge_bases/{kb_name}/export")
def export_knowledge_base(
    kb_name: str,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 export_knowledge_base 的函数职责。"""
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    ensure_kb_owned_or_404(kb_name, current_user)
    result = export_kb(kb_name, user_id=get_scoped_user_id(current_user))

    if result.get("error"):
        return result

    return FileResponse(
        result["path"],
        filename=result["filename"],
        media_type="application/zip",
        background=BackgroundTask(os.remove, result["path"])
    )

@app.post("/knowledge_bases/import")
async def import_knowledge_base(
    file: UploadFile = File(...),
    override: bool = Form(False),
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 import_knowledge_base 的函数职责。"""
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    filename = file.filename or ""

    if not filename.endswith(".zip"):
        return {
            "error": "only .zip files are supported"
        }

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
        temp_path = temp_file.name
        temp_file.write(await file.read())

    try:
        return import_kb(
            temp_path,
            override=override,
            user_id=get_scoped_user_id(current_user),
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/knowledge_bases")
def create_knowledge_base(
    request: CreateKBRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 create_knowledge_base 的函数职责。"""
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    user_id = get_scoped_user_id(current_user)

    kb_path = os.path.join(get_user_kb_root(user_id), request.kb_name)

    os.makedirs(
        os.path.join(kb_path, "content"),
        exist_ok=True
    )

    os.makedirs(
        os.path.join(kb_path, "uploads"),
        exist_ok=True
    )

    os.makedirs(
        os.path.join(kb_path, "vector_store"),
        exist_ok=True
    )

    create_kb(request.kb_name, user_id=user_id)

    return {
        "message": f"{request.kb_name} created"
    }

@app.post("/sync_files")
def sync_files(current_user: CurrentUser = Depends(get_current_user_optional)):
    """负责 sync_files 的函数职责。"""
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    scoped_service = get_scoped_kb_service(current_user)
    scoped_service.sync_files_to_db()
    return scoped_service.get_stats()

@app.get("/file_docs/{filename}")
def get_file_docs(
    filename: str,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 get_file_docs 的函数职责。"""
    scoped_service = get_scoped_kb_service(current_user)
    txt_filename = get_content_txt_filename(filename)
    documents = scoped_service.list_documents()
    if not any(
        item.get("filename") in {filename, txt_filename}
        for item in documents
    ):
        raise HTTPException(status_code=404, detail="file not found")

    return {
        "chunks": list_file_docs(
            scoped_service.kb_name,
            txt_filename,
            user_id=get_scoped_user_id(current_user),
        )
    }

@app.get("/chunk/{chunk_id}")
def get_chunk(
    chunk_id: int,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 get_chunk 的函数职责。"""
    chunk = get_scoped_kb_service(current_user).get_chunk_by_id(chunk_id)

    if chunk.get("error"):
        raise HTTPException(status_code=404, detail=chunk["error"])

    return chunk

from fastapi import Depends, FastAPI, File, UploadFile, Form, HTTPException, Request
from starlette.background import BackgroundTask
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
import os
import asyncio
import sqlite3
import shutil
import time
from model_config import (
    get_openai_client,
    get_lazy_openai_client,
    get_llm_provider,
    get_llm_base_url,
    get_deepseek_api_key,
    get_openai_api_key,
    get_default_chat_model,
    get_default_temperature,
    get_default_max_tokens,
    get_embedding_model_name
)
from services.document_loader import parse_file_to_text_file
from services.kb_service import MiniKBService
from services.kb_import_export_service import (
    export_kb,
    import_kb
)
from chat_service import (
    create_temp_kb_from_upload,
    run_local_kb_chat,
    run_temp_kb_chat,
    run_kb_chat
)
from db import (
    connection_scope,
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
    upsert_file_record,
    update_file_status,
    get_connection,
    user_owns_kb,
)
from user_scope import get_user_kb_root, migrate_legacy_demo_files
from auth.config import get_cors_origins
from auth.config import is_production_environment
from auth.dependencies import (
    get_current_user_optional,
    get_request_user_id,
    require_permission,
)
from auth.models import CurrentUser
from path_security import (
    PathValidationError,
    is_safe_filename,
    is_safe_kb_name,
    safe_join,
    validate_filename,
    validate_kb_name,
)
from resource_limits import (
    MAX_DOCUMENT_UPLOAD_BYTES,
    MAX_TEMP_UPLOAD_BYTES,
    MAX_ZIP_UPLOAD_BYTES,
    ResourceLimitError,
    install_staged_file,
    remove_file_quietly,
    stage_upload,
)
from auth.permissions import Permission, has_permission
from auth.security import (
    validate_production_auth_config,
)
from api.routes.agent import router as agent_router
from api.routes.auth import router as auth_router
from api.routes.conversations import router as conversation_router
from api.routes.openai_compat import create_openai_compat_router
from api.schemas import (
    ChatRequest,
    CreateKBRequest,
    FileChatRequest,
    KBChatRequest,
    ReindexFileRequest,
    SearchDocsRequest,
    SwitchKBRequest,
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
app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(conversation_router)


@app.exception_handler(PathValidationError)
async def path_validation_error_handler(request: Request, exc: PathValidationError):
    """将路径边界错误转换为不暴露内部路径的稳定 HTTP 400。"""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ResourceLimitError)
async def resource_limit_error_handler(request: Request, exc: ResourceLimitError):
    """将上传资源超限转换为不暴露临时路径的稳定 HTTP 413。"""
    return JSONResponse(status_code=413, content={"detail": str(exc)})


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

client = get_lazy_openai_client()
app.include_router(create_openai_compat_router(client))
kb_service = MiniKBService()
current_kb_by_scope = {}

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
    *,
    staged_path: str | None = None,
    override: bool = True,
    staged_size: int | None = None,
    user_id=None,
) -> None:
    """在线程池内锁住普通上传从正式文件安装到 DB 同步的完整过程。"""
    with scoped_service.mutation_lock:
        txt_filename = os.path.basename(txt_path)
        try:
            if staged_path is not None:
                install_staged_file(staged_path, upload_path)
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
                upsert_file_record(
                    scoped_service.kb_name,
                    txt_filename,
                    staged_size or 0,
                    0,
                    status="uploaded",
                    error=None,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    content_path=txt_path,
                    upload_path=upload_path,
                    user_id=user_id,
                )

            parse_file_to_text_file(upload_path, txt_path)
            scoped_service.chunk_size = chunk_size
            scoped_service.chunk_overlap = chunk_overlap
            scoped_service.rebuild_and_sync(file_overrides={
                txt_filename: {
                    "status": "indexed",
                    "error": None,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "content_path": txt_path,
                    "upload_path": upload_path,
                }
            })
        except Exception as exc:
            if staged_path is not None:
                update_file_status(
                    scoped_service.kb_name,
                    txt_filename,
                    "failed",
                    str(exc),
                    user_id=user_id,
                )
            raise


def ensure_kb_owned_or_404(kb_name: str, current_user: CurrentUser):
    """负责 ensure_kb_owned_or_404 的函数职责。"""
    if not user_owns_kb(kb_name, user_id=get_scoped_user_id(current_user)):
        raise HTTPException(status_code=404, detail="knowledge base not found")


@connection_scope
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


@connection_scope
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
    kb_name: str = Form(...),
    override: bool = Form(True),
    chunk_size: int = Form(300, gt=0),
    chunk_overlap: int = Form(50, ge=0),
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 upload 的函数职责。"""
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    validate_chunk_settings(chunk_size, chunk_overlap)
    kb_name = validate_kb_name(kb_name)
    ensure_kb_owned_or_404(kb_name, current_user)
    filename = validate_filename(file.filename or "uploaded.txt")
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTS:
        return {"message": "Only .txt, .pdf, .docx, .md and .csv files are supported."}

    staged = await stage_upload(
        file,
        max_bytes=MAX_DOCUMENT_UPLOAD_BYTES,
        error_message="document upload exceeds configured limit",
        suffix=ext,
    )

    try:
        # 上传目标来自本次请求，不能依赖可能被并发 /switch_kb 改写的进程内状态。
        scoped_service = get_scoped_kb_service(current_user, kb_name)
        user_id = get_scoped_user_id(current_user)
        upload_path = safe_join(
            scoped_service.upload_path,
            filename,
            field_name="filename",
        )
        txt_filename = f"{os.path.splitext(filename)[0]}.txt"
        txt_path = safe_join(
            scoped_service.content_path,
            txt_filename,
            field_name="filename",
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

        try:
            # 解析、embedding、FAISS/BM25 重建均可能耗时，不占用 async 事件循环。
            await asyncio.to_thread(
                process_uploaded_document,
                scoped_service,
                upload_path,
                txt_path,
                chunk_size,
                chunk_overlap,
                staged_path=staged.path,
                override=override,
                staged_size=staged.size,
                user_id=user_id,
            )
        except Exception as exc:
            error_message = str(exc)
            return {
                "error": error_message,
                "message": f"{filename} upload failed"
            }
    finally:
        remove_file_quietly(staged.path)

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
    filename = validate_filename(file.filename or "uploaded.txt")
    staged = await stage_upload(
        file,
        max_bytes=MAX_TEMP_UPLOAD_BYTES,
        error_message="document upload exceeds configured limit",
        suffix=os.path.splitext(filename)[1].lower(),
    )
    try:
        return await asyncio.to_thread(
            create_temp_kb_from_upload,
            staged.path,
            filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            user_id=get_scoped_user_id(current_user),
        )
    finally:
        remove_file_quietly(staged.path)


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


def get_content_txt_filename(filename: str):
    """负责 get_content_txt_filename 的函数职责。"""
    return (
        filename
        if filename.endswith(".txt")
        else f"{os.path.splitext(filename)[0]}.txt"
    )


def find_reindex_source_file(filename: str, scoped_service: MiniKBService):
    """负责 find_reindex_source_file 的函数职责。"""
    upload_path = safe_join(
        scoped_service.upload_path,
        filename,
        field_name="filename",
    )

    if os.path.exists(upload_path):
        return upload_path

    content_filename = get_content_txt_filename(filename)
    content_path = safe_join(
        scoped_service.content_path,
        content_filename,
        field_name="filename",
    )

    if os.path.exists(content_path):
        return content_path

    direct_content_path = safe_join(
        scoped_service.content_path,
        filename,
        field_name="filename",
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

    upload_path = safe_join(
        scoped_service.upload_path,
        filename,
        field_name="filename",
    )

    txt_filename = (
        filename
        if filename.endswith(".txt")
        else f"{os.path.splitext(filename)[0]}.txt"
    )
    content_path = safe_join(
        scoped_service.content_path,
        txt_filename,
        field_name="filename",
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
        with scoped_service.mutation_lock:
            try:
                update_file_status(
                    scoped_service.kb_name,
                    txt_filename,
                    "uploaded",
                    None,
                    user_id=user_id,
                )

                parse_file_to_text_file(source_path, txt_path)

                scoped_service.chunk_size = request.chunk_size
                scoped_service.chunk_overlap = request.chunk_overlap
                scoped_service.rebuild_and_sync(file_overrides={
                    txt_filename: {
                        "status": "indexed",
                        "error": None,
                        "chunk_size": request.chunk_size,
                        "chunk_overlap": request.chunk_overlap,
                        "content_path": txt_path,
                        "upload_path": source_path,
                    }
                })
            except Exception as exc:
                update_file_status(
                    scoped_service.kb_name,
                    txt_filename,
                    "failed",
                    str(exc),
                    user_id=user_id,
                )
                raise

        return {
            "message": f"{filename} reindexed successfully",
            "filename": txt_filename
        }
    except Exception as exc:
        error_message = str(exc)
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
    validate_filename(filename)
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
    scoped_service.rebuild_and_sync()
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

    if not is_safe_kb_name(kb_name):
        raise HTTPException(status_code=400, detail="invalid knowledge base name")

    if not user_owns_kb(kb_name, user_id=user_id):
        raise HTTPException(status_code=404, detail="knowledge base not found")

    delete_file_docs_by_kb(kb_name, user_id=user_id)
    delete_files_by_kb(kb_name, user_id=user_id)
    delete_kb_record(kb_name, user_id=user_id)

    kb_path = safe_join(get_user_kb_root(user_id), kb_name, field_name="kb_name")

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
    filename = validate_filename(file.filename or "")

    if not filename.endswith(".zip"):
        return {
            "error": "only .zip files are supported"
        }

    staged = await stage_upload(
        file,
        max_bytes=MAX_ZIP_UPLOAD_BYTES,
        error_message="zip upload exceeds configured limit",
        suffix=".zip",
    )

    try:
        return await asyncio.to_thread(
            import_kb,
            staged.path,
            override=override,
            user_id=get_scoped_user_id(current_user),
        )
    finally:
        remove_file_quietly(staged.path)

@app.post("/knowledge_bases")
def create_knowledge_base(
    request: CreateKBRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 create_knowledge_base 的函数职责。"""
    require_permission(current_user, Permission.CAN_MANAGE_KB)
    user_id = get_scoped_user_id(current_user)

    kb_name = validate_kb_name(request.kb_name)
    kb_path = safe_join(get_user_kb_root(user_id), kb_name, field_name="kb_name")

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

    create_kb(kb_name, user_id=user_id)

    return {
        "message": f"{kb_name} created"
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
    validate_filename(filename)
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

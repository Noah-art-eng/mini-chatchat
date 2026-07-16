from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from starlette.background import BackgroundTask
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
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
    get_conversation_messages,
    update_conversation_title,
    delete_conversation,
    get_connection
)


load_dotenv()

SUPPORTED_EXTS = [".txt", ".pdf", ".docx", ".md", ".csv"]
SERVICE_NAME = "mini-chatchat"
SERVICE_VERSION = "0.1.0"
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
UPLOADS_DIR = os.path.join(BACKEND_DIR, "uploads")

app = FastAPI()
init_db()
create_default_kb()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = get_openai_client()
kb_service = MiniKBService()


class ChatRequest(BaseModel):
    question: str
    conversation_id: int | None = None
    top_k: int = 3
    score_threshold: float = 0.8
    prompt_name: str = "default"
    return_direct: bool = False
    model: str = get_default_chat_model()
    temperature: float = get_default_temperature()
    max_tokens: int | None = get_default_max_tokens()
    stream: bool = False

class CreateKBRequest(BaseModel):
    kb_name: str

class SwitchKBRequest(BaseModel):
    kb_name: str

class SearchDocsRequest(BaseModel):
    query: str
    top_k: int = 3
    file_name: str | None = None

class ReindexFileRequest(BaseModel):
    chunk_size: int = 300
    chunk_overlap: int = 50

class FileChatRequest(BaseModel):
    query: str
    temp_kb_id: str
    top_k: int = 3
    score_threshold: float = 0.8
    prompt_name: str = "default"
    stream: bool = False

class KBChatRequest(BaseModel):
    query: str
    mode: str = "local_kb"
    kb_name: str = "default"
    temp_kb_id: str | None = None
    top_k: int = 3
    score_threshold: float = 0.8
    prompt_name: str = "default"
    stream: bool = False
    model: str = get_default_chat_model()
    temperature: float = get_default_temperature()
    max_tokens: int | None = get_default_max_tokens()
    return_direct: bool = False
    conversation_id: int | None = None
    rerank: bool = False
    rerank_top_n: int = 3
    file_name: str | None = None
    source: str | None = None
    metadata_filter: dict | None = None

class OpenAIChatCompletionRequest(BaseModel):
    model: str = get_default_chat_model()
    messages: list
    stream: bool = False
    temperature: float = get_default_temperature()
    max_tokens: int | None = get_default_max_tokens()
    extra_body: dict | None = None

class FeedbackRequest(BaseModel):
    message_id: int
    score: int
    reason: str | None = None

class ConversationUpdateRequest(BaseModel):
    title: str

class ToolRunRequest(BaseModel):
    arguments: dict = {}

class AgentToolCallRequest(BaseModel):
    query: str
    kb_name: str | None = "default"
    tools: list[str] | None = None
    conversation_id: int | None = None
    max_steps: int = 3

# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────


def get_configured_provider():
    if get_deepseek_api_key():
        return "deepseek"

    if get_openai_api_key():
        return "openai"

    return "none"


def check_database():
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
    provider = get_configured_provider()
    embedding_model = get_embedding_model_name()

    return {
        "database": check_database(),
        "data_dir": "ok" if os.path.isdir(DATA_DIR) else "error",
        "uploads_dir": "ok" if os.path.isdir(UPLOADS_DIR) else "error",
        "chat_provider": "ok" if provider != "none" else "error",
        "embedding_model": "ok" if embedding_model else "error",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "provider": get_configured_provider()
    }


@app.get("/health/deps")
def health_deps():
    checks = build_dependency_checks()
    status = (
        "ok"
        if all(value == "ok" for value in checks.values())
        else "degraded"
    )

    return {
        "status": status,
        "checks": checks
    }


@app.get("/agent/tools")
def get_agent_tools():
    return {
        "tools": list_all_tools()
    }


@app.post("/agent/tools/{tool_name}/run")
def run_agent_tool(tool_name: str, request: ToolRunRequest):
    result = run_tool(tool_name, request.arguments)
    return result.to_dict()


@app.get("/agent/mcp/tools")
def get_agent_mcp_tools():
    return {
        "tools": list_mcp_tools(),
        "enabled": True,
        "provider": "mcp",
    }


@app.get("/agent/mcp/servers")
def get_agent_mcp_servers():
    return {
        "servers": list_mcp_servers(),
    }


@app.post("/agent/mcp/servers/{server_name}/shutdown")
def stop_agent_mcp_server(server_name: str):
    return {
        "server": shutdown_mcp_server(server_name),
    }


@app.post("/agent/mcp/tools/{tool_name}/run")
def run_agent_mcp_tool(tool_name: str, request: ToolRunRequest):
    result = run_mcp_tool(tool_name, request.arguments)
    return result.to_dict()


@app.post("/agent/decide")
def agent_decide(request: AgentToolCallRequest):
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
def agent_run_once(request: AgentToolCallRequest):
    return run_agent_once(
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
    )


@app.post("/agent/run")
def agent_run(request: AgentToolCallRequest):
    return run_agent_persisted(
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
        conversation_id=request.conversation_id,
    )


@app.post("/agent/run_multi")
def agent_run_multi(request: AgentToolCallRequest):
    return run_agent_multi_step_persisted(
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
        max_steps=request.max_steps,
        conversation_id=request.conversation_id,
    )


@app.post("/agent/plan_run")
def agent_plan_run(request: AgentToolCallRequest):
    return run_agent_planner_persisted(
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
        max_steps=request.max_steps,
        conversation_id=request.conversation_id,
    )


def encode_sse(event):
    event_type = event.get("type", "message")
    payload = json.dumps(event, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


@app.post("/agent/plan_run_stream")
async def agent_plan_run_stream(
    request: AgentToolCallRequest,
    http_request: Request,
):
    events: queue.Queue = queue.Queue()
    stop_event = threading.Event()

    def put_event(event):
        events.put(event)

    def run_agent_worker():
        try:
            result = run_agent_planner_stream_persisted(
                request.query,
                kb_name=request.kb_name,
                tools=request.tools,
                max_steps=request.max_steps,
                conversation_id=request.conversation_id,
                event_sink=put_event,
                should_stop=stop_event.is_set,
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
def kb_chat(request: KBChatRequest):
    return run_kb_chat(request, client)


@app.get("/models")
def get_models():
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
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")

    return ""


def build_kb_chat_request_from_openai(request: OpenAIChatCompletionRequest):
    extra_body = request.extra_body or {}
    query = get_last_user_message(request.messages)

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


def build_openai_completion_response(completion_id, model, result):
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
    async def event_stream():
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
    async def event_stream():
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
def chat_completions(request: OpenAIChatCompletionRequest):
    query = get_last_user_message(request.messages)

    if not query:
        return {
            "error": "messages must contain at least one user message"
        }

    completion_id = f"chatcmpl-{uuid.uuid4()}"
    kb_request = build_kb_chat_request_from_openai(request)
    result = run_kb_chat(kb_request, client)

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
def chat_feedback(request: FeedbackRequest):
    if request.score not in [1, -1]:
        return {
            "error": "score must be 1 or -1"
        }

    updated = update_message_feedback(
        request.message_id,
        request.score,
        request.reason
    )

    if not updated:
        return {
            "error": "message not found"
        }

    return {
        "message": "feedback saved",
        "message_id": request.message_id,
        "feedback_score": request.score,
        "feedback_reason": request.reason
    }


@app.get("/conversations")
def get_conversations():
    return {
        "conversations": list_conversations()
    }


@app.get("/conversations/{conversation_id}/messages")
def get_conversation_history(conversation_id: int):
    return {
        "conversation_id": conversation_id,
        "messages": get_conversation_messages(conversation_id)
    }


@app.patch("/conversations/{conversation_id}")
def update_conversation(conversation_id: int, request: ConversationUpdateRequest):
    title = request.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="title cannot be empty"
        )

    conversation = update_conversation_title(
        conversation_id,
        title
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
def remove_conversation(conversation_id: int):
    deleted = delete_conversation(conversation_id)

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
def chat(request: ChatRequest):
    return run_local_kb_chat(request, kb_service, client)

@app.post("/search_docs")
def search_docs(request: SearchDocsRequest):
    results = kb_service.search_docs(
        request.query,
        top_k=request.top_k
    )

    if request.file_name:
        results = [
            result
            for result in results
            if result.get("source") == request.file_name
        ]

    return {
        "query": request.query,
        "results": results
    }

@app.post("/switch_kb")
def switch_kb(request: SwitchKBRequest):
    global kb_service

    kb_service = MiniKBService(
        request.kb_name
    )

    return {
        "current_kb": request.kb_name
    }

@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    override: bool = Form(True),
    chunk_size: int = Form(300),
    chunk_overlap: int = Form(50)
):
    content = await file.read()
    filename = file.filename or "uploaded.txt"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTS:
        return {"message": "Only .txt, .pdf, .docx, .md and .csv files are supported."}

    upload_path = os.path.join(
        kb_service.upload_path,
        filename
    )
    txt_filename = f"{os.path.splitext(filename)[0]}.txt"
    txt_path = os.path.join(
        kb_service.content_path,
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
            kb_service.kb_name,
            txt_filename
        )
        delete_file_docs(
            kb_service.kb_name,
            txt_filename
        )

    with open(upload_path, "wb") as f:
        f.write(content)

    upsert_file_record(
        kb_service.kb_name,
        txt_filename,
        os.path.getsize(upload_path),
        0,
        status="uploaded",
        error=None,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        content_path=txt_path,
        upload_path=upload_path,
    )

    try:
        text = load_file(upload_path)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        kb_service.chunk_size = chunk_size
        kb_service.chunk_overlap = chunk_overlap
        kb_service.rebuild_index()

        txt_size = os.path.getsize(txt_path)

        kb_service.save_file_record(
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
            kb_service.kb_name,
            txt_filename,
            "failed",
            error_message,
        )
        return {
            "error": error_message,
            "message": f"{filename} upload failed"
        }

    return {"message": f"{filename} uploaded and indexed successfully"}


@app.post("/temp_upload")
async def temp_upload(
    file: UploadFile = File(...),
    chunk_size: int = Form(300),
    chunk_overlap: int = Form(50)
):
    content = await file.read()
    return create_temp_kb_from_upload(
        content,
        file.filename,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )


@app.post("/file_chat")
def file_chat(request: FileChatRequest):
    return run_temp_kb_chat(request, client)


@app.get("/documents")
def list_documents():
    return {"files": kb_service.list_documents()}


def is_safe_filename(filename: str):
    return ".." not in filename and "/" not in filename and "\\" not in filename


def get_content_txt_filename(filename: str):
    return (
        filename
        if filename.endswith(".txt")
        else f"{os.path.splitext(filename)[0]}.txt"
    )


def find_reindex_source_file(filename: str):
    upload_path = os.path.join(
        kb_service.upload_path,
        filename
    )

    if os.path.exists(upload_path):
        return upload_path

    content_filename = get_content_txt_filename(filename)
    content_path = os.path.join(
        kb_service.content_path,
        content_filename
    )

    if os.path.exists(content_path):
        return content_path

    direct_content_path = os.path.join(
        kb_service.content_path,
        filename
    )

    if os.path.exists(direct_content_path):
        return direct_content_path

    return None


@app.get("/documents/{filename}/download")
def download_document(filename: str):
    if not is_safe_filename(filename):
        return {
            "error": "invalid filename"
        }

    upload_path = os.path.join(
        kb_service.upload_path,
        filename
    )

    txt_filename = (
        filename
        if filename.endswith(".txt")
        else f"{os.path.splitext(filename)[0]}.txt"
    )
    content_path = os.path.join(
        kb_service.content_path,
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

    return {
        "error": "file not found"
    }


@app.post("/documents/{filename}/reindex")
def reindex_document(filename: str, request: ReindexFileRequest):
    if not is_safe_filename(filename):
        return {
            "error": "invalid filename"
        }

    source_path = find_reindex_source_file(filename)

    if source_path is None:
        return {
            "error": "file not found"
        }

    txt_filename = get_content_txt_filename(filename)
    txt_path = os.path.join(
        kb_service.content_path,
        txt_filename
    )

    try:
        update_file_status(
            kb_service.kb_name,
            txt_filename,
            "uploaded",
            None,
        )

        text = load_file(source_path)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        kb_service.chunk_size = request.chunk_size
        kb_service.chunk_overlap = request.chunk_overlap

        delete_file_docs(
            kb_service.kb_name,
            txt_filename
        )

        kb_service.rebuild_index()

        kb_service.save_file_record(
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
            kb_service.kb_name,
            txt_filename,
            "failed",
            error_message,
        )
        return {
            "error": error_message,
            "message": f"{filename} reindex failed"
        }


@app.delete("/documents/{filename}")
def delete_document(filename: str):
    return kb_service.delete_document(filename)

@app.get("/stats")
def get_stats():
    return kb_service.get_stats()

@app.post("/reload")
def reload_index():
    """Manually trigger a full index rebuild without restarting the server."""
    kb_service.rebuild_index()
    return kb_service.get_stats()

@app.get("/knowledge_bases")
def get_knowledge_bases():
    return {
        "knowledge_bases": list_kbs()
    }

@app.delete("/knowledge_bases/{kb_name}")
def delete_knowledge_base(kb_name: str):
    global kb_service

    if kb_name == "default":
        return {
            "error": "default knowledge base cannot be deleted"
        }

    if ".." in kb_name or "/" in kb_name or "\\" in kb_name:
        return {
            "error": "invalid knowledge base name"
        }

    delete_file_docs_by_kb(kb_name)
    delete_files_by_kb(kb_name)
    delete_kb_record(kb_name)

    kb_path = os.path.join("data", kb_name)

    if os.path.exists(kb_path):
        shutil.rmtree(kb_path)

    if kb_service.kb_name == kb_name:
        kb_service = MiniKBService("default")

    return {
        "message": f"{kb_name} deleted"
    }

@app.get("/knowledge_bases/{kb_name}/export")
def export_knowledge_base(kb_name: str):
    result = export_kb(kb_name)

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
):
    filename = file.filename or ""

    if not filename.endswith(".zip"):
        return {
            "error": "only .zip files are supported"
        }

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
        temp_path = temp_file.name
        temp_file.write(await file.read())

    try:
        return import_kb(temp_path, override=override)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/knowledge_bases")
def create_knowledge_base(request: CreateKBRequest):

    kb_path = os.path.join("data", request.kb_name)

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

    create_kb(request.kb_name)

    return {
        "message": f"{request.kb_name} created"
    }

@app.post("/sync_files")
def sync_files():
    kb_service.sync_files_to_db()
    return kb_service.get_stats()

@app.get("/file_docs/{filename}")
def get_file_docs(filename: str):
    return {
        "chunks": list_file_docs(
            kb_service.kb_name,
            filename
        )
    }

@app.get("/chunk/{chunk_id}")
def get_chunk(chunk_id: int):
    return kb_service.get_chunk_by_id(chunk_id)

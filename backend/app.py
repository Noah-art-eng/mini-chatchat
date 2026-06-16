from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os

from rag import generate_answer, load_pdf
from services.kb_service import MiniKBService
from db import init_db, create_default_kb, list_kbs, list_file_docs, create_kb


load_dotenv()

SUPPORTED_EXTS = [".pdf", ".txt"]

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

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
kb_service = MiniKBService()
chat_history = []


class ChatRequest(BaseModel):
    question: str

class CreateKBRequest(BaseModel):
    kb_name: str

class SwitchKBRequest(BaseModel):
    kb_name: str


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@app.post("/chat")
def chat(request: ChatRequest):
    results = kb_service.search_docs(request.question)

    chat_history.append({"role": "user", "content": request.question})

    try:
        answer = generate_answer(
            request.question, results, client, chat_history
        )
    except Exception:
        if results:
            answer = results[0]["chunk"]
        else:
            answer = "No relevant information found."

    chat_history.append({"role": "assistant", "content": answer})

    return {
        "question": request.question,
        "answer": answer,
        "sources": results,
        "chat_history": chat_history,
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
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTS:
        return {"message": "Only .pdf and .txt files are supported."}

    if ext == ".pdf":
        pdf_path = os.path.join(kb_service.upload_path, filename)
        with open(pdf_path, "wb") as f:
            f.write(content)
        text = load_pdf(pdf_path)
        txt_filename = filename.replace(".pdf", ".txt")
        txt_path = os.path.join(kb_service.content_path, txt_filename)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        txt_path = os.path.join(kb_service.content_path, filename)
        with open(txt_path, "wb") as f:
            f.write(content)

    kb_service.rebuild_index()

    txt_size = os.path.getsize(txt_path)

    kb_service.save_file_record(
    os.path.basename(txt_path),
    txt_size
    )  

    return {"message": f"{filename} uploaded and indexed successfully"}


@app.get("/documents")
def list_documents():
    return {"files": kb_service.list_documents()}

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
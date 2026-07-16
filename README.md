# Mini ChatChat

Mini ChatChat is a compact, readable clone of the core LangChain-Chatchat experience. It focuses on the practical RAG path first:

```text
Question -> Retrieve -> Context -> Prompt -> LLM -> Answer
```

The project intentionally avoids LangChain for now so the retrieval, prompt building, streaming, knowledge-base management, and conversation flow remain easy to inspect.

## Core Features

- Local knowledge-base RAG chat.
- Temporary file chat.
- Search-engine mode.
- Unified `/kb_chat` endpoint with ChatChat-style `mode`.
- OpenAI-compatible `/chat/completions` endpoint.
- DeepSeek-first, OpenAI-compatible model provider config.
- Streaming SSE responses.
- Conversation list, messages, rename, delete, and persisted assistant sources.
- Feedback/rating for assistant messages.
- Prompt templates: `default`, `empty`, `strict`.
- Multi-format document loading: `.txt`, `.pdf`, `.docx`, `.md`, `.csv`.
- FAISS persistence.
- Hybrid search: FAISS + BM25.
- Metadata filter by file/source.
- Lightweight rerank.
- Context deduplication.
- Context token budget before prompt construction.
- KB file metadata/status.
- Single-file reindex.
- KB import/export.
- React frontend for the main product UI.
- Agent mode with tool calling, multi-step execution, lightweight planner metadata, and trace restore.
- Real MCP Integration Foundation with allowlisted demo, filesystem readonly, real stdio transport, and SQLite readonly MCP discovery and calls.
- Legacy plain HTML/CSS/JS frontend kept for compatibility.
- Smoke test scripts for core backend flows.

## Tech Stack

Backend:

- Python
- FastAPI
- SQLite
- FAISS
- Sentence Transformers
- OpenAI-compatible Python SDK
- DeepSeek API by default when `DEEPSEEK_API_KEY` is configured
- pypdf
- python-docx
- python-dotenv

Frontend:

- React
- Vite
- TypeScript
- Plain HTML/CSS/JS legacy frontend

Testing:

- Python smoke test scripts using `requests`
- Vite production build

## Architecture

Important backend modules:

- `backend/app.py`: FastAPI routes and request models.
- `backend/chat_service.py`: local/temp/search KB chat orchestration and streaming response assembly.
- `backend/rag.py`: document splitting, prompt context building, token budget, answer generation, streaming.
- `backend/db.py`: SQLite schema, migrations, KB metadata, conversation/message, feedback.
- `backend/model_config.py`: DeepSeek/OpenAI provider selection and model defaults.
- `backend/services/kb_service.py`: KB state, FAISS persistence, hybrid search, metadata filter, dedup.
- `backend/services/document_loader.py`: txt/pdf/docx/md/csv parsing.
- `backend/services/search_service.py`: web search adapter.
- `backend/services/reranker_service.py`: lightweight embedding rerank.
- `backend/services/kb_import_export_service.py`: KB zip export/import.

Frontend:

- `frontend-react/`: current React UI.
- `frontend/`: legacy frontend retained during migration.

Runtime data:

- `backend/mini.db`
- `backend/data/`
- `backend/data/{kb_name}/uploads/`
- `backend/data/{kb_name}/content/`
- `backend/data/{kb_name}/vector_store/`

Runtime data is ignored by Git and should not be committed.

## Environment

Copy the example file and fill in one provider key:

```bash
cp .env.example .env
```

`docker compose` reads the root `.env` file. If you run the backend directly from `backend/`, you can also copy the same values to `backend/.env`.

DeepSeek is preferred when `DEEPSEEK_API_KEY` exists:

```bash
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

OpenAI-compatible fallback:

```bash
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
```

Embedding model:

```bash
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

Do not commit real API keys.

## Local Setup

Python 3.10+ is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

If the project is missing dependencies because `requirements.txt` is minimal in your checkout, install the backend runtime dependencies:

```bash
python3 -m pip install fastapi uvicorn python-multipart openai python-dotenv sentence-transformers faiss-cpu numpy pypdf python-docx requests
```

## Run Backend

Run from the `backend/` directory because runtime data paths are relative to that directory:

```bash
cd backend
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Model config check:

```bash
curl http://127.0.0.1:8000/models
```

The `/models` response intentionally does not expose API keys.

## Run With Docker Compose

Create a root `.env` file first:

```bash
cp .env.example .env
```

Fill in `DEEPSEEK_API_KEY` or `OPENAI_API_KEY`, then start the stack:

```bash
docker compose up --build
```

Services:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://127.0.0.1:5173
```

Health checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/deps
```

The compose setup keeps runtime state outside the image:

- `./backend/data:/app/backend/data`
- `./backend/uploads:/app/backend/uploads`
- `./backend/mini.db:/app/backend/mini.db`

The frontend image is built with:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Override it when needed:

```bash
VITE_API_BASE_URL=http://your-backend:8000 docker compose up --build
```

Docker build excludes `.venv`, `node_modules`, `backend/data`, `backend/uploads`, `backend/mini.db`, cache folders, test artifacts, and zip exports.

## Run React Frontend

```bash
cd frontend-react
npm install
npm run dev
```

Default Vite URL:

```text
http://localhost:5173
```

Production build:

```bash
cd frontend-react
npm run build
```

## Run Legacy Frontend

The old frontend is still available:

```bash
cd frontend
python3 -m http.server 5500
```

Then open:

```text
http://127.0.0.1:5500
```

## Smoke Tests

Start the backend first:

```bash
cd backend
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Run the unified smoke suite from the project root:

```bash
python3 scripts/run_smoke_tests.py
```

The runner executes tests sequentially because several tests call `/switch_kb`.

Covered scripts:

- `scripts/test_llm_provider.py`
- `scripts/test_react_core_api_smoke.py`
- `scripts/test_conversation_api_smoke.py`
- `scripts/test_temp_kb_api_smoke.py`
- `scripts/test_hybrid_search_smoke.py`
- `scripts/test_metadata_filter_smoke.py`
- `scripts/test_context_dedup_smoke.py`
- `scripts/test_context_token_budget_smoke.py`
- `scripts/test_kb_import_export.py`

Syntax checks:

```bash
python3 -m py_compile scripts/run_smoke_tests.py
cd frontend-react && npm run build
```

## Current Status

Completed:

- Local KB RAG.
- Temp KB / file chat.
- Search-engine mode.
- Streaming.
- Conversation productization.
- Feedback.
- Sources persistence for assistant messages.
- KB CRUD, upload, document actions, reindex, import/export.
- Hybrid search.
- Metadata filter.
- Context deduplication.
- Context token budget.
- DeepSeek/OpenAI-compatible provider config.
- React UI core experience.
- Unified smoke test runner.
- Agent planner loop.
- Real MCP Integration Foundation.
- Filesystem MCP readonly.
- Real MCP stdio transport runtime.
- SQLite MCP readonly.

## Deferred Items

Not started yet:

- Playwright MCP tools.
- Agent streaming.
- OCR/PPT/Excel loaders.
- Multi-provider model UI.
- LangChain integration.

The next recommended work is Playwright MCP controlled browser integration and Agent streaming.

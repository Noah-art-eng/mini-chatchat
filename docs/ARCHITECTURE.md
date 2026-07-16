# Architecture

Mini ChatChat is intentionally smaller than LangChain-Chatchat. It keeps the same core product concepts but uses direct Python services instead of LangChain chains.

## System Shape

```text
Frontend
  HTML/CSS/JS currently
  React next
      |
      v
FastAPI app.py
      |
      +--> chat_service.py
      |       local_kb / temp_kb / search_engine
      |       streaming SSE
      |       return_direct
      |
      +--> rag.py
      |       context builder
      |       history builder
      |       prompt builder
      |       OpenAI call
      |
      +--> services/
      |       kb_service.py
      |       document_loader.py
      |       reranker_service.py
      |       search_service.py
      |       kb_import_export_service.py
      |
      +--> db.py
              SQLite schema and repositories
```

## RAG Flow

```text
Question
  -> retrieve docs
  -> optional rerank
  -> build context
  -> build prompt
  -> OpenAI chat completion
  -> stream answer
  -> save assistant message
```

`/kb_chat` is the preferred endpoint. It supports:

- `mode=local_kb`
- `mode=temp_kb`
- `mode=search_engine`
- `stream`
- `return_direct`
- `top_k`
- `score_threshold`
- `prompt_name`
- `rerank`
- `rerank_top_n`
- model settings
- `conversation_id`

## Backend Modules

### `backend/app.py`

Responsibilities:

- FastAPI app setup.
- CORS.
- request models.
- route definitions.
- calling service functions.

This file should not accumulate more business logic. New complex workflows should go into `backend/services/` or `chat_service.py`.

### `backend/chat_service.py`

Responsibilities:

- Unified KB chat orchestration.
- Local KB, temp KB, search engine routing.
- Streaming response assembly.
- Save assistant messages after streaming.
- Rerank integration.

This mirrors the role of ChatChat `kb_chat.py`, but without LangChain.

### `backend/rag.py`

Responsibilities:

- Load/split/search primitives.
- `build_context()`
- `build_history()`
- `build_prompt()`
- `generate_answer()`
- `stream_answer()`

Prompt templates live in `backend/prompts/`.

### `backend/services/kb_service.py`

Responsibilities:

- Formal KB filesystem layout.
- Document loading from `content/`.
- Chunking.
- FAISS index build/load/save.
- Search.
- Document metadata sync.

KB layout:

```text
backend/data/{kb_name}/
  uploads/
  content/
  vector_store/
    index.faiss
    chunks.json
```

Runtime KB data is ignored by Git.

### `backend/db.py`

SQLite stores:

- knowledge bases
- knowledge files
- file to chunk mapping
- conversations
- messages
- feedback

Migrations are done in `init_db()` with `PRAGMA table_info` and `ALTER TABLE` for compatibility.

### `backend/model_config.py`

Centralized model configuration:

- OpenAI API key
- OpenAI base URL
- default chat model
- default temperature
- default max tokens
- embedding model

`/models` returns non-secret config. API keys are never returned.

### `backend/services/kb_import_export_service.py`

Responsibilities:

- export KB zip
- import KB zip
- write/read `metadata.json`
- prevent zip slip
- restore DB metadata
- rebuild index after import

Export zip includes:

```text
metadata.json
uploads/
content/
vector_store/
```

## Frontend Architecture Today

Current frontend is plain JS:

- one large `app.js`
- HTML in `index.html`
- shared CSS in `style.css`

It works, but state is now spread across globals:

- `currentTempKbId`
- selected KB
- selected chat mode
- retrieval settings
- localStorage chat HTML
- streaming DOM node references

This is the reason React UI redesign is the next phase.

## ChatChat Parity Map

Implemented Mini equivalent:

- `kb_chat.py` mode routing -> `/kb_chat`
- `file_chat.py` temp docs -> `/temp_upload` and `/file_chat`
- prompt template selection -> `backend/prompts/`
- empty prompt fallback -> `build_prompt()`
- vector store persistence -> FAISS `index.faiss` and `chunks.json`
- KB file metadata -> SQLite `knowledge_file`
- feedback -> `/chat/feedback`
- OpenAI compatible route -> `/chat/completions`
- search engine mode -> `search_service.py`

Not yet implemented:

- full conversation UI
- advanced reranker model
- model provider registry UI
- Agent tools
- MCP connection UI
- OCR/PPT/Excel loaders
- KB summary

## Data Safety

Do not commit:

- SQLite DB
- FAISS files
- uploaded documents
- exported zip files
- screenshots and test artifacts

Keep:

- source code
- docs
- config templates
- tests
- `test_files/sample_rag.txt`

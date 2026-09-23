# Mini ChatChat Agent Guide

This file is the working contract for AI coding agents in this repository. Keep it short, durable, and specific to Mini ChatChat. One-off task notes belong in chat, not here.

## Project Goal

Mini ChatChat is a small, readable clone of the core LangChain-Chatchat experience. The project intentionally avoids LangChain for now and keeps the implementation inspectable:

Question -> Retrieve -> Context -> Prompt -> LLM -> Answer

The current product already supports local KB chat, temp file chat, search engine mode, streaming, rerank, model config, KB metadata, file reindex, KB import/export, feedback, and OpenAI-compatible chat completions.

## Current Priority

The next major phase is:

1. React UI redesign
2. Conversation History UI

Do not start Agent, MCP expansion, multi-provider UI, or large backend rewrites before these are planned and approved.

## Operating Rules

- Read existing code before editing. Prefer local patterns over new abstractions.
- Keep `backend/app.py` thin when possible. Put reusable workflow logic in services.
- Do not introduce LangChain unless explicitly requested.
- Do not modify runtime data or commit generated data.
- Do not commit or track:
  - `backend/mini.db`
  - `backend/data/`
  - `backend/uploads/`
  - `playwright-report/`
  - `test-results/`
  - zip exports
  - cache directories
- Keep `test_files/sample_rag.txt` tracked. It is the stable test fixture.
- Use `apply_patch` for manual edits.
- Prefer `rg` for search.
- Do not run or start long-lived servers unless the user asks.

## Verification Commands

Use the smallest validation that proves the change.

Backend syntax:

```bash
python3 -m py_compile backend/app.py backend/db.py backend/rag.py backend/chat_service.py backend/services/kb_service.py
```

Import/export E2E:

```bash
python3 -m py_compile scripts/test_kb_import_export.py
python3 scripts/test_kb_import_export.py
```

Frontend syntax:

```bash
node --check frontend/app.js
```

When changing both backend and frontend, run both Python compile checks and `node --check`.

## Backend Boundaries

Core modules:

- `backend/app.py`: FastAPI routes and request models.
- `backend/chat_service.py`: local/temp/search KB chat orchestration, streaming response assembly.
- `backend/rag.py`: document splitting, prompt building, LLM answer generation and streaming.
- `backend/db.py`: SQLite schema, migrations, conversation/message, KB/file metadata.
- `backend/model_config.py`: OpenAI client and model defaults.
- `backend/services/kb_service.py`: formal KB document state, FAISS index, persistence, search.
- `backend/services/document_loader.py`: txt/pdf/docx/md/csv parsing.
- `backend/services/reranker_service.py`: lightweight embedding rerank.
- `backend/services/search_service.py`: web search adapter.
- `backend/services/kb_import_export_service.py`: KB zip export/import.

Runtime data lives under `backend/data/` and must remain ignored.

## Frontend Boundaries

The current frontend is plain HTML/CSS/JS:

- `frontend/index.html`
- `frontend/app.js`
- `frontend/style.css`

Do not keep adding complex UI state to the plain JS frontend indefinitely. The next UI phase should move to React with explicit state boundaries for:

- KB selection
- chat mode
- conversation id
- streaming message state
- sources
- retrieval debug options
- temp KB id

## Architecture Rules From References

Useful rules distilled from the reference repos:

- Evidence first: verify with code and tests before claiming completion.
- File-based context is useful, but keep durable docs separate from runtime logs.
- Progressive disclosure: keep high-level docs concise and link to detailed docs.
- Tools and services should return structured data with clear errors.
- Prefer deterministic checks before model-based judgement.
- For RAG, keep retrieval, prompt building, model invocation, and response formatting separate.
- For UI, avoid hidden global state as the product grows. Conversation state should be explicit.

## Next Work Queue

1. React UI redesign plan and scaffold.
2. Conversation list and message history API/UI.
3. Move frontend streaming/SSE parsing into a reusable React hook.
4. Add E2E tests for conversation switching and feedback.
5. Only after the above, revisit Agent/MCP features.

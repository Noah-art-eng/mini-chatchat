# Project State

Last updated: 2026-06-30

## Summary

Mini ChatChat is now a functional ChatChat-inspired RAG and Agent product with local KB chat, temporary file chat, search-engine mode, React UI, conversation history, KB management, import/export, retrieval enhancement, authentication, OAuth, health checks, production Docker Compose, reverse proxy support, backup/restore scripts, deployment docs, and a unified smoke test runner.

The RAG core, Agent foundation, authentication foundation, and single-host production deployment baseline are considered feature-complete for the current phase. The next stage should focus on real deployment rehearsal and targeted production hardening.

## Completed Backend Features

Chat and RAG:

- `/chat`: legacy local KB chat entry.
- `/kb_chat`: unified ChatChat-style entry with `mode=local_kb | temp_kb | search_engine`.
- `/file_chat`: temp KB chat.
- `/chat/completions`: OpenAI-compatible wrapper.
- Streaming SSE with `sources`, `token`, `done`.
- `return_direct` retrieval-only mode.
- Prompt templates: `default`, `empty`, `strict`.
- DeepSeek-first, OpenAI-compatible provider config.

Conversation:

- Conversation list.
- Conversation messages.
- Conversation rename.
- Conversation delete.
- `updated_time` ordering.
- Assistant message IDs.
- Feedback storage.
- Assistant sources persisted in message metadata.

Knowledge base:

- KB CRUD.
- Document upload.
- Multi-format loader: txt, pdf, docx, md, csv.
- Chunking with `chunk_size` and `chunk_overlap`.
- FAISS persistence under `data/{kb_name}/vector_store/`.
- File metadata/status:
  - `uploaded`
  - `indexed`
  - `failed`
- File download.
- File delete.
- Single-file reindex.
- KB export/import zip with metadata.

Retrieval enhancement:

- Hybrid Search: FAISS + BM25.
- Metadata Filter by `file_name`, `source`, or `metadata_filter`.
- Optional lightweight embedding rerank.
- Context deduplication before returning top results.
- Context token budget in prompt context construction.
- Retrieval debug support through `return_direct`.

Configuration:

- `backend/model_config.py` centralizes:
  - DeepSeek API key/base URL/model.
  - OpenAI API key/base URL/model fallback.
  - default temperature.
  - default max tokens.
  - embedding model.
- `/models` exposes non-secret model config.

Deployment:

- `GET /health`
- `GET /health/deps`
- Backend Dockerfile.
- React frontend Dockerfile.
- `docker-compose.yml`.
- `docker-compose.dev.yml`.
- `docker-compose.prod.yml`.
- nginx frontend reverse proxy for `/api`.
- Request ID response header.
- Structured JSON request logs.
- Runtime metadata in health responses.
- Backup and restore scripts.
- `.env.production.example`.
- Deployment docs under `docs/deployment/`.
- Production checklist.
- Runtime data mounted through volumes:
  - `backend/data`
  - `backend/uploads`
  - `backend/mini.db`
- Docker Compose verified:
  - backend on `127.0.0.1:8000`
  - frontend on `127.0.0.1:5173`
  - health checks pass

Authentication:

- Email registration/login.
- HttpOnly refresh cookie.
- Refresh token rotation.
- Multi-device session management.
- Account page.
- User data isolation.
- Google OAuth.
- GitHub OAuth.

## Completed Frontend Features

React frontend:

- Three-column application layout.
- Conversation sidebar.
- Chat area.
- Sources panel.
- Chat mode selector:
  - local KB
  - temp KB
  - search engine
- KB selector.
- Document list.
- Upload.
- Download.
- Reindex.
- Delete.
- Import/export.
- Feedback controls.
- Retrieval Debug panel.
- Search engine mode productized.
- Temp file chat productized.

Legacy frontend:

- Kept for compatibility.
- No longer the primary UI target.

## Testing

Unified runner:

- `scripts/run_smoke_tests.py`

Core smoke scripts:

- `scripts/test_llm_provider.py`
- `scripts/test_react_core_api_smoke.py`
- `scripts/test_conversation_api_smoke.py`
- `scripts/test_temp_kb_api_smoke.py`
- `scripts/test_hybrid_search_smoke.py`
- `scripts/test_metadata_filter_smoke.py`
- `scripts/test_context_dedup_smoke.py`
- `scripts/test_context_token_budget_smoke.py`
- `scripts/test_kb_import_export.py`
- `scripts/test_tool_registry_smoke.py`
- `scripts/test_agent_tool_calling_smoke.py`
- `scripts/test_agent_loop_smoke.py`
- `scripts/test_mcp_adapter_smoke.py`
- `scripts/test_sqlite_tool_smoke.py`
- `scripts/test_filesystem_tool_smoke.py`
- `scripts/test_oauth_smoke.py`
- `scripts/test_account_session_smoke.py`
- `scripts/test_auth_session_smoke.py`
- `scripts/test_email_auth_isolation_smoke.py`
- `scripts/test_browser_search_tool_smoke.py`
- `scripts/test_browser_read_tool_smoke.py`

Stable fixture:

- `test_files/sample_rag.txt`

## Current API Surface

Chat:

- `POST /chat`
- `POST /kb_chat`
- `POST /file_chat`
- `POST /chat/completions`
- `POST /chat/feedback`

Conversation:

- `GET /conversations`
- `GET /conversations/{conversation_id}/messages`
- `PATCH /conversations/{conversation_id}`
- `DELETE /conversations/{conversation_id}`

Retrieval and docs:

- `POST /search_docs`
- `GET /documents`
- `GET /documents/{filename}/download`
- `POST /documents/{filename}/reindex`
- `DELETE /documents/{filename}`
- `GET /file_docs/{filename}`
- `GET /chunk/{chunk_id}`

KB:

- `GET /knowledge_bases`
- `POST /knowledge_bases`
- `DELETE /knowledge_bases/{kb_name}`
- `GET /knowledge_bases/{kb_name}/export`
- `POST /knowledge_bases/import`
- `POST /switch_kb`
- `POST /sync_files`

Other:

- `POST /upload`
- `POST /temp_upload`
- `GET /stats`
- `POST /reload`
- `GET /models`

## Known Gaps

Deployment:

- Docker image size is large because `sentence-transformers` pulls PyTorch and CUDA/NVIDIA dependencies in the Linux container.
- Docker image size is still a deferred optimization even after CPU-wheel install.
- Real VPS/cloud deployment rehearsal is still pending.
- SQLite is still a single-host storage choice, not a multi-node production database.
- OAuth state is in memory and should move to Redis or DB TTL storage for multi-process deployments.

Agent:

- Tool Registry is implemented.
- Single-step Tool Calling is implemented.
- One-step Agent Loop with final answer is implemented.
- Multi-step Agent Loop is implemented with a default 3-step limit, a hard 5-step cap, loop guards, compact observations, and `agent-v2` trace persistence.
- Lightweight Planner Loop is implemented on top of the multi-step loop with `agent-v3` planner metadata persistence.
- React Agent Mode UI is implemented.
- React Agent Trace UI restores persisted single-step, multi-step, and planner traces from assistant message metadata.
- Real MCP Integration Foundation is implemented with allowlisted discovery, normalized MCP tool specs, unified registry resolution, and Agent-callable MCP tools.
- Filesystem MCP readonly is implemented with `mcp.filesystem.read_file` and `mcp.filesystem.list_dir`.
- Real MCP stdio transport runtime is implemented with initialize, tools/list, tools/call, shutdown, status, timeout, and process cleanup.
- Filesystem MCP stdio discovery is implemented with `mcp.filesystem_stdio.*` read-only tools.
- SQLite MCP readonly is implemented through real stdio discovery with `mcp.sqlite.query`, `mcp.sqlite.list-tables`, and `mcp.sqlite.describe-table`.
- Agent Streaming SSE is implemented through `POST /agent/plan_run_stream` with planning, step, tool, planner update, token, done, and error events.
- SQLite readonly tool is implemented.
- Filesystem readonly tool is implemented.
- No browser/playwright MCP tools yet.

Deferred:

- Docker image size optimization:
  - CPU-only PyTorch install.
  - separate Docker requirements.
  - model cache volume.
- OCR/PPT/Excel loaders.
- Stronger cross-encoder reranker.
- Query rewrite / multi-query retrieval.
- Multi-provider model UI.
- LangChain integration.

## Next Stage

Recommended order:

1. Agent Foundation:
   - Add browser/playwright tools after safety boundaries are explicit.
   - Add stop-generation controls for streaming Agent runs.
2. Deployment hardening:
   - Docker image size optimization.
   - Production reverse proxy notes.
   - Production CORS settings.

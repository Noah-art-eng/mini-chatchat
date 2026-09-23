# Roadmap

This roadmap is ordered by current project value. The RAG and React core are now mature enough to pause further retrieval expansion after the current phase.

## Phase 1: Stabilized Mini RAG Core

Status: complete

Delivered:

- Formal KB RAG.
- Temp KB / file chat.
- Search engine mode.
- Prompt system.
- FAISS search and persistence.
- Streaming answers.
- Conversation/message storage.
- Feedback.
- Multi-format document loader.
- Chunk management.
- KB metadata/status.
- File reindex.
- KB import/export.
- Optional rerank.
- DeepSeek/OpenAI-compatible model config.

## Phase 2: React UI Core

Status: complete

Delivered:

- React app scaffold.
- API client modules.
- Conversation sidebar.
- Chat area.
- Sources panel.
- KB selector.
- Document list.
- Upload/download/reindex/delete.
- KB import/export.
- Feedback controls.
- Retrieval Debug panel.
- Search engine mode.
- Temp file mode.

## Phase 3: Conversation and Retrieval Productization

Status: complete

Delivered:

- Conversation `updated_time`.
- Conversation list ordering.
- Conversation rename.
- Conversation delete.
- Assistant sources metadata persistence.
- Hybrid Search: BM25 + FAISS.
- Metadata Filter.
- Context Deduplication.
- Context Token Budget.
- Smoke tests for each retrieval enhancement.

## Step 4.1: Unified Smoke Test Runner

Status: complete

Delivered:

- `scripts/run_smoke_tests.py`
- Sequential execution to avoid `/switch_kb` conflicts.
- PASS/FAIL summary.
- Total elapsed time.
- Backend availability check.

## Step 4.2: Environment and Documentation

Status: complete

Delivered:

- `.env.example`
- Updated `README.md`
- Updated `docs/PROJECT_STATE.md`
- Updated `docs/ROADMAP.md`

## Step 4.3: Docker / docker-compose

Status: complete

Delivered:

- Backend Dockerfile.
- React frontend Dockerfile.
- `docker-compose.yml`.
- Root `.dockerignore`.
- Frontend `.dockerignore`.
- Runtime data mounted as volumes:
  - `backend/data`
  - `backend/uploads`
  - `backend/mini.db`
- API keys kept in environment variables.
- Docker startup instructions in `README.md`.

Verified:

- `docker compose build`
- `docker compose up -d`
- `curl http://127.0.0.1:8000/health`
- `curl http://127.0.0.1:8000/health/deps`

## Step 4.4: Health Check / Deployment Hardening

Status: complete

Delivered:

- `GET /health`
- `GET /health/deps`
- Non-secret provider status.
- Database check.
- Runtime directory checks.
- Provider configuration check.
- Embedding model configuration check.
- `scripts/test_health_smoke.py`

Still deferred:

- Docker image size optimization.
- Production reverse proxy notes.
- Production CORS hardening.
- Cloud/VPS deployment walkthrough.

## Phase 5: Agent Foundation

Status: in progress

Delivered:

- Tool Registry.
- Direct tool execution API.
- LLM Tool Calling decision endpoint.
- One-step Agent Loop with final answer.
- Multi-step Agent Loop with max-step guardrails.
- Lightweight Planner Loop with plan metadata persistence.
- Agent trace persistence for single-step and multi-step runs.
- KB search tool.
- Calculator tool.
- Current time tool.
- Mock MCP adapter layer.
- Real MCP Integration Foundation with allowlisted `mcp.demo.echo` discovery/call through the unified registry.
- Filesystem MCP readonly with `mcp.filesystem.read_file` and `mcp.filesystem.list_dir`.
- Real MCP stdio transport runtime with initialize, tools/list, tools/call, shutdown, status, timeout, and cleanup.
- Filesystem MCP stdio discovery with `mcp.filesystem_stdio.*` read-only tools.
- SQLite MCP readonly through real stdio discovery with `mcp.sqlite.query`, `mcp.sqlite.list-tables`, and `mcp.sqlite.describe-table`.
- Agent Streaming SSE through `POST /agent/plan_run_stream` with planner/tool progress and final answer token events.
- SQLite readonly query tool.
- Filesystem readonly read tool.
- React Agent Mode UI.
- Agent tool result UI polish.
- React Agent trace restore from assistant message metadata.
- React Planner panel restore from assistant message metadata.
- Agent smoke tests integrated into `scripts/run_smoke_tests.py`.

Current smoke coverage:

- `scripts/test_tool_registry_smoke.py`
- `scripts/test_agent_tool_calling_smoke.py`
- `scripts/test_agent_loop_smoke.py`
- `scripts/test_multi_step_agent_smoke.py`
- `scripts/test_agent_planner_smoke.py`
- `scripts/test_agent_streaming_smoke.py`
- `scripts/test_agent_trace_persistence_smoke.py`
- `scripts/test_mcp_adapter_smoke.py`
- `scripts/test_real_mcp_integration_smoke.py`
- `scripts/test_real_mcp_transport_smoke.py`
- `scripts/test_sqlite_mcp_readonly_smoke.py`
- `scripts/test_filesystem_mcp_readonly_smoke.py`
- `scripts/test_sqlite_tool_smoke.py`
- `scripts/test_filesystem_tool_smoke.py`

Next suggested steps:

1. Phase 6.8 Playwright MCP controlled browser.
2. Stop Generation for streaming Agent runs.

Rules:

- Do not introduce Agent until Docker/deployment basics are stable.
- Do not mix Agent work with further RAG retrieval experiments.
- Keep tools structured, observable, and testable.

## Deferred Items

- Docker image size optimization:
  - CPU-only PyTorch install.
  - separate Docker requirements.
  - model cache volume.
- Production deployment rehearsal on a real VPS/cloud host.
- OAuth state durable storage for multi-process production.
- Optional managed PostgreSQL/object storage migration.
- OCR/image document parsing.
- PPT/Excel loaders.
- Cross-encoder reranker.
- Query rewrite.
- Multi-query retrieval.
- Multi-provider model UI.
- LangChain integration.

## Phase 11: Production Deployment And DevOps Hardening

Status: complete for single-host production-readiness candidate

Delivered:

- Backend multi-stage Dockerfile.
- Non-root backend runtime user.
- CPU PyTorch wheel index for backend dependency install.
- Frontend nginx production image.
- nginx `/api` reverse proxy with SSE buffering disabled.
- `docker-compose.dev.yml`.
- `docker-compose.prod.yml`.
- Healthchecks and restart policies.
- Configurable DB/data/uploads paths.
- `.env.production.example`.
- Request ID and structured request logs.
- Runtime metadata and non-secret stats in health responses.
- `scripts/backup.sh`.
- `scripts/restore.sh`.
- Deployment docs under `docs/deployment/`.
- `CHANGELOG.md`.
- `docs/release/v1.0-production-ready.md`.

Remaining production limitations:

- Real public deployment rehearsal is still required.
- SQLite remains single-host only.
- OAuth state is still in memory.
- Backend image size can still be reduced further.
- Browser QA depends on local Playwright/browser availability.

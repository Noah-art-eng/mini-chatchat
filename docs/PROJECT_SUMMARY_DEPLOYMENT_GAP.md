# Mini ChatChat Project Summary and Deployment Gap

Last updated: 2026-08-04

## 1. Executive Summary

Mini ChatChat has moved beyond a RAG demo. It is now a ChatChat-inspired AI application with a complete local knowledge-base workflow, temporary file chat, web-search mode, conversation history, source attribution, feedback, React product UI, agent tool calling, MCP tool integration, Docker Compose startup, health checks, and a unified smoke test runner.

The project is currently strong enough to present as a portfolio project. The main remaining work before a real public deployment is operational hardening: secrets, CORS, reverse proxy/TLS, authentication or access control, persistent storage strategy, backup policy, image-size optimization, and production smoke verification.

## 2. Current Product State

### Core RAG

Completed:

- Local knowledge-base RAG through `/kb_chat` with `mode=local_kb`.
- Temporary file chat through `/temp_upload` and `mode=temp_kb`.
- Search-engine mode through `mode=search_engine`.
- Streaming SSE with `sources`, `token`, `done`, and error events.
- `return_direct` retrieval-only mode for debugging and source inspection.
- OpenAI-compatible `/chat/completions` endpoint.
- Prompt templates: `default`, `empty`, `strict`.
- DeepSeek-first provider configuration with OpenAI-compatible fallback.

Retrieval quality:

- FAISS vector search.
- BM25 keyword search.
- Hybrid Search merge.
- Metadata filter by file/source.
- Optional lightweight rerank.
- Context deduplication.
- Context token budget before prompt construction.

### Knowledge Base Management

Completed:

- KB create/list/delete/switch.
- Multi-format document loader: `.txt`, `.pdf`, `.docx`, `.md`, `.csv`.
- Upload, download, delete, reindex.
- Chunk size and overlap configuration.
- File metadata/status:
  - `uploaded`
  - `indexed`
  - `failed`
- KB export/import zip with `metadata.json`.
- FAISS persistence under `backend/data/{kb_name}/vector_store/`.

### Conversation and Feedback

Completed:

- Conversation list.
- Message history restore.
- Conversation rename/delete.
- `updated_time` ordering.
- Assistant message IDs.
- Feedback score/reason.
- Assistant sources persisted in message metadata.
- React conversation sidebar with grouping and destructive action confirmation.

### Agent and Tools

Completed:

- Tool Registry.
- Direct tool execution API.
- LLM tool-call decision endpoint.
- One-step and multi-step Agent loops.
- Planner-style Agent flow.
- Agent streaming SSE.
- Agent trace persistence and restore.
- React Agent Mode UI.
- Tool Center product UI.

Available tool families:

- Calculator.
- Current time.
- Knowledge search.
- SQLite readonly query.
- Filesystem readonly read.
- Browser read.
- Browser search.
- MCP adapter and real stdio transport.
- Filesystem MCP readonly.
- SQLite MCP readonly.

Current constraint:

- Browser/Playwright MCP tools are not fully productized as controlled browser automation tools. The project has browser read/search tools, but not a full browser-control agent workflow.

### Frontend

Completed:

- React + Vite + TypeScript frontend in `frontend-react/`.
- Product shell with navigation.
- Chat workspace.
- Knowledge workspace.
- Agent workspace.
- System workspace.
- Tool Center.
- Sources panel.
- Retrieval Debug in Developer Mode.
- Design tokens and foundational UI components.
- ESLint, TypeScript, Vitest smoke tests.

Legacy:

- `frontend/` plain HTML/CSS/JS remains for compatibility but is no longer the primary UI.

### Testing

Completed:

- Unified runner: `scripts/run_smoke_tests.py`.
- Backend smoke tests for:
  - provider/model config
  - core React API surface
  - conversation API
  - temp KB
  - hybrid search
  - metadata filter
  - context dedup
  - context token budget
  - KB import/export
  - tool registry
  - agent tool calling
  - agent loop
  - multi-step/planner/streaming agent
  - MCP adapter/transport
  - SQLite/filesystem/browser tools

Frontend checks:

- `npm run typecheck`
- `npm run build`
- `npm run lint`
- `npm run test`

## 3. Current Architecture

Backend:

- `backend/app.py`: FastAPI routes and request models.
- `backend/chat_service.py`: KB chat orchestration and streaming response assembly.
- `backend/rag.py`: chunking, prompt context, context budget, answer generation.
- `backend/db.py`: SQLite schema, migrations, KB metadata, conversations, messages, feedback.
- `backend/model_config.py`: DeepSeek/OpenAI provider selection.
- `backend/services/kb_service.py`: KB state, FAISS persistence, hybrid search, metadata filter, dedup.
- `backend/services/tools/`: local tool implementations and registry.
- `backend/services/mcp_*`: MCP adapter, registry, transport, and types.
- `backend/agent_service.py`: tool decision, agent loop, planner, streaming.

Frontend:

- `frontend-react/src/pages/App.tsx`: app routing state.
- `frontend-react/src/components/AppShell.tsx`: product shell.
- `frontend-react/src/features/chat/`: Chat workspace container.
- `frontend-react/src/features/conversation/`: conversation sidebar.
- `frontend-react/src/components/kb/`: Knowledge workspace.
- `frontend-react/src/components/agent/`: Agent workspace.
- `frontend-react/src/components/system/`: System and Tool Center.
- `frontend-react/src/components/ui/`: foundation UI components.
- `frontend-react/src/styles/tokens.css`: design tokens.

Deployment:

- `backend/Dockerfile`
- `frontend-react/Dockerfile`
- `docker-compose.yml`
- Runtime volumes:
  - `backend/data`
  - `backend/uploads`
  - `backend/mini.db`

## 4. Deployment Readiness

### Already Ready

- Docker Compose can build and run backend/frontend locally.
- Backend exposes `/health` and `/health/deps`.
- Runtime data is mounted outside the image.
- API keys are read from environment variables.
- `.env.example` exists and does not include secrets.
- Smoke tests can validate core flows against a running backend.
- React frontend has build/typecheck/lint/test scripts.

### Not Yet Production Ready

The project should not be deployed publicly without addressing these items:

1. Access control
   - There is no login, user isolation, or admin boundary.
   - If deployed publicly, add authentication or restrict access through a private network/reverse proxy.

2. Secrets management
   - Real API keys must live in deployment secrets, not committed files.
   - Confirm `.env`, `backend/.env`, and runtime DB/data paths are ignored.

3. CORS hardening
   - Development CORS is acceptable locally.
   - Production should allow only the deployed frontend origin.

4. Reverse proxy and TLS
   - Add Nginx/Caddy/Traefik or platform-level HTTPS.
   - Route frontend and backend consistently under one domain or subdomains.

5. Persistent storage and backups
   - SQLite database, uploaded files, parsed content, and FAISS vector stores need a backup policy.
   - KB export/import is implemented, but scheduled backup is not.

6. Docker image size
   - Backend image is likely large because `sentence-transformers` pulls PyTorch dependencies.
   - Consider CPU-only PyTorch wheels, a separate Docker requirements file, and model cache volumes.

7. Model and embedding cache
   - First startup can be slow if embedding models download at runtime.
   - Production should pre-cache or mount model cache.

8. Observability
   - Health checks exist, but structured logs, request tracing, and metrics are minimal.

9. Rate limiting and upload limits
   - Public deployment needs limits for uploads, chat calls, agent runs, and tool execution.

10. Frontend API base URL
   - Docker build currently injects `VITE_API_BASE_URL`.
   - Production needs a clear value for domain/subdomain deployment.

## 5. Recommended Path to Deployment

### Step 1: Local Release Verification

Run:

```bash
cd frontend-react
npm run typecheck
npm run lint
npm run test
npm run build
```

Then start backend and run:

```bash
python3 scripts/run_smoke_tests.py
```

### Step 2: Docker Verification

Run:

```bash
docker compose config
docker compose build
docker compose up -d
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/deps
```

Then run the smoke runner against the Docker backend:

```bash
MINI_CHATCHAT_API_BASE=http://127.0.0.1:8000 python3 scripts/run_smoke_tests.py
```

### Step 3: Production Configuration

Prepare:

- Domain name.
- HTTPS reverse proxy.
- Production `.env` values.
- Persistent volume paths.
- Backup directory or object storage target.
- CORS allowed origin.
- Upload size limit.
- Access control strategy.

### Step 4: Production Smoke

After deployment, verify:

- `/health`
- `/health/deps`
- `/models`
- local KB upload/search/chat
- temp KB upload/chat
- search engine mode
- conversation create/restore/delete
- agent run
- tool registry listing
- KB export/import

## 6. Remaining Distance to Deployment

Estimate for a local/VPS portfolio deployment:

- Small deployment: 1-2 days.
- Polished public deployment: 3-5 days.

Minimum remaining work:

- Add production CORS settings.
- Put the app behind HTTPS.
- Decide access control.
- Verify Docker runtime volumes.
- Run full smoke tests in the target environment.
- Document deployment commands.

Recommended production hardening:

- Add auth or reverse-proxy basic auth.
- Add upload and request limits.
- Add backup/restore instructions for SQLite and KB data.
- Optimize backend Docker image size.
- Pre-cache embedding model.
- Add structured logging.
- Add a simple production troubleshooting guide.

## 7. Portfolio Value

This project is resume-worthy because it demonstrates:

- Full-stack AI product engineering.
- RAG pipeline design without hiding everything behind LangChain.
- Retrieval quality improvements beyond a basic vector search demo.
- Knowledge-base file management and persistence.
- Streaming UX and source attribution.
- Agent tool calling and MCP integration foundations.
- React product UI and design-system refactor work.
- Docker and smoke-test driven engineering discipline.

Suggested short resume line:

> Built Mini ChatChat, a FastAPI + React RAG/Agent platform with FAISS hybrid search, knowledge-base management, streaming chat, conversation history, DeepSeek/OpenAI-compatible provider config, tool calling, MCP integration, Docker Compose deployment, and end-to-end smoke tests.

## 8. Next Recommended Work

Do this before adding more AI features:

1. Production deployment hardening.
2. Auth or private access control.
3. Backup/restore documentation.
4. Docker image-size optimization.
5. Production smoke-test checklist.

After deployment is stable, resume feature work:

1. Controlled browser/Playwright MCP tools.
2. Stop generation for streaming Agent runs.
3. More robust Agent run observability.
4. Optional stronger document loaders such as OCR/PPT/Excel.

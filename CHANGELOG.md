# Changelog

## v1.0.0-rc.1 - Public Demo Release Candidate

### Added

- React product UI for Chat, Knowledge, Agent, Tools, System, and Account.
- Local KB RAG, temp file chat, search-engine mode, and OpenAI-compatible chat completions.
- Conversation history, rename/delete, feedback, and persisted assistant sources.
- Knowledge Base management with upload, download, reindex, delete, import, and export.
- Hybrid Search, metadata filtering, context deduplication, and context token budget.
- DeepSeek-first OpenAI-compatible model provider configuration.
- Agent tool registry, tool calling, multi-step planner, streaming, and trace persistence.
- Read-only local tools for calculator, time, KB search, SQLite, filesystem, browser search, and browser read.
- MCP adapter foundation, real stdio transport, filesystem MCP readonly, and SQLite MCP readonly.
- Email registration/login, HttpOnly refresh cookie, refresh rotation, session management, account page, Google OAuth, GitHub OAuth, and user-scoped data isolation.
- Health checks, structured request logs, request id propagation, runtime metadata, and deployment stats.
- Development and production Docker Compose files.
- Production nginx reverse proxy for React static assets and `/api` backend routing.
- Backup and restore scripts.
- Deployment documentation and production checklist.
- Unified smoke runner with 30 sequential backend/API smoke tests.
- OAuth provider setup guide, demo script, architecture diagram, and release candidate readiness report.

### Changed

- Docker backend now uses a multi-stage build, CPU PyTorch wheel index, non-root runtime user, and model cache volume paths.
- Frontend Docker image now serves React through nginx and proxies `/api` to the backend.
- SQLite path, data root, and uploads directory can be configured with environment variables.
- README now focuses on Docker production, smoke tests, backup/restore, and deployment docs.
- React frontend uses a small internal router instead of `react-router-dom` to keep production dependencies clean.

### Security

- Production mode rejects weak auth defaults.
- OAuth state and PKCE are enforced.
- Mutating auth endpoints use Origin validation.
- Session list and OAuth provider APIs return only safe public fields.
- Public production `/health/deps` exposes only status and dependency checks unless detail exposure is explicitly enabled.
- Frontend `npm audit` and `npm audit --omit=dev` report zero vulnerabilities.
- Backup archives include checksums and restore now requires explicit confirmation.

### Known Issues

- SQLite is suitable for single-host deployment, not multi-node high-concurrency production.
- OAuth transaction state is in memory and should move to Redis or DB TTL storage for multi-process deployments.
- Backend Docker image can remain large because of embedding dependencies.
- Real Google/GitHub OAuth callback verification requires live provider credentials.
- Python/container vulnerability scanning should be automated in CI before internet-facing production.
- OCR, PPT, Excel, multi-provider model UI, and Playwright MCP browser tools are deferred.

# Phase 10.4 Auth Regression Stabilization

## Goal

Phase 10.4 stabilizes the test and error-handling surface after email auth and user-scoped data isolation. It does not add OAuth, refresh tokens, account settings, new AI features, new tools, or frontend product behavior.

## What Changed

- Added `scripts/smoke_auth.py` as the shared smoke-test auth helper.
- Updated protected smoke tests to create a real email user and send `Authorization: Bearer <token>`.
- Updated the unified smoke runner to use the project virtual environment by default.
- Extended the email auth isolation smoke test to cover more cross-user resources.
- Normalized selected private-resource errors from `200 + {"error": ...}` to HTTP 404.
- Added frontend auth regression tests for token injection, 401 token cleanup, and login state.

## Original Failure State

Before this stabilization pass, the unified smoke runner was effectively at:

- PASS: 6
- FAIL: 21
- SKIP: 0
- ENVIRONMENT ERROR: 0 in runner terminology, though two failures were caused by running outside the project virtual environment.

Failure categories:

- Protected endpoint tests still ran as Guest: KB management, document actions, KB import/export, Agent, MCP, SQLite, filesystem, and browser-agent tests received expected 403 responses.
- Test cleanup treated scoped 404 as failure: authenticated test users do not necessarily own legacy test KBs, so `DELETE /knowledge_bases/{name}` may correctly return 404 during cleanup.
- Direct `kb_search` tool route missed request user scope: Agent-driven `kb_search` was scoped, but direct Tool Registry execution did not inject `_user_id`.
- Private resource errors were inconsistent: `/kb_chat`, `/file_docs/{filename}`, and `/chunk/{chunk_id}` could return `200 + error/empty` instead of a private-resource 404.
- Some tests were vulnerable to system Python execution: dependencies such as `openai` and `sentence_transformers` are guaranteed in `.venv`, not necessarily in the shell Python.

## Smoke Auth Helper

`scripts/smoke_auth.py` provides:

- unique test email generation
- email registration
- access-token headers
- authenticated request helpers
- private default KB bootstrap for authenticated Agent/RAG tests
- password/token log scrubbing helpers

The helper does not print the test password or JWT access token.

## Test Categories

### Guest-Compatible Tests

These continue to run without a token:

- `/health`
- `/health/deps`
- `/models`
- ordinary `/kb_chat`
- `search_engine`
- `temp_kb`
- auth register/login primitives

### Authenticated Tests

These now run with a real JWT:

- KB create/delete/import/export
- document upload/download/reindex/delete
- authenticated KB RAG smoke tests
- Agent run/plan/stream tests
- MCP tests
- SQLite tool tests
- filesystem tool tests
- protected tool execution

### Cross-User Tests

`scripts/test_email_auth_isolation_smoke.py` now verifies User B cannot access User A resources across:

- conversation list and messages
- conversation rename/delete
- assistant feedback
- KB list/switch/export/delete
- document list/download/reindex/delete
- file docs
- chunk lookup
- search_docs
- local_kb `/kb_chat`
- temp_kb `/kb_chat`
- direct `kb_search` tool run
- Agent `kb_search`
- user preferences

## HTTP Status Semantics

The stabilized semantics are:

- `401`: invalid, expired, inactive, or malformed authentication.
- `403`: valid identity lacks the capability, such as Guest using Agent/MCP or privileged local tools.
- `404`: authenticated user requests a concrete private resource outside their scope.

The route layer now maps local KB, temp KB, and conversation-not-found `/kb_chat` responses to HTTP 404 for non-streaming resource errors. `/file_docs/{filename}` and `/chunk/{chunk_id}` also return 404 when the current user scope cannot see the resource.

## Real Bugs Found

- `/agent/tools/kb_search/run` did not inject the current scoped user id, so direct tool testing did not enforce the same user boundary as Agent `kb_search`.
- `/kb_chat` returned `200 + {"error": ...}` for missing local KB, temp KB, and conversation resources.
- `/file_docs/{filename}` and `/chunk/{chunk_id}` did not consistently return 404 for resources outside the current user scope.

These were fixed with route-layer and tool-invocation changes only. RAG retrieval, SSE events, Agent planner logic, MCP protocol, and Tool Registry IDs were not changed.

## Direct Tool Scope

`/agent/tools/kb_search/run` now injects the current scoped `user_id` before executing the tool. This makes direct Tool Registry tests follow the same ownership boundary as Agent-driven `kb_search`.

## Smoke Runner

`scripts/run_smoke_tests.py` now:

- uses `.venv/bin/python` by default when available
- keeps tests sequential
- reports `PASS`, `FAIL`, `SKIP`, and `ENVIRONMENT ERROR`
- continues after individual script failures
- exits nonzero for real failures or environment errors
- prints summary counts and total elapsed time

Current verified result:

- total tests: 27
- PASS: 27
- FAIL: 0
- SKIP: 0
- ENVIRONMENT ERROR: 0
- elapsed: 138.9s

## Frontend Regression Coverage

Added `frontend-react/src/auth/auth-regression.test.tsx`.

Coverage:

- shared API client attaches `Authorization: Bearer <token>`
- `401` with stored token clears local session and emits auth-expired event
- `AuthProvider.login()` stores the token and exposes authenticated user state

## Auth API Access Matrix

| Endpoint | Guest | Authenticated | Notes |
| --- | --- | --- | --- |
| `POST /auth/register` | allowed | allowed | creates email user |
| `POST /auth/login` | allowed | allowed | returns JWT |
| `POST /auth/logout` | allowed | allowed | stateless backend logout |
| `GET /auth/me` | allowed | allowed | Guest returns runtime guest; invalid token is 401 |
| `GET /auth/preferences` | 401 | allowed | user preferences only |
| `PATCH /auth/preferences` | 401 | allowed | user preferences only |
| `GET /models` | allowed | allowed | no API key exposure |
| `GET /health` | allowed | allowed | no API key exposure |
| `GET /health/deps` | allowed | allowed | no API key exposure |
| `POST /kb_chat` local/search/temp | allowed | allowed | scoped to Demo or authenticated user |
| `POST /temp_upload` | allowed | allowed | scoped temp files |
| Conversation list/messages/rename/delete | allowed | allowed | scoped to Demo or authenticated user |
| `POST /chat/feedback` | allowed | allowed | message ownership enforced |
| `GET /knowledge_bases` | allowed | allowed | scoped list |
| KB create/delete/import/export/sync | 403 | allowed | KB management permission required |
| Document upload/download/reindex/delete | 403 | allowed | KB management permission required |
| `GET /file_docs/{filename}` | allowed | allowed | current KB scope; missing is 404 |
| `GET /chunk/{chunk_id}` | allowed | allowed | current KB scope; missing is 404 |
| `GET /agent/tools` | allowed | allowed | registry listing only |
| direct `calculator`, `current_time`, `browser_search`, `browser_read`, `kb_search` | allowed | allowed | `kb_search` is user-scoped |
| direct `filesystem_readonly_read` | 403 | allowed | filesystem permission required |
| direct `sqlite_readonly_query` | 403 | allowed | sqlite permission required |
| Agent run/plan/stream APIs | 403 | allowed | Agent permission required |
| MCP APIs | 403 | allowed | MCP permission required |

## Verification

Backend:

- `.venv/bin/python -m py_compile backend/app.py backend/db.py backend/chat_service.py backend/agent_service.py backend/auth/*.py scripts/smoke_auth.py scripts/run_smoke_tests.py scripts/test_email_auth_isolation_smoke.py`
- `MINI_CHATCHAT_API_BASE=http://127.0.0.1:8001 .venv/bin/python scripts/test_email_auth_isolation_smoke.py`
- `MINI_CHATCHAT_API_BASE=http://127.0.0.1:8001 .venv/bin/python scripts/run_smoke_tests.py`

Frontend:

- `npm run typecheck`
- `npm run lint`
- `npm run test`
- `npm run build`

## Known Limits

- JWTs are still stored in `localStorage`; production should move to HttpOnly Secure SameSite cookies.
- No refresh token rotation yet.
- No OAuth providers yet.
- No password reset or email verification yet.
- Smoke tests create disposable test users and runtime data; cleanup of all generated users is not implemented.
- Browser QA was limited to `/`, `/login`, and `/register` loading checks with console and failed-network capture.

## Next Work

Phase 10.5 should focus on production auth hardening before OAuth:

- HttpOnly cookie session mode
- refresh token rotation or short-lived access tokens
- CSRF strategy if cookie auth is enabled
- account profile page
- explicit logout/session expiration UX
- optional Demo-to-private-workspace migration

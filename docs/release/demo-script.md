# Mini ChatChat Demo Script

This script is designed for a 5 to 8 minute portfolio, GitHub, or interview walkthrough.

Do not show `.env`, API keys, cookies, JSON Web Tokens (JWTs), refresh tokens, OAuth secrets, private email inboxes, or real user data during the demo.

## Recording Asset

An actual demo recording is available at:

```text
docs/release/media/github-readme/mini-chatchat-demo.mov
```

Recording summary:

- Duration: about 103 seconds
- Format: QuickTime MOV
- Video/audio: H.264 video with AAC audio
- Resolution: 4096 x 2164
- Size: about 50 MB

The current recording is suitable as a short GitHub README showcase. It does not cover the full 5 to 8 minute script below. Missing or only partially covered flows include full KB upload/indexing, temp file chat, Agent tool execution, Tool Center explanation, Docker terminal proof, and backup/restore discussion.

## Setup

Operation:

```bash
cp .env.production.example .env.production
mkdir -p runtime/prod
docker compose -f docker-compose.prod.yml up --build -d
curl http://127.0.0.1/api/health
```

Narration:

Mini ChatChat runs as a Docker Compose application with a React frontend served by nginx and a FastAPI backend exposed through `/api`.

Expected result:

- Frontend opens at `http://127.0.0.1/`
- `/api/health` returns status `ok`
- Backend and frontend containers are healthy

Interview point:

This shows the project is not just a local dev server. It has a reproducible private demo runtime.

Fallback:

If Docker is unavailable, run the backend and frontend locally:

```bash
cd backend
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend-react
npm run dev -- --host 127.0.0.1 --port 5173
```

## 1. Product Positioning

Operation:

Open the Chat workspace.

Narration:

Mini ChatChat is a full-stack AI knowledge workspace inspired by the core LangChain-Chatchat experience. It supports local knowledge-base RAG, web search, temporary file chat, source-aware answers, Agent tool calling, MCP integration, user auth, user isolation, and Docker deployment.

Expected result:

- The Chat workspace is visible
- Version and current runtime information are visible in the product shell

Interview point:

Emphasize that the retrieval pipeline is inspectable and not hidden behind LangChain.

Fallback:

If the product shell is slow to load, show `curl http://127.0.0.1/api/health` and then refresh the browser.

## 2. Guest Mode

Operation:

Use the app without logging in.

Narration:

Guest users can use basic chat, search, and temp file flows. More sensitive features such as Knowledge management, Agent tools, MCP, filesystem tools, SQLite tools, and Developer Mode are permission controlled.

Expected result:

- Chat is available
- Search mode is visible
- Locked capabilities explain that sign-in is required

Interview point:

This demonstrates progressive access control rather than hiding unfinished features.

Fallback:

If guest permissions are not obvious, open Knowledge or Agent and point out the sign-in prompt.

## 3. Registration And Login

Operation:

Open `/register` or `/login`, then use a prepared demo account.

Narration:

The app supports email registration, login, HttpOnly refresh cookies, refresh rotation, session management, and user-scoped data.

Expected result:

- The account menu shows the signed-in user
- Account page shows profile and sessions
- The browser does not expose refresh tokens to JavaScript

Interview point:

Explain that auth is integrated with user-scoped conversations, KBs, files, and sessions.

Fallback:

If a demo account already exists, log in instead of registering a new one.

## 4. Onboarding

Operation:

Show the first-run onboarding or describe it from the current state.

Narration:

Onboarding introduces the available modes without forcing users into developer settings. Guest preferences remain local; authenticated user preferences are stored on the server.

Expected result:

- The user can understand local KB, temp file, search, and Agent modes
- Onboarding can be completed or skipped

Interview point:

This is product polish, not only backend capability.

Fallback:

If onboarding has already been completed, mention that it is controlled by user preferences.

## 5. Create A Knowledge Base

Operation:

Open Knowledge, select or create a demo KB if available, and inspect the document area.

Narration:

The Knowledge workspace manages the document lifecycle for local RAG: upload, index, inspect, reindex, delete, import, and export.

Expected result:

- The current KB is visible
- Document list or empty upload state is visible

Interview point:

Point out that KB metadata is persisted in SQLite while vectors live in FAISS files under user-scoped storage.

Fallback:

If KB creation is not needed, use the default KB and continue to upload.

## 6. Upload A Document

Operation:

Upload a small `.txt` or `.md` file without private data.

Narration:

The backend parses supported formats, splits content into chunks, stores metadata, and updates the FAISS index.

Expected result:

- Upload status becomes successful
- Document row appears with status and chunk metadata

Interview point:

Mention supported formats: `.txt`, `.pdf`, `.docx`, `.md`, and `.csv`.

Fallback:

If upload fails because the user is not signed in, log in and retry. If parsing fails, use a simple text file.

## 7. Local KB Chat

Operation:

Switch Chat to local knowledge-base mode and ask a question about the uploaded document.

Narration:

Local KB chat retrieves context through FAISS + BM25 hybrid search, applies optional rerank, deduplicates chunks, limits prompt context, and streams the answer.

Expected result:

- User message appears
- Assistant response streams in
- Sources are available after the answer

Interview point:

This is the main RAG path:

```text
Question -> Retrieve -> Context -> Prompt -> LLM -> Answer
```

Fallback:

If the model provider is not configured, use return-direct retrieval or show the stored sources/debug result.

## 8. Sources

Operation:

Open the Sources panel from the assistant answer.

Narration:

Sources are not temporary UI state only. Assistant message source metadata is persisted so historical conversations can restore related sources.

Expected result:

- Source cards show file name, chunk preview, and retrieval scores when available

Interview point:

This is useful for auditability and debugging hallucination risk.

Fallback:

If a historical message has no saved sources, show the explicit empty state instead of pretending sources exist.

## 9. Web Search

Operation:

Switch to Search mode and ask a public-information question.

Narration:

Search mode sends `mode: "search_engine"` and does not pass a KB name. It is useful for current public information, while exact time questions are better handled by the Agent current_time tool.

Expected result:

- Assistant uses search mode
- Sources show web URLs when the search backend returns them

Interview point:

Mention the routing fix: current-time questions can route to the safer time tool instead of relying on web search.

Fallback:

If external search is unavailable, show that the UI reports an error state rather than silently falling back to local KB.

## 10. Temp File Chat

Operation:

Switch to temp file mode, upload a small temporary file, then ask a question.

Narration:

Temp file chat lets users ask about a one-off file without importing it into a persistent knowledge base.

Expected result:

- Temp file upload succeeds
- Question uses `mode: "temp_kb"`
- Sources point to the temp file

Interview point:

This demonstrates separate local KB and temp KB scopes.

Fallback:

If no temp file is uploaded, show the clear error state that asks the user to upload a file first.

## 11. Agent

Operation:

Switch to Agent mode and ask:

```text
What is 25 * 8 and what is the current UTC time?
```

Narration:

Agent mode asks the model to choose tools from a safe registry. It can call calculator, current_time, KB search, browser tools, filesystem readonly, SQLite readonly, and MCP adapter tools depending on configuration and permissions.

Expected result:

- Timeline shows selected tool calls
- Tool observations are visible
- Final answer appears

Interview point:

The project separates tool decision, execution, observation, and final answer generation.

Fallback:

If model tool choice is unstable, run a simpler prompt such as `Calculate 25 * 8`.

## 12. Tool Center

Operation:

Open the System or Tool Center area and show tool categories.

Narration:

Tools are presented as product capabilities, not raw internal IDs. Developer Mode can reveal schemas and IDs when needed.

Expected result:

- Tool categories are readable
- Common tools such as calculator, knowledge search, browser search, filesystem readonly, and SQLite readonly are visible

Interview point:

This shows how product UX and tool safety are connected.

Fallback:

If Developer Mode is disabled, describe that technical details are intentionally hidden for normal users.

## 13. Account And Sessions

Operation:

Open Account and show profile plus sessions.

Narration:

The app supports account profile editing, current session display, revoking other sessions, logout other devices, and logout all devices.

Expected result:

- Current session is marked
- Session actions are available with confirmation

Interview point:

This is beyond a basic demo login. It demonstrates real session management and user isolation.

Fallback:

If there is only one session, explain the multi-device path and show the session API behavior if needed.

## 14. System

Operation:

Open System.

Narration:

System shows provider/model status, dependency checks, tool registry, MCP status, runtime version, and health.

Expected result:

- Health is readable
- Runtime version matches the release candidate

Interview point:

This supports operational debugging without exposing secrets.

Fallback:

Use:

```bash
curl http://127.0.0.1/api/health
curl http://127.0.0.1/api/health/deps
```

## 15. Docker And Architecture

Operation:

Show the architecture diagram in README and optionally run:

```bash
docker compose -f docker-compose.prod.yml ps
```

Narration:

The deployable shape is Browser -> nginx -> React/FastAPI -> Auth/Chat/RAG/Agent -> SQLite/FAISS/uploads/model provider.

Expected result:

- Containers are healthy
- README architecture is easy to explain

Interview point:

Mention backup/restore, health checks, nginx proxy, and 30/30 smoke tests.

Fallback:

If Docker is not running, show `docs/release/v1.0-release-candidate-readiness.md`.

## Closing Summary

Narration:

Mini ChatChat is portfolio-ready and suitable for local or Docker-based private demos. It does not currently provide a public hosted demo. Google/GitHub OAuth flows are implemented, but live provider verification requires real production credentials and callback configuration.

Known demo limits:

- No public hosted demo
- Single-node SQLite architecture
- Backend image is about 2 GB
- No email verification or password reset yet
- Backup is local archive only
- Public production deployment still requires HTTPS, monitoring, and shared infrastructure

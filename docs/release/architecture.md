# Mini ChatChat v1.0 Architecture

```mermaid
flowchart LR
  User["Browser User"] --> Proxy["Frontend nginx / Caddy"]
  Proxy --> React["React App"]
  Proxy --> API["FastAPI Backend"]

  API --> Auth["Auth + Sessions"]
  API --> Chat["Chat Service"]
  API --> KB["Knowledge Base Service"]
  API --> Agent["Agent Service"]
  API --> Tools["Tool Registry / MCP Adapter"]

  Auth --> SQLite["SQLite"]
  Chat --> KB
  Chat --> LLM["DeepSeek or OpenAI-compatible LLM"]
  KB --> FAISS["FAISS Vector Store"]
  KB --> Files["User-scoped Files"]
  Agent --> Tools
  Tools --> SQLite
  Tools --> Files
  Tools --> Web["Browser Search"]

  SQLite --> Backup["Backup Archive"]
  FAISS --> Backup
  Files --> Backup
```

## Runtime Boundaries

- React is served as static production assets.
- nginx proxies `/api` requests and keeps SSE buffering disabled.
- FastAPI owns auth, chat, RAG, Agent, tools, health, and import/export APIs.
- SQLite stores users, sessions, conversations, messages, KB metadata, OAuth links, and preferences.
- Runtime data is mounted under `runtime/prod` in production Compose.
- Backup and restore cover SQLite, user-scoped knowledge files, uploads, extracted content, and FAISS indexes.

## Security Boundaries

- Browser receives only short-lived access tokens.
- Refresh token is stored in an HttpOnly cookie.
- OAuth provider tokens are not persisted.
- Public health details are restricted in production unless explicitly enabled.
- Agent filesystem and SQLite tools are read-only and scoped.

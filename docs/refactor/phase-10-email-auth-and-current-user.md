# Phase 10.3 Email Auth and Current User

## Goal

Phase 10.3 adds real email/password registration and login on top of the Phase 10.1 auth foundation and Phase 10.2 user isolation. It keeps the existing public chat, RAG, SSE, Agent, MCP, and Tool Registry contracts intact while routing authenticated requests through the JWT user identity.

This phase does not implement OAuth, refresh tokens, password reset, email verification, phone login, RBAC tiers, billing, or account management.

## Auth Flow

### Register

`POST /auth/register`

```json
{
  "email": "user@example.com",
  "password": "at least 8 characters",
  "display_name": "Optional display name"
}
```

Behavior:

- normalizes email to lowercase
- validates basic email format
- requires a minimum 8 character password
- rejects duplicate emails with a generic `invalid email or password` error
- stores a PBKDF2 password hash, never plaintext
- creates a default KB for the new user scope
- returns an access token and public user object

### Login

`POST /auth/login`

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

Behavior:

- checks only email-provider users
- rejects wrong password, unknown user, and inactive user with the same generic error
- returns `access_token`, `token_type`, `expires_in`, and public user fields

### Logout

`POST /auth/logout`

The backend is stateless. Logout returns success and the frontend removes its stored access token.

### Current User

`GET /auth/me`

- no token: returns runtime Guest user with `authenticated=false`
- valid token: returns authenticated user with `authenticated=true`
- invalid, expired, or inactive token: returns 401

## JWT Payload

Access tokens are HS256 JWTs created by `backend/auth/jwt.py`.

Payload fields:

- `iss`: issuer from `AUTH_ISSUER`, default `mini-chatchat`
- `sub`: string user id
- `uid`: numeric user id
- `email`: user email
- `iat`: issued-at Unix timestamp
- `exp`: expiration Unix timestamp

Token lifetime is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES`, default 1440 minutes.

## Password Strategy

Passwords use PBKDF2-HMAC-SHA256 with a random per-password salt and 210,000 iterations in `backend/auth/password.py`.

The stored format is:

```text
pbkdf2_sha256$iterations$salt$digest
```

This avoids plaintext passwords and avoids custom reversible encryption. A production deployment should consider Argon2id or bcrypt through a maintained password library once dependencies are finalized.

## Current User Injection

Routes now use FastAPI dependencies from `backend/auth/dependencies.py`:

- `get_current_user_optional`: guest fallback if no token, 401 for invalid token
- `get_current_user`: requires authenticated user
- `get_request_user_id`: maps guest to `None` and authenticated users to their integer id
- `require_permission`: central permission enforcement

Request-scoped helpers in `backend/app.py` map the current user to:

- DB `user_id`
- current KB selection key
- `MiniKBService(..., user_id=user_id)`
- user-scoped upload/content/vector-store paths
- user-scoped temp KB root

Authenticated requests always override the Demo fallback. Unauthenticated requests continue to resolve to the Demo User through the existing `user_id=None` compatibility path.

## Scoped Backend Resources

Authenticated identity is passed through:

- `/kb_chat`
- `/chat/completions`
- conversation list/messages/rename/delete
- feedback
- local KB chat
- temp upload and temp file chat
- document upload/download/reindex/delete
- KB list/create/switch/delete/import/export/sync
- file docs and chunk lookup through current scoped KB service
- Agent run endpoints
- Agent persisted traces and messages
- `kb_search` tool defaults

Cross-user access returns 404 for private resources where possible, avoiding disclosure of whether another user's resource exists.

## Guest Compatibility

Unauthenticated requests remain supported for:

- ordinary chat
- local KB read/chat against the Demo workspace
- search mode
- temp file upload/chat
- conversation history in the Demo workspace

Guests are runtime identities and are not written to the `users` table. The Demo User still owns legacy data and unauthenticated persistent rows.

## Permission Enforcement

Guest permissions:

- chat
- web search
- temp file chat

Authenticated users:

- all current capabilities

Protected backend capabilities now include:

- KB management
- document upload/download/reindex/delete
- KB import/export/delete/create/sync
- Agent run APIs
- MCP APIs
- filesystem and SQLite tools
- Developer Mode-facing privileged operations

The frontend shows locked workspace states for Knowledge and Agent pages instead of pretending the features are unavailable.

## Frontend Auth

New frontend auth flow:

- `/login`
- `/register`
- `AuthProvider`
- `useAuth`
- `EmailPasswordForm`
- persistent access token storage
- startup session recovery via `/auth/me`
- authenticated preference loading via `/auth/preferences`
- automatic `Authorization: Bearer <token>` injection in the shared API client
- token cleanup on 401
- logout clears the local token and returns to Guest

The current implementation stores the access token in `localStorage` for development simplicity. This is vulnerable to XSS if an attacker can execute JavaScript in the page. A production hardening phase should move access tokens to HttpOnly, Secure, SameSite cookies and add CSRF protections where needed.

## Onboarding and Preferences

Guest onboarding remains localStorage-based.

Authenticated onboarding uses `user_preferences.onboarding_completed` from the backend:

- app startup loads server preferences after `/auth/me`
- completing onboarding calls `PATCH /auth/preferences`
- logged-in users use server preferences as the source of truth

Language and Developer Mode preference synchronization are prepared in the API and auth provider, but this phase prioritizes onboarding persistence to minimize UI regressions.

## Demo Workspace Policy

Registered users do not inherit Demo workspace data automatically.

The Demo workspace remains separate and is used only for unauthenticated compatibility. A future migration/import flow can explicitly copy Demo data into a private account, but this phase intentionally avoids implicit data transfer.

## Cross-User Isolation Test

`scripts/test_email_auth_isolation_smoke.py` creates User A and User B, then verifies:

- duplicate email registration rejected
- wrong password rejected
- invalid JWT rejected
- inactive user rejected
- `/auth/me` returns authenticated user for valid JWT
- `/auth/preferences` read/write persists onboarding state
- unauthenticated Guest/Demo temp upload still works
- authenticated KB create/switch/upload/chat writes into User A scope
- User A upload and FAISS files exist under `backend/data/users/user_{id}/knowledge_bases/{kb_name}`
- User B cannot read, rename, or delete User A conversation
- User B cannot submit feedback to User A assistant message
- User B cannot switch, export, or delete User A KB
- User B cannot download, reindex, or delete User A document

## API Compatibility

Existing request and response fields are preserved for normal success paths. Some protected operations now return HTTP 403/404 instead of `200 {"error": ...}` when a guest lacks permission or a scoped private resource is missing. This is intentional for real authorization semantics.

The SSE event contract, RAG algorithm, prompt construction, BM25/FAISS retrieval logic, Agent planner protocol, MCP protocol, and Tool Registry IDs were not changed.

## Test Status

Verified:

- backend Python compile
- frontend typecheck
- frontend lint
- frontend Vitest
- frontend production build
- `scripts/test_email_auth_isolation_smoke.py`

Unified smoke runner now includes the auth isolation script. The runner currently fails legacy protected-feature smoke scripts because they still call KB management, Agent, MCP, filesystem, and SQLite endpoints without logging in. These scripts need an authenticated test helper in the next stabilization pass. Two existing local-import tests also still depend on the shell Python environment having `sentence_transformers` and `openai`.

Phase 10.4 resolved this regression by adding `scripts/smoke_auth.py`, updating protected smoke tests to use real JWT users, and forcing the smoke runner to use the project virtual environment by default. See `docs/refactor/phase-10-auth-regression-stabilization.md`.

## Remaining Work

- keep auth smoke helpers aligned with future protected endpoints
- add HttpOnly cookie session mode
- add refresh token rotation or short-lived access tokens
- add account profile management
- add password reset
- add optional email verification if a mail provider is introduced
- add Google/GitHub OAuth after session hardening
- add explicit Demo-to-private-workspace migration/import UX
- add admin tooling only after a real RBAC model is designed

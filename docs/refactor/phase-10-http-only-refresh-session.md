# Phase 10.5 HttpOnly Refresh Session

## Goal

Phase 10.5 replaces the previous persistent localStorage access-token flow with a safer session model:

- short-lived JWT access token returned to the frontend and kept only in memory
- long-lived JWT refresh token stored in an HttpOnly cookie
- server-side refresh session record with hashed refresh token
- refresh token rotation
- logout revocation
- shared frontend refresh-on-401 handling

This phase does not add OAuth, social login, email verification, forgot password, account settings, billing, or new AI features.

## Session Architecture

Login and registration now create a server-side auth session.

The backend returns:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": 1,
    "email": "user@example.com"
  }
}
```

The refresh token is not returned in JSON. It is written only to an HttpOnly cookie.

The API response keeps the OAuth-style compatibility value `token_type = bearer`.
The JWT payload itself carries `token_type = access`.

Normal API requests continue to use:

```http
Authorization: Bearer <access_token>
```

The frontend stores the access token in module memory only. On app startup it calls `POST /auth/refresh` with `credentials: include`, receives a fresh access token, then calls `GET /auth/me`.

## Token Lifetimes

Access token:

- default TTL: 15 minutes
- environment variable: `ACCESS_TOKEN_TTL_MINUTES`
- fallback compatibility variable: `ACCESS_TOKEN_EXPIRE_MINUTES`

Refresh token:

- default TTL: 30 days
- environment variable: `REFRESH_TOKEN_TTL_DAYS`
- fallback compatibility variable: `REFRESH_TOKEN_EXPIRE_DAYS`

## JWT Payloads

Access token payload:

- `iss`
- `sub`
- `uid`
- `email`
- `iat`
- `exp`
- `token_type = access`
- `session_id`

Refresh token payload:

- `iss`
- `sub`
- `uid`
- `email`
- `iat`
- `exp`
- `token_type = refresh`
- `session_id`
- `jti`

Access and refresh tokens are explicitly type-checked. A refresh token cannot be used as an access token, and an access token cannot refresh a session.

## Cookie Configuration

Default cookie:

- name: `mini_chatchat_refresh`
- HttpOnly: enabled
- Secure: disabled by default for local development
- SameSite: `lax`
- path: `/auth`
- domain: unset by default

Environment variables:

```env
AUTH_COOKIE_NAME=mini_chatchat_refresh
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
AUTH_COOKIE_DOMAIN=
AUTH_COOKIE_PATH=/auth
```

Production should set `AUTH_COOKIE_SECURE=true` behind HTTPS.

## Database Migration

`backend/db.py` creates `auth_sessions`:

| Field | Purpose |
| --- | --- |
| `id` | internal row id |
| `session_id` | public session UUID stored in JWT payloads |
| `user_id` | owning user |
| `refresh_token_hash` | SHA-256 hash of current refresh token |
| `created_at` | session creation time |
| `updated_at` | latest mutation time |
| `expires_at` | refresh session expiry |
| `revoked_at` | revocation timestamp |
| `last_used_at` | latest successful refresh |
| `user_agent` | optional request user agent |
| `ip_address` | optional request IP |
| `is_active` | active/revoked state |

The database never stores plaintext refresh tokens or access tokens.

## Refresh Rotation

`POST /auth/refresh` performs rotation:

1. read refresh token from HttpOnly cookie
2. verify JWT signature, issuer, expiry, and `token_type = refresh`
3. load `auth_sessions.session_id`
4. verify session is active, unrevoked, and unexpired
5. compare SHA-256 hash of the presented token to the stored hash
6. generate new refresh token and access token
7. update `refresh_token_hash`, `last_used_at`, `updated_at`, and `expires_at`
8. write new HttpOnly cookie

If an old refresh token is reused after rotation, the backend revokes the session and returns `401`.

## Auth APIs

Changed:

- `POST /auth/register`: creates user, creates auth session, returns short access token, sets refresh cookie
- `POST /auth/login`: validates credentials, creates auth session, returns short access token, sets refresh cookie
- `POST /auth/logout`: revokes current refresh session and clears cookie

New:

- `POST /auth/refresh`: rotates refresh token and returns a new short access token
- `POST /auth/logout-all`: revokes all sessions for the current authenticated user and clears cookie

Unchanged contract:

- `GET /auth/me`
- `GET /auth/preferences`
- `PATCH /auth/preferences`

## Current User Enforcement

Access-token dependencies now require a valid `session_id`.

Authenticated API requests are accepted only if:

- JWT is valid
- JWT is an access token
- session exists
- session belongs to the token user
- session is active
- session is not revoked
- session is not expired
- user is still active

This makes logout effective for subsequent access-token API calls.

Unauthenticated requests still fall back to the existing Guest/Demo compatibility path.

## Frontend AuthProvider

`AuthProvider` now:

- clears legacy `mini-chatchat:access-token` localStorage data
- starts by calling `POST /auth/refresh`
- stores the returned access token in memory only
- calls `GET /auth/me` after refresh
- loads server preferences for authenticated users
- falls back to Guest if refresh fails
- clears in-memory state and cookie-backed session on logout

The frontend no longer restores a session from localStorage.

## API Client

`frontend-react/src/api/client.ts` now owns auth transport:

- stores access token in module memory only
- adds `Authorization: Bearer <token>` automatically
- sends `credentials: include` on all requests
- performs `POST /auth/refresh` on `401`
- retries the original request once after refresh
- shares one in-flight refresh promise across concurrent `401` responses
- clears legacy localStorage token
- dispatches `mini-chatchat:auth-expired` when refresh fails

Individual API modules do not manually implement token refresh.

## CORS

Backend CORS now uses explicit dev origins and credentials:

```python
allow_origins=[
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
allow_credentials=True
```

Origins are configurable through `CORS_ORIGINS`.

## LocalStorage Cleanup

Legacy key:

```text
mini-chatchat:access-token
```

is removed on:

- app startup
- explicit session clear
- failed refresh
- logout

No new access token is written to localStorage.

## Tests

Backend auth session smoke:

- register/login set HttpOnly refresh cookie
- auth JSON does not leak refresh token
- missing refresh cookie returns `401`
- invalid refresh cookie returns `401`
- access token cannot refresh
- refresh token cannot access normal API
- refresh rotation updates cookie
- old refresh token reuse revokes session
- logout clears cookie and revokes session
- disabled user cannot refresh

Frontend auth regression tests:

- access token is kept in memory
- localStorage access token is not written
- legacy localStorage token is cleared
- app startup restores session through `/auth/refresh`
- expired access token triggers refresh and single retry
- concurrent `401` responses share one refresh call

Unified smoke runner:

- total tests: 28
- pass: 28
- fail: 0
- environment error: 0

## Verification Commands

Backend:

```bash
.venv/bin/python -m py_compile backend/app.py backend/db.py backend/auth/config.py backend/auth/dependencies.py backend/auth/jwt.py backend/auth/models.py backend/auth/password.py backend/auth/permissions.py backend/auth/session.py scripts/test_auth_session_smoke.py scripts/smoke_auth.py scripts/run_smoke_tests.py
MINI_CHATCHAT_API_BASE=http://127.0.0.1:8001 .venv/bin/python scripts/test_auth_session_smoke.py
MINI_CHATCHAT_API_BASE=http://127.0.0.1:8001 .venv/bin/python scripts/test_email_auth_isolation_smoke.py
MINI_CHATCHAT_API_BASE=http://127.0.0.1:8001 .venv/bin/python scripts/run_smoke_tests.py
```

Frontend:

```bash
cd frontend-react
npm run typecheck
npm run lint
npm run test
npm run build
```

Browser QA was attempted with local Playwright, but local browser execution required elevated desktop permissions and the approval system rejected the request due usage-limit constraints. It should be rerun manually or in CI with browser permissions.

## Compatibility

Preserved:

- `/kb_chat` behavior
- SSE contract
- RAG retrieval
- Agent planner and tool registry IDs
- MCP protocol
- user data isolation
- Guest/Demo compatibility
- existing auth response shape, except access-token TTL is shorter and refresh token is cookie-only

Changed security behavior:

- old access tokens become invalid after logout if their session is revoked
- localStorage access-token persistence is removed
- refresh cookie is required for silent session restore

## Remaining Limits

- No CSRF token layer yet. SameSite Lax and `/auth` cookie path reduce exposure for the current dev architecture, but production should add CSRF protection if cross-site authenticated mutations are supported.
- No refresh-token device management UI yet.
- No session list or revoke-one-device UI yet.
- No HttpOnly-cookie-only access token mode; access token is still available to JavaScript while in memory.
- No refresh token family/audit event table beyond session revocation fields.
- No rate limiting on login/refresh endpoints yet.
- No OAuth providers yet.

## Next Work

Recommended next auth phase:

1. Account and session management UI.
2. Session list and device revoke.
3. CSRF token strategy for cookie-authenticated mutation endpoints.
4. Rate limiting for login, register, and refresh.
5. Optional OAuth providers after session management is stable.

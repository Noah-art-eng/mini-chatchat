# Phase 10.6 Account Profile And Session Management

## Goal

Phase 10.6 adds account profile management, per-device session management, and the first deployment-facing auth hardening layer on top of the existing email auth, user isolation, and HttpOnly refresh-cookie flow.

This phase does not add OAuth, email verification, forgot password, avatar upload, admin roles, billing, or new AI capabilities.

## Account APIs

New account endpoints:

- `GET /auth/account`
- `PATCH /auth/account`

`GET /auth/account` returns the current authenticated user in the same public user shape used by `/auth/me`.

`PATCH /auth/account` accepts only:

```json
{
  "display_name": "New name"
}
```

Rules:

- trims leading and trailing whitespace
- rejects empty names
- rejects names longer than 80 characters
- rejects extra fields
- does not allow changing `id`, `email`, `auth_provider`, `is_active`, or `password_hash`
- returns the updated public user

Email changes are intentionally deferred because they require verification.

## Session APIs

New session endpoints:

- `GET /auth/sessions`
- `DELETE /auth/sessions/{session_id}`
- `POST /auth/logout-others`

Existing:

- `POST /auth/logout`
- `POST /auth/logout-all`

`GET /auth/sessions` returns only the current user's sessions.

Returned fields are safe for UI display:

| Field | Purpose |
| --- | --- |
| `session_id` | public opaque session identifier |
| `device` | summarized browser/device string |
| `created_at` | session creation time |
| `last_used_at` | last successful refresh |
| `expires_at` | refresh-session expiry |
| `revoked_at` | revocation time, if revoked |
| `is_active` | active session marker |
| `is_current` | whether it matches the current access-token session |
| `ip_address` | masked IP address |

The API never returns refresh token hashes, access tokens, refresh tokens, full raw IP addresses, or internal database ids.

## Session Revocation

`DELETE /auth/sessions/{session_id}` revokes a single session if and only if it belongs to the current user.

Behavior:

- revoking another user's session returns `404`
- revoking an unknown session returns `404`
- revoking another device keeps the current device signed in
- revoking the current device clears the refresh cookie and the frontend returns to Guest mode

## Logout Others And Logout All

`POST /auth/logout-others` revokes every active session for the current user except the current session.

`POST /auth/logout-all` preserves the existing behavior:

- revokes all sessions for the current authenticated user
- clears the refresh cookie
- frontend clears in-memory access token and returns to Guest mode

## Session Cleanup

`cleanup_expired_auth_sessions()` marks expired active sessions inactive and revoked.

It is intentionally lightweight:

- called before session listing
- available for maintenance scripts
- does not perform heavy full-table scans on every authenticated request

## Rate Limiting

Phase 10.6 adds an in-memory failed-attempt limiter for auth-sensitive endpoints.

Covered flows:

- registration failures
- login failures
- refresh failures

Bucket keys include:

- action kind
- client IP
- optional normalized email identifier where applicable

Environment variables:

```env
AUTH_RATE_LIMIT_MAX_FAILURES=5
AUTH_RATE_LIMIT_WINDOW_SECONDS=300
```

The limiter is intentionally simple and suitable for local deployment hardening. A production deployment should move this to Redis or another shared store.

Login failures use the same user-facing message for wrong email and wrong password:

```json
{
  "detail": "Email or password is incorrect."
}
```

## Origin And CSRF Strategy

Cookie-backed auth endpoints now validate `Origin` on mutating requests.

Protected endpoints include:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/logout-all`

Requests without an `Origin` header are allowed for scripts, curl, and server-to-server smoke tests.

Requests with an unknown origin are rejected with `403`.

Allowed origins are derived from the existing CORS configuration, including the local dev frontend origins. The backend keeps credentials-enabled CORS and does not use wildcard origins.

This is a baseline CSRF defense. A future production phase should add a same-site CSRF token if cross-site embedding or broader cookie usage is introduced.

## Production Auth Configuration

On startup, production mode rejects unsafe auth defaults:

- default development JWT secret
- insecure refresh cookie
- wildcard or empty CORS origins

`APP_ENV=production` must be paired with explicit secure auth settings.

## Frontend Account UI

New page:

- `/account`

New component:

- `frontend-react/src/features/account/AccountPage.tsx`

TopBar now exposes:

- `Account`
- `Logout`

The account page includes:

- profile section
- display name editor
- email and auth provider read-only fields
- account creation time
- session list
- current device marker
- other device rows
- revoke single device
- logout other devices
- logout all devices

All destructive actions use the shared `ConfirmDialog` and toast feedback. The UI does not use `window.confirm`.

## i18n

Account and session labels are available in:

- English
- Simplified Chinese

The page uses user-facing copy such as "Current device", "Other device", "Last activity", and "Logout other devices". Developer-only values such as refresh hashes or tokens are never shown.

## Testing

New backend smoke test:

- `scripts/test_account_session_smoke.py`

Coverage:

- profile read/update
- rejected invalid display names
- rejected extra account fields
- current session marker
- safe session list fields
- no token/hash/full-IP leakage
- revoke other session
- cross-user revoke returns `404`
- expired session cleanup
- logout other sessions
- logout all sessions
- unknown Origin rejection
- allowed Origin behavior
- login rate-limit trigger
- disabled-user account request rejection

New frontend tests:

- `frontend-react/src/features/account/account-page.test.tsx`

Coverage:

- account page load
- profile update
- session list
- current device marker
- revoke other device
- logout other devices
- logout all devices
- Chinese labels
- ConfirmDialog usage
- toast feedback

## Compatibility

No RAG, SSE, Agent, MCP, Tool Registry, knowledge-base, or user-isolation data flow is changed.

Existing Guest/Demo compatibility remains intact. Authenticated users continue to use their real user scope through the existing Current User dependency chain.

## Known Limits

- rate limiting is process-local and resets on backend restart
- no refresh-token family reuse detection beyond the current session hash mismatch
- no email verification
- no password reset
- no OAuth provider
- no avatar upload
- no admin session management
- no persistent audit log
- CSRF protection is Origin-based baseline protection, not a full double-submit token flow

## Next Phase

Phase 10.7 or Phase 10.4 should decide whether to prioritize:

- Google/GitHub OAuth
- verified email changes
- password reset
- Redis-backed rate limiting
- HttpOnly access-token cookie mode
- account deletion and export

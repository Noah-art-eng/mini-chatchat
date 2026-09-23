# Phase 10.7 Google And GitHub OAuth Integration

## Goal

Phase 10.7 adds production-oriented Google and GitHub OAuth login on top of the existing email auth, HttpOnly refresh cookie, refresh rotation, auth sessions, account page, and user data isolation.

This phase does not add WeChat login, phone login, email verification, forgot password, refresh-token redesign, billing, admin roles, or new AI features. RAG, chat streaming, Knowledge Base, Agent, MCP, and Tool Registry behavior remain unchanged.

## OAuth Providers

Supported providers:

- Google
- GitHub

OAuth configuration is read from environment variables:

```env
FRONTEND_BASE_URL=http://127.0.0.1:5173
BACKEND_BASE_URL=http://127.0.0.1:8001

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8001/auth/oauth/google/callback

GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=http://127.0.0.1:8001/auth/oauth/github/callback
```

In production, OAuth provider configuration is validated along with the existing JWT, refresh cookie, and allowed-origin security settings.

## Backend APIs

New OAuth endpoints:

- `GET /auth/oauth/providers`
- `GET /auth/oauth/google`
- `GET /auth/oauth/google/callback`
- `GET /auth/oauth/github`
- `GET /auth/oauth/github/callback`
- `POST /auth/oauth/link/{provider}`
- `DELETE /auth/oauth/link/{provider}`

`GET /auth/oauth/providers` returns public provider status only:

```json
{
  "providers": [
    {
      "provider": "google",
      "label": "Google",
      "configured": false,
      "linked": false,
      "account": null
    }
  ]
}
```

It never returns client secrets, access tokens, refresh tokens, or provider token payloads.

`GET /auth/oauth/{provider}` starts an OAuth login redirect. It creates a short-lived state record and PKCE verifier, then redirects to the provider authorization URL.

`GET /auth/oauth/{provider}/callback` validates state, exchanges the authorization code for a provider token, fetches provider user info, resolves or creates the local user, creates the existing Mini ChatChat auth session, sets the existing HttpOnly refresh cookie, and redirects back to the frontend.

`POST /auth/oauth/link/{provider}` requires an authenticated user. It creates a provider authorization URL in `link` mode and returns it to the frontend.

`DELETE /auth/oauth/link/{provider}` requires an authenticated user and removes the linked provider account if doing so will not leave the user without any login method.

## Database

New table:

```sql
CREATE TABLE IF NOT EXISTS oauth_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  provider TEXT NOT NULL,
  provider_user_id TEXT NOT NULL,
  provider_email TEXT DEFAULT NULL,
  provider_display_name TEXT DEFAULT NULL,
  provider_avatar TEXT DEFAULT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(provider, provider_user_id),
  UNIQUE(user_id, provider),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
)
```

The table stores identity binding metadata only. It does not store OAuth access tokens, refresh tokens, client secrets, or provider session secrets.

## Account Resolution Rules

OAuth login uses these rules:

1. If `(provider, provider_user_id)` is already linked, use the linked active local user.
2. If no provider link exists but the provider email matches an active local user, bind the provider to that existing user.
3. If no matching local user exists, create a new local user with `auth_provider` set to the provider.
4. Provider email is required. If the provider does not return an email, the login is rejected.
5. The same provider user id can belong to only one Mini ChatChat user.
6. A local user can bind at most one account per provider.

Existing Demo Workspace data is not automatically inherited by OAuth users. OAuth users get their own user scope and default Knowledge Base.

## Binding Rules

Authenticated users can link Google or GitHub from the Account page.

Rules:

- Binding requires a valid current Mini ChatChat session.
- The provider user id must not already be linked to another Mini ChatChat user.
- The provider email must match the current user email.
- If the current user already linked the same provider to another provider identity, the request is rejected.
- Binding reuses the same OAuth state and PKCE infrastructure as login.

## Unlink Rules

Authenticated users can unlink a provider from the Account page.

Rules:

- Unlinking requires a valid current Mini ChatChat session.
- Users can only unlink their own provider accounts.
- Unlinking the last remaining login method is rejected.
- Password login counts as one login method when `password_hash` exists.
- Each linked OAuth provider counts as one login method.

## Session Reuse

OAuth does not create a parallel authentication system.

Successful OAuth login calls the existing `create_login_session()` flow, which:

- creates an `auth_sessions` row
- issues a short-lived access token
- sets the existing HttpOnly refresh cookie
- supports refresh rotation
- participates in session list, logout, logout-all, and logout-others behavior

## Security Strategy

Security controls in this phase:

- OAuth state is generated with high-entropy random data and validated on callback.
- State records are short-lived and removed after callback.
- PKCE S256 is used for Google and GitHub authorization flows.
- OAuth callback redirect URIs must use HTTPS, except local development URLs on `localhost` or `127.0.0.1`.
- Provider access tokens are used only server-side to fetch user info.
- Provider tokens are not stored in SQLite.
- Provider tokens and client secrets are not returned to the frontend.
- OAuth provider secrets are not logged.
- Link and unlink endpoints require the existing authenticated current user.
- Link and unlink mutating requests use the existing Origin/CSRF validation.

Known limitation: state records are currently in memory, so restarting the backend invalidates pending OAuth redirects. A production deployment should move OAuth transaction state to a durable, short-lived store.

## Frontend

New frontend auth component:

- `frontend-react/src/auth/OAuthButtons.tsx`

Updated pages:

- `LoginPage`
- `RegisterPage`
- `AccountPage`

Login and Register now show Google and GitHub OAuth buttons. If a provider is not configured, the button is disabled and clearly marked by provider availability.

The Account page now includes a Connected Accounts section:

- provider label
- linked/unlinked/configured status
- linked provider email when available
- Link action
- Unlink action with shared `ConfirmDialog`

The UI uses existing Toast, ConfirmDialog, i18n, design tokens, and Account page styling. It does not use `alert()` or `window.confirm()`.

## i18n

OAuth copy is available in:

- English
- Simplified Chinese

Covered copy includes:

- loading providers
- continue with provider
- sign in with Google/GitHub
- register with Google/GitHub
- connected accounts
- linked/unlinked/not configured states
- link/unlink actions
- unlink confirmation

## Testing

New smoke test:

- `scripts/test_oauth_smoke.py`

Coverage:

- provider API returns Google and GitHub without leaking secrets
- callback cancellation redirects with `oauth_error`
- invalid state redirects with `oauth_error`
- state and PKCE generation
- invalid state rejection
- Google first login creates user and OAuth account
- Google repeated login does not duplicate users
- Google existing-email login auto-binds to existing user
- GitHub first login creates user and OAuth account
- provider link and unlink
- cross-user provider binding rejection
- unlinking last login method rejection
- OAuth login reuses HttpOnly refresh session infrastructure
- responses do not contain API keys, client secrets, provider tokens, password hashes, `invalid_api_key`, or `OpenAI 401`

Frontend account tests cover OAuth provider display and unlink confirmation.

## Known Limits

- Real Google/GitHub browser OAuth requires project-specific client ids, client secrets, and redirect URIs.
- OAuth state is in memory and should move to a durable expiring store for multi-process production deployments.
- Provider account linking currently requires email match and does not implement an account merge UI.
- OAuth provider avatars are stored as metadata but avatar upload and profile image management are deferred.
- Email verification, forgot password, Google/GitHub production consent-screen configuration, and refresh-token storage hardening remain separate phases.

## Next Work

Recommended next auth work:

1. Email verification.
2. Forgot password.
3. OAuth production deployment checklist and consent screen setup.
4. Avatar upload.
5. Optional Google/GitHub account-management polish.

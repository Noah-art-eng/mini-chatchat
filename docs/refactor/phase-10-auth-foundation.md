# Phase 10.1 Auth Foundation

## Goal

Phase 10.1 establishes authentication and authorization infrastructure without changing the current product behavior. It does not add login, registration, OAuth, account pages, or backend route enforcement.

## Backend Modules

New module: `backend/auth/`

- `config.py`: reads auth secret, issuer, and token expiration settings.
- `jwt.py`: creates and verifies HS256 JWT access tokens with standard-library HMAC/SHA256.
- `models.py`: defines `GuestUser`, `AuthenticatedUser`, `CurrentUser`, and auth provider names.
- `permissions.py`: defines the project permission model.
- `dependencies.py`: defines FastAPI current-user dependencies for future route protection.
- `password.py`: provides PBKDF2 password hashing and verification for future email/password login.

No login or registration routes were added.

## Database Design

`users`

- `id`
- `email`
- `display_name`
- `avatar_url`
- `auth_provider`
- `password_hash`
- `created_at`
- `updated_at`
- `is_guest`
- `is_active`

`user_preferences`

- `id`
- `user_id`
- `language`
- `developer_mode`
- `onboarding_completed`
- `theme`
- `preferred_model`
- `created_at`
- `updated_at`

Guest users are runtime-only and are not written to SQLite in this phase.

## Permission Model

Permissions:

- `can_use_chat`
- `can_use_search`
- `can_use_temp_file`
- `can_manage_kb`
- `can_use_agent`
- `can_use_mcp`
- `can_use_filesystem`
- `can_use_sqlite`
- `can_enable_developer_mode`

Current rules:

- Guest: chat, search, temp file.
- Authenticated user: all current capabilities.
- Inactive authenticated user: no permissions.

These permissions are not enforced on existing endpoints in Phase 10.1, preserving current compatibility.

## Frontend Modules

New module: `frontend-react/src/auth/`

- `AuthContext.tsx`: `AuthProvider` and `useAuth()`.
- `types.ts`: session, provider, and permission types.
- `permissions.ts`: frontend permission helpers.
- `ProtectedRoute.tsx`: future authenticated-route wrapper.
- `GuestRoute.tsx`: future guest-only route wrapper.
- `index.ts`: exports.

The provider defaults to a runtime Guest session. `TopBar` shows a passive Guest marker only. No login UI was added.

## Compatibility Strategy

- Existing API requests do not send auth headers.
- Existing backend routes do not require auth.
- Existing localStorage preferences remain active.
- User preferences are only prepared in SQLite; no migration from localStorage happens yet.
- Chat, RAG, streaming, conversation history, feedback, KB management, Agent, MCP, Tool Center, and System remain compatible.

## Deferred to Phase 10.2

- Email/password registration.
- Email/password login.
- Login and registration pages.
- Session persistence in frontend.
- Authenticated API client headers.
- User profile endpoint.
- Preferences sync endpoint.
- Real permission enforcement on protected backend routes.
- Optional OAuth providers: Google and GitHub.
- Guest-to-account upgrade flow.

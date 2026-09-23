# OAuth Provider Setup

This guide configures Google and GitHub OAuth for a deployed Mini ChatChat instance.

Do not commit provider secrets. Store them in `.env.production` or your deployment secret manager.

## Public URLs

Use one canonical HTTPS domain for the product:

```text
https://your-domain.example
```

Backend callbacks are served behind the `/api` reverse proxy:

```text
https://your-domain.example/api/auth/oauth/google/callback
https://your-domain.example/api/auth/oauth/github/callback
```

Local development may use:

```text
http://127.0.0.1:8001/auth/oauth/google/callback
http://127.0.0.1:8001/auth/oauth/github/callback
```

## Google OAuth

1. Open Google Cloud Console.
2. Create or select a project.
3. Configure the OAuth consent screen.
4. Create an OAuth 2.0 Client ID for a web application.
5. Add authorized redirect URI:

```text
https://your-domain.example/api/auth/oauth/google/callback
```

6. Set production variables:

```bash
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://your-domain.example/api/auth/oauth/google/callback
```

Google OAuth uses state validation and PKCE. Provider access tokens are not stored by Mini ChatChat.

## GitHub OAuth

1. Open GitHub Developer Settings.
2. Create an OAuth App.
3. Set Homepage URL:

```text
https://your-domain.example
```

4. Set Authorization callback URL:

```text
https://your-domain.example/api/auth/oauth/github/callback
```

5. Set production variables:

```bash
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GITHUB_REDIRECT_URI=https://your-domain.example/api/auth/oauth/github/callback
```

GitHub OAuth uses state validation. Provider access tokens are used only to fetch profile data and are not persisted.

## Account Linking Rules

- First OAuth login creates a user when the provider returns a verified email not already used.
- If the email already exists, OAuth links to the existing user.
- One provider account can belong to only one Mini ChatChat user.
- A signed-in user may link or unlink providers from Account.
- Unlinking the last login method is blocked.

## Production Checklist

- `FRONTEND_BASE_URL` matches the public HTTPS origin.
- `BACKEND_BASE_URL` matches the public `/api` origin.
- `CORS_ORIGINS` contains only the production HTTPS origin.
- OAuth callback URLs match provider console values exactly.
- Secrets are stored outside Git.
- Browser network logs do not expose OAuth access tokens.

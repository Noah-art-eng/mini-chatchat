# Production Deployment

## Required Environment

Start from:

```bash
cp .env.production.example .env.production
```

Minimum required values:

- `APP_ENV=production`
- `AUTH_SECRET_KEY` set to a long random secret
- `AUTH_COOKIE_SECURE=true`
- `CORS_ORIGINS=https://your-domain.example`
- `FRONTEND_BASE_URL=https://your-domain.example`
- `BACKEND_BASE_URL=https://your-domain.example/api`
- one LLM provider key: `DEEPSEEK_API_KEY` or `OPENAI_API_KEY`

OAuth values are required in production when OAuth is enabled:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`
- `GITHUB_CLIENT_ID`
- `GITHUB_CLIENT_SECRET`
- `GITHUB_REDIRECT_URI`

## HTTPS

The included production compose is HTTP-ready behind a TLS-terminating host proxy.

Recommended outer proxy:

- Caddy
- Nginx
- cloud load balancer

The repository includes a Caddy staging example:

```bash
PUBLIC_DOMAIN=your-domain.example ACME_EMAIL=admin@your-domain.example \
docker compose -f docker-compose.staging.yml up -d
```

TLS proxy must preserve:

- `X-Forwarded-Proto`
- `X-Forwarded-For`
- `Host`
- long read timeouts for SSE

The example `Caddyfile.example` proxies to the frontend container, which then proxies `/api` to the backend. This keeps one public origin for cookies, OAuth callbacks, and SSE.

## OAuth Callback URLs

Provider callback URLs must match production env exactly:

```text
https://your-domain.example/api/auth/oauth/google/callback
https://your-domain.example/api/auth/oauth/github/callback
```

Development localhost callbacks are allowed only for local development.

## Streaming And Uploads

The bundled nginx config disables proxy buffering for `/api/` so SSE streaming remains incremental.

Upload limit:

```nginx
client_max_body_size 50m;
```

Increase it only when the backend document loader and host storage limits have also been reviewed.

## Upgrade Guide

1. Stop the service.
2. Run `scripts/backup.sh`.
3. Pull or deploy the new image.
4. Start the service.
5. Check `/api/health/deps`.
6. Run smoke tests against the production-like endpoint from a trusted network.

Public production `/api/health/deps` should expose only dependency check status by default. Keep `HEALTH_DEPS_PUBLIC_DETAILS=false` unless the endpoint is protected behind an operator-only network.

## Troubleshooting

Common issues:

- `AUTH_COOKIE_SECURE=false` in production: backend should reject unsafe production startup.
- OAuth callback mismatch: provider redirects fail before reaching Mini ChatChat.
- CORS mismatch: browser auth requests fail with credentials.
- SQLite file mounted as a directory: use the `runtime/prod` directory mount from `docker-compose.prod.yml`.
- First boot slow: embedding model download/cache can take time.
- Public health response too verbose: keep `HEALTH_DEPS_PUBLIC_DETAILS=false`.

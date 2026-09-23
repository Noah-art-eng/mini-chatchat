# Production Checklist

Use this checklist before exposing Mini ChatChat to the public internet.

## Required

- [ ] HTTPS terminates before the app.
- [ ] `APP_ENV=production`.
- [ ] `AUTH_SECRET_KEY` is long, random, and not committed.
- [ ] `AUTH_COOKIE_SECURE=true`.
- [ ] `CORS_ORIGINS` contains only trusted HTTPS origins.
- [ ] `FRONTEND_BASE_URL` matches the public domain.
- [ ] `BACKEND_BASE_URL` matches the public `/api` URL.
- [ ] Google OAuth callback URL matches production provider console.
- [ ] GitHub OAuth callback URL matches production provider console.
- [ ] `HEALTH_DEPS_PUBLIC_DETAILS=false` unless health details are behind an operator-only network.
- [ ] `npm audit --omit=dev` returns zero production vulnerabilities.
- [ ] Full `npm audit` returns zero vulnerabilities or documented dev-only exceptions.
- [ ] At least one LLM provider key is configured.
- [ ] Upload size limit is reviewed.
- [ ] Auth rate limit is enabled.
- [ ] Session cleanup has been tested.
- [ ] `scripts/backup.sh` has been run before deployment.
- [ ] `scripts/restore.sh` has been tested on a non-production copy.
- [ ] Backup `.sha256` checksum is stored with each archive.
- [ ] Non-interactive restore jobs set `RESTORE_CONFIRM=yes` explicitly.
- [ ] `/api/health` returns `ok`.
- [ ] `/api/health/deps` returns `ok` or known acceptable `degraded`.
- [ ] Full smoke runner passes against the deployed backend from a trusted network.

## Recommended

- [ ] External log rotation is configured.
- [ ] Backups are encrypted and copied off-host.
- [ ] OAuth secrets are stored in a secret manager.
- [ ] Model cache volume is warmed before traffic.
- [ ] Reverse proxy read timeout supports long SSE streams.
- [ ] Monitoring alerts on `/api/health/deps` degraded status.

## Known Portfolio Limits

- SQLite is acceptable for a single-host portfolio deployment, not multi-node high concurrency.
- OAuth transaction state is in memory.
- The backend image can still be large because of embedding dependencies.
- No managed object storage is configured for uploads.

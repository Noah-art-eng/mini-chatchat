# Environment Variables

## Model Provider

| Variable | Required | Notes |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | one provider required | Preferred provider when set. |
| `DEEPSEEK_BASE_URL` | no | Defaults to `https://api.deepseek.com`. |
| `DEEPSEEK_MODEL` | no | Defaults to `deepseek-chat`. |
| `OPENAI_API_KEY` | one provider required | Fallback when DeepSeek is not set. |
| `OPENAI_BASE_URL` | no | Optional OpenAI-compatible base URL. |
| `OPENAI_MODEL` | no | Optional OpenAI-compatible model. |
| `EMBEDDING_MODEL` | no | Defaults to `all-MiniLM-L6-v2`. |

## Auth And Sessions

| Variable | Production Rule |
| --- | --- |
| `AUTH_SECRET_KEY` | Must be a long random secret. Weak default is rejected in production. |
| `AUTH_ISSUER` | Stable issuer string, default `mini-chatchat`. |
| `ACCESS_TOKEN_TTL_MINUTES` | Short-lived access token TTL. |
| `REFRESH_TOKEN_TTL_DAYS` | Refresh cookie/session TTL. |
| `AUTH_COOKIE_SECURE` | Must be `true` in production. |
| `AUTH_COOKIE_SAMESITE` | `lax`, `strict`, or `none`. |
| `AUTH_COOKIE_DOMAIN` | Optional cookie domain. |
| `AUTH_COOKIE_PATH` | Defaults to `/auth`. |
| `AUTH_RATE_LIMIT_MAX_FAILURES` | Failed auth attempts before temporary block. |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | Rate-limit window. |

## CORS And URLS

| Variable | Production Rule |
| --- | --- |
| `APP_ENV` | Set to `production`. |
| `FRONTEND_BASE_URL` | Public frontend URL. |
| `BACKEND_BASE_URL` | Public backend URL, usually frontend URL plus `/api`. |
| `CORS_ORIGINS` | Explicit HTTPS origins only. No wildcard. |

## OAuth

| Variable | Notes |
| --- | --- |
| `GOOGLE_CLIENT_ID` | Google OAuth client id. |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret. |
| `GOOGLE_REDIRECT_URI` | Must match provider console. |
| `GITHUB_CLIENT_ID` | GitHub OAuth app client id. |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app client secret. |
| `GITHUB_REDIRECT_URI` | Must match provider console. |

## Runtime Paths

| Variable | Default |
| --- | --- |
| `MINI_CHATCHAT_DB_PATH` | `backend/mini.db` |
| `MINI_CHATCHAT_DATA_ROOT` | `backend/data` |
| `MINI_CHATCHAT_UPLOADS_DIR` | `backend/uploads` |
| `HF_HOME` | embedding/model cache path |
| `SENTENCE_TRANSFORMERS_HOME` | embedding/model cache path |

## Observability

| Variable | Notes |
| --- | --- |
| `APP_VERSION` | Version returned by `/health`. |
| `BUILD_TIME` | Build timestamp returned by `/health/deps`. |
| `GIT_COMMIT` | Commit SHA returned by `/health/deps`. |
| `LOG_LEVEL` | Defaults to `INFO`. |
| `HEALTH_DEPS_PUBLIC_DETAILS` | Defaults to `false`. In production, keep `false` so public `/health/deps` returns only status and dependency checks. |

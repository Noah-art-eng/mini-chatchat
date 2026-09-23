# Docker Deployment

## Development Compose

Create local environment values:

```bash
cp .env.example .env.docker
```

Start:

```bash
docker compose -f docker-compose.dev.yml up --build
```

URLs:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`

## Production Compose

Create production environment values:

```bash
cp .env.production.example .env.production
```

Create the runtime directory before first boot:

```bash
mkdir -p runtime/prod
```

Start:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Production topology:

```text
browser
  |
  v
frontend nginx :80
  |-- /        -> React static files
  |-- /api/*   -> backend:8000/*
  |
  v
backend FastAPI
```

The frontend image is built with:

```env
VITE_API_BASE_URL=/api
```

## Volumes

Production compose keeps runtime state outside images:

- `./runtime/prod:/app/backend/runtime`

SQLite path:

```env
MINI_CHATCHAT_DB_PATH=/app/backend/runtime/mini.db
```

Knowledge Base data and uploads:

```env
MINI_CHATCHAT_DATA_ROOT=/app/backend/runtime/data
MINI_CHATCHAT_UPLOADS_DIR=/app/backend/runtime/uploads
```

Embedding cache:

```env
HF_HOME=/app/backend/runtime/model_cache
SENTENCE_TRANSFORMERS_HOME=/app/backend/runtime/model_cache
```

## Health Checks

```bash
curl http://127.0.0.1/healthz
curl http://127.0.0.1/api/health
curl http://127.0.0.1/api/health/deps
```

## Docker Validation

```bash
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml build
```

## Image Size Note

The backend image still includes `sentence-transformers` and PyTorch dependencies. The Dockerfile installs through the PyTorch CPU wheel index, but image size can remain large. Further optimization can split backend requirements, prebuild model cache, or move embeddings to a separate service.

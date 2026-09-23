# Local Deployment

## Backend

Use the project virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cd backend
uvicorn app:app --reload --host 127.0.0.1 --port 8001
```

Check:

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/health/deps
curl http://127.0.0.1:8001/models
```

## Frontend

```bash
cd frontend-react
npm install
VITE_API_BASE_URL=http://127.0.0.1:8001 npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173
```

## Runtime Data

Default local paths:

- `backend/mini.db`
- `backend/data/`
- `backend/uploads/`

Override paths when needed:

```bash
MINI_CHATCHAT_DB_PATH=/absolute/path/mini.db
MINI_CHATCHAT_DATA_ROOT=/absolute/path/data
MINI_CHATCHAT_UPLOADS_DIR=/absolute/path/uploads
```

## Smoke Tests

Run after the backend is up:

```bash
MINI_CHATCHAT_API_BASE=http://127.0.0.1:8001 python3 scripts/run_smoke_tests.py
```

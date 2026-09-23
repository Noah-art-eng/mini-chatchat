FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install --extra-index-url https://download.pytorch.org/whl/cpu -r /app/requirements.txt

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"
ENV MINI_CHATCHAT_DATA_ROOT=/app/backend/data
ENV MINI_CHATCHAT_UPLOADS_DIR=/app/backend/uploads
ENV MINI_CHATCHAT_DB_PATH=/app/backend/mini.db
ENV HF_HOME=/app/backend/data/model_cache
ENV SENTENCE_TRANSFORMERS_HOME=/app/backend/data/model_cache

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv

COPY backend /app/backend
RUN mkdir -p /app/backend/data /app/backend/uploads /app/backend/temp \
    && chown -R appuser:appuser /app/backend

WORKDIR /app/backend

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

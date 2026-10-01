#!/usr/bin/env bash

set -u

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
FRONTEND_DIR="${REPO_ROOT}/frontend-react"
BACKEND_PID=""
FRONTEND_PID=""

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

if [[ ! -x "${PYTHON_BIN}" ]]; then
  fail "Python environment not found. Run: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
fi

if ! command -v npm >/dev/null 2>&1; then
  fail "npm was not found. Install Node.js/npm, then run: cd frontend-react && npm install"
fi

if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
  fail "Frontend dependencies not found. Run: cd frontend-react && npm install"
fi

cleanup() {
  local exit_status="${1:-0}"
  trap - EXIT INT TERM

  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi

  if [[ -n "${FRONTEND_PID}" ]]; then
    wait "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]]; then
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi

  exit "${exit_status}"
}

trap 'cleanup $?' EXIT
trap 'cleanup 130' INT
trap 'cleanup 143' TERM

(
  cd "${REPO_ROOT}/backend" || exit 1
  exec "${PYTHON_BIN}" -m uvicorn app:app --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

(
  cd "${FRONTEND_DIR}" || exit 1
  exec npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
) &
FRONTEND_PID=$!

printf 'Mini ChatChat is starting.\n'
printf 'Backend: http://127.0.0.1:8000\n'
printf 'Frontend: http://127.0.0.1:5173\n'
printf 'Press Ctrl+C to stop both processes.\n'

while true; do
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    wait "${BACKEND_PID}" 2>/dev/null
    printf 'Error: backend process exited; stopping frontend.\n' >&2
    cleanup 1
  fi

  if ! kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    wait "${FRONTEND_PID}" 2>/dev/null
    printf 'Error: frontend process exited; stopping backend.\n' >&2
    cleanup 1
  fi

  sleep 1
done

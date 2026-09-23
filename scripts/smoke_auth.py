import os
import secrets
import tempfile
import time
from pathlib import Path

import requests


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

SMOKE_PASSWORD = "SmokePassword123"
ROOT_DIR = Path(__file__).resolve().parents[1]

_SMOKE_USER = None
_DEFAULT_KB_READY = False
_SMOKE_SESSION = requests.Session()


def unique_email(prefix="smoke"):
    """负责 unique_email 的函数职责。"""
    timestamp = int(time.time() * 1000)
    suffix = secrets.token_hex(4)
    return f"{prefix}_{timestamp}_{suffix}@example.test"


def auth_headers(token=None):
    """负责 auth_headers 的函数职责。"""
    if token is None:
        token = get_smoke_user()["token"]
    return {"Authorization": f"Bearer {token}"}


def request(method, path, token=None, **kwargs):
    """负责 request 的函数职责。"""
    headers = kwargs.pop("headers", {})
    if token is not None:
        headers = {**headers, **auth_headers(token)}

    return requests.request(
        method,
        f"{API_BASE}{path}",
        headers=headers,
        timeout=kwargs.pop("timeout", 180),
        **kwargs,
    )


def auth_request(method, path, **kwargs):
    """负责 auth_request 的函数职责。"""
    headers = kwargs.pop("headers", {})
    headers = {**auth_headers(), **headers}
    return _SMOKE_SESSION.request(
        method,
        f"{API_BASE}{path}",
        headers=headers,
        timeout=kwargs.pop("timeout", 180),
        **kwargs,
    )


def register_user(prefix="smoke"):
    """负责 register_user 的函数职责。"""
    email = unique_email(prefix)
    response = _SMOKE_SESSION.post(
        f"{API_BASE}/auth/register",
        json={
            "display_name": f"Smoke {prefix}",
            "email": email,
            "password": SMOKE_PASSWORD,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    token = data.get("access_token")
    user = data.get("user") or {}
    if not token or not user.get("id"):
        raise RuntimeError("auth register did not return access_token and user")
    return {
        "email": email,
        "password": SMOKE_PASSWORD,
        "token": token,
        "user": user,
    }


def get_smoke_user(ensure_default_kb=True):
    """负责 get_smoke_user 的函数职责。"""
    global _SMOKE_USER

    if _SMOKE_USER is None:
        _SMOKE_USER = register_user()

    if ensure_default_kb:
        ensure_default_kb_document(_SMOKE_USER["token"])

    return _SMOKE_USER


def ensure_default_kb_document(token):
    """负责 ensure_default_kb_document 的函数职责。"""
    global _DEFAULT_KB_READY

    if _DEFAULT_KB_READY:
        return

    content = (
        "Docker packages applications and their dependencies into portable "
        "containers. Mini ChatChat is a local knowledge base and Agent "
        "workspace for RAG, search, temporary file chat, and tool use.\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    try:
        with temp_path.open("rb") as file:
            response = request(
                "POST",
                "/upload",
                token=token,
                files={
                    "file": (
                        "smoke_default_kb.txt",
                        file,
                        "text/plain",
                    ),
                },
            )
        response.raise_for_status()
    finally:
        temp_path.unlink(missing_ok=True)

    _DEFAULT_KB_READY = True


def create_smoke_users():
    """负责 create_smoke_users 的函数职责。"""
    return register_user("user_a"), register_user("user_b")


def scrub_text(text):
    """负责 scrub_text 的函数职责。"""
    cleaned = text.replace(SMOKE_PASSWORD, "[redacted-password]")
    if _SMOKE_USER:
        cleaned = cleaned.replace(_SMOKE_USER["token"], "[redacted-token]")
    return cleaned

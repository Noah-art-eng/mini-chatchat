import os
import sys
import tempfile
import time
from pathlib import Path

import requests


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

FORBIDDEN_TEXT = (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "invalid_api_key",
    "OpenAI 401",
)


def pass_step(message):
    """负责 pass_step 的函数职责。"""
    print(f"[PASS] {message}")


def fail_step(message, response=None):
    """负责 fail_step 的函数职责。"""
    print(f"[FAIL] {message}")

    if response is not None:
        print(f"status={response.status_code}")
        print(f"body={response.text[:1200]}")

    sys.exit(1)


def request(method, path, token=None, **kwargs):
    """负责 request 的函数职责。"""
    headers = kwargs.pop("headers", {})

    if token:
        headers = {
            **headers,
            "Authorization": f"Bearer {token}",
        }

    try:
        return requests.request(
            method,
            f"{API_BASE}{path}",
            headers=headers,
            timeout=120,
            **kwargs,
        )
    except requests.ConnectionError:
        fail_step(f"Backend is not running at {API_BASE}")
    except requests.RequestException as exc:
        print(f"[FAIL] request failed: {method} {path}")
        print(exc)
        sys.exit(1)


def assert_safe_response(response, step_name):
    """负责 assert_safe_response 的函数职责。"""
    for text in FORBIDDEN_TEXT:
        if text.lower() in response.text.lower():
            fail_step(f"{step_name}: forbidden text found: {text}", response)


def parse_json(response, step_name):
    """负责 parse_json 的函数职责。"""
    try:
        return response.json()
    except ValueError:
        fail_step(f"{step_name}: response is not JSON", response)


def expect_status(response, expected, step_name):
    """负责 expect_status 的函数职责。"""
    assert_safe_response(response, step_name)

    if response.status_code != expected:
        fail_step(f"{step_name}: expected HTTP {expected}", response)

    return parse_json(response, step_name)


def expect_ok(response, step_name):
    """负责 expect_ok 的函数职责。"""
    return expect_status(response, 200, step_name)


def register_user(email, password, display_name):
    """负责 register_user 的函数职责。"""
    response = request(
        "POST",
        "/auth/register",
        json={
            "display_name": display_name,
            "email": email,
            "password": password,
        },
    )
    data = expect_ok(response, "POST /auth/register")

    token = data.get("access_token")
    user = data.get("user") or {}

    if not token:
        fail_step("POST /auth/register: missing access_token", response)

    if not user.get("id") or user.get("email") != email:
        fail_step("POST /auth/register: invalid user payload", response)

    print(f"registered user id={user['id']} email={email}")
    pass_step(f"POST /auth/register {email}")
    return token, user


def login_user(email, password):
    """负责 login_user 的函数职责。"""
    response = request(
        "POST",
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    data = expect_ok(response, "POST /auth/login")

    if not data.get("access_token"):
        fail_step("POST /auth/login: missing access_token", response)

    pass_step(f"POST /auth/login {email}")
    return data["access_token"]


def create_kb(token, kb_name):
    """负责 create_kb 的函数职责。"""
    response = request(
        "POST",
        "/knowledge_bases",
        token=token,
        json={
            "kb_name": kb_name,
        },
    )
    expect_ok(response, "POST /knowledge_bases")
    pass_step(f"created KB {kb_name}")


def switch_kb(token, kb_name):
    """负责 switch_kb 的函数职责。"""
    response = request(
        "POST",
        "/switch_kb",
        token=token,
        json={
            "kb_name": kb_name,
        },
    )
    expect_ok(response, "POST /switch_kb")
    pass_step(f"switched KB {kb_name}")


def upload_document(token, filename, content):
    """负责 upload_document 的函数职责。"""
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
                    "file": (filename, file, "text/plain"),
                },
            )
    finally:
        temp_path.unlink(missing_ok=True)

    data = expect_ok(response, "POST /upload")

    if data.get("error"):
        fail_step("POST /upload returned error", response)

    pass_step(f"uploaded document {filename}")


def create_conversation(token, kb_name):
    """负责 create_conversation 的函数职责。"""
    payload = {
        "mode": "local_kb",
        "kb_name": kb_name,
        "query": "What does this auth isolation test document say?",
        "stream": False,
        "top_k": 3,
        "score_threshold": 0.8,
        "prompt_name": "default",
        "return_direct": False,
        "rerank": False,
        "rerank_top_n": 3,
    }
    response = request("POST", "/kb_chat", token=token, json=payload)
    data = expect_ok(response, "POST /kb_chat authenticated local_kb")

    conversation_id = data.get("conversation_id")
    assistant_message_id = data.get("assistant_message_id")

    if not conversation_id or not assistant_message_id:
        fail_step("POST /kb_chat: missing conversation or assistant message id", response)

    print(
        "authenticated chat summary="
        f"conversation_id={conversation_id}, assistant_message_id={assistant_message_id}"
    )
    pass_step("POST /kb_chat writes authenticated user conversation")
    return conversation_id, assistant_message_id


def assert_forbidden_or_not_found(response, step_name):
    """负责 assert_forbidden_or_not_found 的函数职责。"""
    assert_safe_response(response, step_name)

    if response.status_code not in (403, 404):
        fail_step(f"{step_name}: expected HTTP 403 or 404", response)

    pass_step(f"{step_name} denied with HTTP {response.status_code}")


def check_auth_basics(user_a_token, user_a_email, password):
    """负责 check_auth_basics 的函数职责。"""
    response = request("GET", "/auth/me", token=user_a_token)
    data = expect_ok(response, "GET /auth/me")

    if not data.get("authenticated") or (data.get("user") or {}).get("email") != user_a_email:
        fail_step("GET /auth/me: authenticated user mismatch", response)

    pass_step("GET /auth/me authenticated")

    response = request("GET", "/auth/preferences", token=user_a_token)
    data = expect_ok(response, "GET /auth/preferences")
    preferences = data.get("preferences") or {}

    if "onboarding_completed" not in preferences:
        fail_step("GET /auth/preferences: missing onboarding_completed", response)

    response = request(
        "PATCH",
        "/auth/preferences",
        token=user_a_token,
        json={
            "onboarding_completed": True,
            "language": "en",
        },
    )
    data = expect_ok(response, "PATCH /auth/preferences")

    if not (data.get("preferences") or {}).get("onboarding_completed"):
        fail_step("PATCH /auth/preferences: onboarding not persisted", response)

    pass_step("auth preferences read/update")

    response = request(
        "POST",
        "/auth/login",
        json={
            "email": user_a_email,
            "password": f"{password}-wrong",
        },
    )
    expect_status(response, 401, "POST /auth/login wrong password")
    pass_step("wrong password rejected")

    response = request("GET", "/auth/me", headers={"Authorization": "Bearer invalid.token"})
    expect_status(response, 401, "GET /auth/me invalid JWT")
    pass_step("invalid JWT rejected")


def check_preference_isolation(user_a_token, user_b_token):
    """负责 check_preference_isolation 的函数职责。"""
    response = request(
        "PATCH",
        "/auth/preferences",
        token=user_a_token,
        json={
            "onboarding_completed": True,
            "language": "en",
            "developer_mode": True,
        },
    )
    expect_ok(response, "PATCH /auth/preferences user A")

    response = request("GET", "/auth/preferences", token=user_b_token)
    data = expect_ok(response, "GET /auth/preferences user B")
    preferences = data.get("preferences") or {}

    if preferences.get("developer_mode") is True:
        fail_step("User B inherited User A developer_mode preference", response)

    pass_step("user preferences are isolated")


def check_duplicate_email(email, password):
    """负责 check_duplicate_email 的函数职责。"""
    response = request(
        "POST",
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )
    expect_status(response, 400, "POST /auth/register duplicate email")
    pass_step("duplicate email rejected")


def check_disabled_user(email, password):
    """负责 check_disabled_user 的函数职责。"""
    sys.path.insert(0, str(BACKEND_DIR))
    from db import get_user_auth_by_email, set_user_active

    user = get_user_auth_by_email(email)

    if not user:
        fail_step("disabled user setup failed: user not found")

    set_user_active(user["id"], False)
    response = request(
        "POST",
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    expect_status(response, 401, "POST /auth/login disabled user")
    set_user_active(user["id"], True)
    pass_step("disabled user rejected")


def check_demo_compatibility():
    """负责 check_demo_compatibility 的函数职责。"""
    response = request("GET", "/auth/me")
    data = expect_ok(response, "GET /auth/me guest")

    if data.get("authenticated") or (data.get("user") or {}).get("id") != "guest":
        fail_step("GET /auth/me guest: expected runtime guest", response)

    response = request(
        "POST",
        "/temp_upload",
        files={
            "file": ("guest-temp.txt", b"Guest temp file isolation smoke content.", "text/plain"),
        },
    )
    data = expect_ok(response, "POST /temp_upload guest")

    if not data.get("temp_kb_id"):
        fail_step("POST /temp_upload guest: missing temp_kb_id", response)

    pass_step("unauthenticated demo/guest compatibility")


def check_user_scope_paths(user, kb_name, filename):
    """负责 check_user_scope_paths 的函数职责。"""
    user_root = BACKEND_DIR / "data" / "users" / f"user_{user['id']}"
    kb_root = user_root / "knowledge_bases" / kb_name
    upload_path = kb_root / "uploads" / filename
    vector_path = kb_root / "vector_store" / "index.faiss"

    if not user_root.exists():
        fail_step(f"user scope root missing: {user_root}")

    if not upload_path.exists():
        fail_step(f"user-scoped upload missing: {upload_path}")

    if not vector_path.exists():
        fail_step(f"user-scoped FAISS index missing: {vector_path}")

    print(f"user scope path={kb_root}")
    pass_step("FAISS/upload paths are user-scoped")


def get_first_chunk_id(token, filename):
    """负责 get_first_chunk_id 的函数职责。"""
    response = request("GET", f"/file_docs/{filename}", token=token)
    data = expect_ok(response, "GET /file_docs user A")
    chunks = data.get("chunks") or []

    if not chunks or not chunks[0].get("chunk_id"):
        fail_step("GET /file_docs user A: missing chunk_id", response)

    pass_step("GET /file_docs user A")
    return chunks[0]["chunk_id"]


def create_temp_kb(token):
    """负责 create_temp_kb 的函数职责。"""
    response = request(
        "POST",
        "/temp_upload",
        token=token,
        files={
            "file": (
                "auth-temp-private.txt",
                b"Private temp kb content for User A only.",
                "text/plain",
            ),
        },
    )
    data = expect_ok(response, "POST /temp_upload user A")
    temp_kb_id = data.get("temp_kb_id")

    if not temp_kb_id:
        fail_step("POST /temp_upload user A: missing temp_kb_id", response)

    pass_step("POST /temp_upload user A")
    return temp_kb_id


def assert_no_private_source(response, filename, step_name):
    """负责 assert_no_private_source 的函数职责。"""
    data = expect_ok(response, step_name)
    sources = data.get("results") or data.get("sources") or []
    if any(item.get("source") == filename for item in sources):
        fail_step(f"{step_name}: leaked private source {filename}", response)

    pass_step(step_name)


def check_cross_user_denials(
    user_b_token,
    kb_name,
    filename,
    conversation_id,
    assistant_message_id,
    chunk_id,
    temp_kb_id,
):
    """负责 check_cross_user_denials 的函数职责。"""
    response = request("GET", "/conversations", token=user_b_token)
    data = expect_ok(response, "B GET /conversations")
    if any(item.get("id") == conversation_id for item in data.get("conversations", [])):
        fail_step("B conversation list leaked A conversation", response)

    response = request("GET", "/knowledge_bases", token=user_b_token)
    data = expect_ok(response, "B GET /knowledge_bases")
    if any(item.get("kb_name") == kb_name for item in data.get("knowledge_bases", [])):
        fail_step("B knowledge base list leaked A KB", response)

    response = request("GET", "/documents", token=user_b_token)
    data = expect_ok(response, "B GET /documents")
    if any(item.get("filename") == filename for item in data.get("files", [])):
        fail_step("B document list leaked A document", response)

    response = request("GET", f"/conversations/{conversation_id}/messages", token=user_b_token)
    assert_forbidden_or_not_found(response, "B GET A conversation messages")

    response = request(
        "PATCH",
        f"/conversations/{conversation_id}",
        token=user_b_token,
        json={
            "title": "stolen",
        },
    )
    assert_forbidden_or_not_found(response, "B PATCH A conversation")

    response = request("DELETE", f"/conversations/{conversation_id}", token=user_b_token)
    assert_forbidden_or_not_found(response, "B DELETE A conversation")

    response = request(
        "POST",
        "/chat/feedback",
        token=user_b_token,
        json={
            "message_id": assistant_message_id,
            "score": 1,
        },
    )
    assert_forbidden_or_not_found(response, "B feedback on A message")

    response = request(
        "POST",
        "/switch_kb",
        token=user_b_token,
        json={
            "kb_name": kb_name,
        },
    )
    assert_forbidden_or_not_found(response, "B switch to A KB")

    response = request("GET", f"/knowledge_bases/{kb_name}/export", token=user_b_token)
    assert_forbidden_or_not_found(response, "B export A KB")

    response = request("DELETE", f"/knowledge_bases/{kb_name}", token=user_b_token)
    assert_forbidden_or_not_found(response, "B delete A KB")

    response = request("GET", f"/documents/{filename}/download", token=user_b_token)
    assert_forbidden_or_not_found(response, "B download A document")

    response = request(
        "POST",
        f"/documents/{filename}/reindex",
        token=user_b_token,
        json={
            "chunk_size": 300,
            "chunk_overlap": 50,
        },
    )
    assert_forbidden_or_not_found(response, "B reindex A document")

    response = request("DELETE", f"/documents/{filename}", token=user_b_token)
    assert_forbidden_or_not_found(response, "B delete A document")

    response = request("GET", f"/file_docs/{filename}", token=user_b_token)
    assert_forbidden_or_not_found(response, "B file_docs on A document")

    response = request("GET", f"/chunk/{chunk_id}", token=user_b_token)
    assert_forbidden_or_not_found(response, "B chunk on A document")

    response = request(
        "POST",
        "/search_docs",
        token=user_b_token,
        json={
            "query": "private auth isolation",
            "top_k": 5,
        },
    )
    assert_no_private_source(response, filename, "B search_docs cannot see A source")

    response = request(
        "POST",
        "/kb_chat",
        token=user_b_token,
        json={
            "mode": "local_kb",
            "kb_name": kb_name,
            "query": "private auth isolation",
            "stream": False,
            "return_direct": True,
        },
    )
    assert_forbidden_or_not_found(response, "B kb_chat on A KB")

    response = request(
        "POST",
        "/kb_chat",
        token=user_b_token,
        json={
            "mode": "temp_kb",
            "temp_kb_id": temp_kb_id,
            "query": "private temp kb",
            "stream": False,
            "return_direct": True,
        },
    )
    assert_forbidden_or_not_found(response, "B temp_kb on A temp KB")

    response = request(
        "POST",
        "/agent/tools/kb_search/run",
        token=user_b_token,
        json={
            "arguments": {
                "query": "private auth isolation",
                "kb_name": kb_name,
                "top_k": 3,
            },
        },
    )
    data = expect_ok(response, "B direct kb_search on A KB")
    if data.get("ok"):
        fail_step("B direct kb_search unexpectedly succeeded on A KB", response)

    response = request(
        "POST",
        "/agent/run",
        token=user_b_token,
        json={
            "query": "Search this private auth isolation document.",
            "kb_name": kb_name,
            "tools": ["kb_search"],
        },
    )
    data = expect_ok(response, "B agent kb_search on A KB")
    tool_result = data.get("tool_result") or {}
    if tool_result.get("ok"):
        fail_step("B agent kb_search unexpectedly succeeded on A KB", response)

    pass_step("cross-user search/temp_kb/agent/tool denials")


def cleanup_user_a_resources(token, kb_name, conversation_id):
    """负责 cleanup_user_a_resources 的函数职责。"""
    request("DELETE", f"/conversations/{conversation_id}", token=token)
    request("DELETE", f"/knowledge_bases/{kb_name}", token=token)


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    suffix = f"{int(time.time())}"
    password = "CorrectHorse123"
    user_a_email = f"auth-a-{suffix}@example.test"
    user_b_email = f"auth-b-{suffix}@example.test"
    user_disabled_email = f"auth-disabled-{suffix}@example.test"
    kb_name = f"auth_isolation_{suffix}"
    filename = f"auth-isolation-{suffix}.txt"

    check_demo_compatibility()
    token_a, user_a = register_user(user_a_email, password, "Auth User A")
    check_duplicate_email(user_a_email, password)
    token_a = login_user(user_a_email, password)
    check_auth_basics(token_a, user_a_email, password)

    token_b, _ = register_user(user_b_email, password, "Auth User B")
    check_preference_isolation(token_a, token_b)
    _, _ = register_user(user_disabled_email, password, "Disabled User")
    check_disabled_user(user_disabled_email, password)

    create_kb(token_a, kb_name)
    switch_kb(token_a, kb_name)
    upload_document(
        token_a,
        filename,
        "This private auth isolation document belongs only to User A.",
    )
    conversation_id, assistant_message_id = create_conversation(token_a, kb_name)
    chunk_id = get_first_chunk_id(token_a, filename)
    temp_kb_id = create_temp_kb(token_a)
    check_user_scope_paths(user_a, kb_name, filename)
    check_cross_user_denials(
        token_b,
        kb_name,
        filename,
        conversation_id,
        assistant_message_id,
        chunk_id,
        temp_kb_id,
    )
    cleanup_user_a_resources(token_a, kb_name, conversation_id)
    pass_step("email auth and user isolation smoke test complete")


if __name__ == "__main__":
    main()

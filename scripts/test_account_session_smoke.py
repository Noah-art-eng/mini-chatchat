import os
import sys
import time
from pathlib import Path

import requests


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from auth.config import get_auth_cookie_name  # noqa: E402
from auth.session import hash_refresh_token  # noqa: E402
from db import create_auth_session, get_user_auth_by_email, set_user_active  # noqa: E402


PASSWORD = "CorrectHorse123"
FORBIDDEN_TEXT = (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "invalid_api_key",
    "OpenAI 401",
    "refresh_token_hash",
    "password_hash",
    "refresh_token",
    "mini_chatchat_refresh=",
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


def assert_safe_response(response, step_name):
    """负责 assert_safe_response 的函数职责。"""
    lower = response.text.lower()
    for text in FORBIDDEN_TEXT:
        if text.lower() in lower:
            fail_step(f"{step_name}: forbidden text found: {text}", response)


def expect_status(response, status, step_name):
    """负责 expect_status 的函数职责。"""
    assert_safe_response(response, step_name)
    if response.status_code != status:
        fail_step(f"{step_name}: expected HTTP {status}", response)
    try:
        return response.json()
    except ValueError:
        fail_step(f"{step_name}: response is not JSON", response)


def request(session, method, path, token=None, **kwargs):
    """负责 request 的函数职责。"""
    headers = kwargs.pop("headers", {})
    if token:
        headers = {
            **headers,
            "Authorization": f"Bearer {token}",
        }

    try:
        return session.request(
            method,
            f"{API_BASE}{path}",
            headers=headers,
            timeout=90,
            **kwargs,
        )
    except requests.ConnectionError:
        fail_step(f"Backend is not running at {API_BASE}")


def unique_email(prefix):
    """负责 unique_email 的函数职责。"""
    return f"{prefix}-{int(time.time() * 1000)}@example.test"


def register(session, prefix):
    """负责 register 的函数职责。"""
    email = unique_email(prefix)
    response = request(
        session,
        "POST",
        "/auth/register",
        json={
            "display_name": f"Account {prefix}",
            "email": email,
            "password": PASSWORD,
        },
    )
    data = expect_status(response, 200, "POST /auth/register")
    return {
        "email": email,
        "token": data["access_token"],
        "user": data["user"],
        "session_id": data["session_id"],
    }


def login(session, email):
    """负责 login 的函数职责。"""
    response = request(
        session,
        "POST",
        "/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )
    data = expect_status(response, 200, "POST /auth/login")
    return {
        "email": email,
        "token": data["access_token"],
        "user": data["user"],
        "session_id": data["session_id"],
    }


def session_by_id(sessions, session_id):
    """负责 session_by_id 的函数职责。"""
    for session in sessions:
        if session.get("session_id") == session_id:
            return session
    return None


def check_account_update(user):
    """负责 check_account_update 的函数职责。"""
    session = requests.Session()
    response = request(session, "GET", "/auth/account", token=user["token"])
    data = expect_status(response, 200, "GET /auth/account")
    if data["user"]["email"] != user["email"]:
        fail_step("GET /auth/account returned wrong user", response)

    response = request(
        session,
        "PATCH",
        "/auth/account",
        token=user["token"],
        json={"display_name": "Updated Account Smoke"},
    )
    data = expect_status(response, 200, "PATCH /auth/account display_name")
    if data["user"]["display_name"] != "Updated Account Smoke":
        fail_step("display_name was not updated", response)

    response = request(
        session,
        "PATCH",
        "/auth/account",
        token=user["token"],
        json={"display_name": ""},
    )
    expect_status(response, 400, "PATCH /auth/account empty name rejected")

    response = request(
        session,
        "PATCH",
        "/auth/account",
        token=user["token"],
        json={"display_name": "x" * 81},
    )
    expect_status(response, 400, "PATCH /auth/account long name rejected")

    response = request(
        session,
        "PATCH",
        "/auth/account",
        token=user["token"],
        json={"display_name": "Allowed", "email": "changed@example.test"},
    )
    expect_status(response, 422, "PATCH /auth/account extra email rejected")
    pass_step("account profile update and field restrictions")


def check_session_listing_and_revoke(user, second_login):
    """负责 check_session_listing_and_revoke 的函数职责。"""
    session = requests.Session()
    response = request(session, "GET", "/auth/sessions", token=user["token"])
    data = expect_status(response, 200, "GET /auth/sessions")
    sessions = data.get("sessions") or []
    current = session_by_id(sessions, user["session_id"])
    other = session_by_id(sessions, second_login["session_id"])

    if not current or not current.get("is_current"):
        fail_step("current session was not marked", response)

    if not other or other.get("is_current"):
        fail_step("other session was not listed correctly", response)

    body = response.text.lower()
    if "hash" in body or "token" in body:
        fail_step("session list leaked hash/token text", response)

    if current.get("ip_address") in {"127.0.0.1", "::1"}:
        fail_step("session list leaked full IP address", response)

    response = request(
        session,
        "DELETE",
        f"/auth/sessions/{second_login['session_id']}",
        token=user["token"],
    )
    expect_status(response, 200, "DELETE /auth/sessions/{session_id}")

    response = request(second_login["http"], "POST", "/auth/refresh")
    expect_status(response, 401, "revoked session refresh rejected")
    pass_step("session list and single-session revoke")


def check_cross_user_session_isolation(user_a, user_b):
    """负责 check_cross_user_session_isolation 的函数职责。"""
    session = requests.Session()
    response = request(
        session,
        "DELETE",
        f"/auth/sessions/{user_a['session_id']}",
        token=user_b["token"],
    )
    expect_status(response, 404, "User B cannot revoke User A session")
    pass_step("cross-user session isolation")


def check_logout_others_and_all(user):
    """负责 check_logout_others_and_all 的函数职责。"""
    current_http = requests.Session()
    current = login(current_http, user["email"])
    current["http"] = current_http

    other_http = requests.Session()
    other = login(other_http, user["email"])
    other["http"] = other_http

    response = request(
        current_http,
        "POST",
        "/auth/logout-others",
        token=current["token"],
    )
    data = expect_status(response, 200, "POST /auth/logout-others")
    if data.get("revoked_sessions", 0) < 1:
        fail_step("logout-others did not revoke any other sessions", response)

    response = request(other_http, "POST", "/auth/refresh")
    expect_status(response, 401, "other session refresh rejected")

    response = request(current_http, "POST", "/auth/refresh")
    data = expect_status(response, 200, "current session survived logout-others")
    current["token"] = data["access_token"]

    response = request(
        current_http,
        "POST",
        "/auth/logout-all",
        token=current["token"],
    )
    data = expect_status(response, 200, "POST /auth/logout-all")
    if data.get("revoked_sessions", 0) < 1:
        fail_step("logout-all did not revoke current session", response)

    response = request(current_http, "POST", "/auth/refresh")
    expect_status(response, 401, "logout-all refresh rejected")
    pass_step("logout-others and logout-all")


def check_origin_and_rate_limit(user):
    """负责 check_origin_and_rate_limit 的函数职责。"""
    session = requests.Session()
    response = request(
        session,
        "POST",
        "/auth/refresh",
        headers={"Origin": "https://evil.example"},
    )
    expect_status(response, 403, "unknown Origin rejected")

    response = request(
        session,
        "POST",
        "/auth/refresh",
        headers={"Origin": "http://127.0.0.1:5173"},
    )
    expect_status(response, 401, "allowed Origin reaches auth handler")

    email = unique_email("rate-limit")
    for attempt in range(6):
        response = request(
            session,
            "POST",
            "/auth/login",
            json={"email": email, "password": "wrong-password"},
        )
        if attempt < 5:
            expect_status(response, 401, "failed login counted")
        else:
            expect_status(response, 429, "login rate limit triggered")

    pass_step("origin check and login rate limit")


def check_expired_cleanup(user):
    """负责 check_expired_cleanup 的函数职责。"""
    expired_session_id = f"expired-smoke-{int(time.time() * 1000)}"
    create_auth_session(
        expired_session_id,
        user["user"]["id"],
        hash_refresh_token("expired-token"),
        "2000-01-01 00:00:00",
        user_agent="Python requests",
        ip_address="127.0.0.1",
    )

    session = requests.Session()
    response = request(session, "GET", "/auth/sessions", token=user["token"])
    data = expect_status(response, 200, "expired session cleanup list")
    expired = session_by_id(data.get("sessions") or [], expired_session_id)
    if not expired or expired.get("is_active"):
        fail_step("expired session was not marked inactive", response)
    pass_step("expired session cleanup")


def check_disabled_user_account(user):
    """负责 check_disabled_user_account 的函数职责。"""
    user_record = get_user_auth_by_email(user["email"])
    if not user_record:
        fail_step("disabled user setup failed")

    set_user_active(user_record["id"], False)
    try:
        session = requests.Session()
        response = request(session, "GET", "/auth/account", token=user["token"])
        expect_status(response, 401, "disabled user account rejected")
    finally:
        set_user_active(user_record["id"], True)

    pass_step("disabled user account request rejected")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    health = requests.get(f"{API_BASE}/models", timeout=10)
    if health.status_code != 200:
        fail_step(f"Backend is not running at {API_BASE}", health)

    user_a_http = requests.Session()
    user_a = register(user_a_http, "account-a")
    user_a["http"] = user_a_http

    user_a_second_http = requests.Session()
    user_a_second = login(user_a_second_http, user_a["email"])
    user_a_second["http"] = user_a_second_http

    user_b_http = requests.Session()
    user_b = register(user_b_http, "account-b")
    user_b["http"] = user_b_http

    check_account_update(user_a)
    check_session_listing_and_revoke(user_a, user_a_second)
    check_cross_user_session_isolation(user_a, user_b)
    check_expired_cleanup(user_a)
    check_logout_others_and_all(user_a)
    check_origin_and_rate_limit(user_a)
    check_disabled_user_account(user_b)
    pass_step("account/session smoke test complete")


if __name__ == "__main__":
    main()

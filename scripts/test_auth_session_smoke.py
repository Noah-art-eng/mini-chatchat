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
from db import get_user_auth_by_email, set_user_active  # noqa: E402


PASSWORD = "CorrectHorse123"
FORBIDDEN_TEXT = (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "invalid_api_key",
    "OpenAI 401",
    "refresh_token",
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


def request(session, method, path, **kwargs):
    """负责 request 的函数职责。"""
    try:
        return session.request(
            method,
            f"{API_BASE}{path}",
            timeout=90,
            **kwargs,
        )
    except requests.ConnectionError:
        fail_step(f"Backend is not running at {API_BASE}")


def unique_email(prefix):
    """负责 unique_email 的函数职责。"""
    return f"{prefix}-{int(time.time() * 1000)}@example.test"


def register(session, email):
    """负责 register 的函数职责。"""
    response = request(
        session,
        "POST",
        "/auth/register",
        json={
            "display_name": "Session Smoke",
            "email": email,
            "password": PASSWORD,
        },
    )
    data = expect_status(response, 200, "POST /auth/register")
    token = data.get("access_token")
    if not token:
        fail_step("POST /auth/register missing access token", response)
    if "refresh" in data:
        fail_step("POST /auth/register leaked refresh token in JSON", response)
    return data, response


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
    if "refresh" in data:
        fail_step("POST /auth/login leaked refresh token in JSON", response)
    return data, response


def get_cookie_value(session):
    """负责 get_cookie_value 的函数职责。"""
    return session.cookies.get(get_auth_cookie_name())


def assert_refresh_cookie(response, session):
    """负责 assert_refresh_cookie 的函数职责。"""
    cookie = get_cookie_value(session)
    if not cookie:
        fail_step("refresh cookie missing", response)

    set_cookie = response.headers.get("set-cookie", "")
    lowered = set_cookie.lower()
    if "httponly" not in lowered:
        fail_step("refresh cookie missing HttpOnly flag", response)
    if "samesite=lax" not in lowered and "samesite=strict" not in lowered:
        fail_step("refresh cookie missing SameSite flag", response)
    if f"{get_auth_cookie_name()}=" not in set_cookie:
        fail_step("refresh cookie name missing in Set-Cookie", response)

    pass_step("refresh cookie flags")


def check_refresh_rotation(session, access_token):
    """负责 check_refresh_rotation 的函数职责。"""
    before = get_cookie_value(session)
    response = request(session, "POST", "/auth/refresh")
    data = expect_status(response, 200, "POST /auth/refresh")
    after = get_cookie_value(session)

    if not data.get("access_token"):
        fail_step("POST /auth/refresh missing access token", response)
    if before == after:
        fail_step("refresh rotation did not change cookie", response)

    response = request(
        session,
        "GET",
        "/auth/preferences",
        headers={
            "Authorization": f"Bearer {data['access_token']}",
        },
    )
    expect_status(response, 200, "GET /auth/preferences after refresh")

    old_refresh_session = requests.Session()
    old_refresh_session.cookies.set(
        get_auth_cookie_name(),
        before,
        path="/auth",
        domain="127.0.0.1",
    )
    response = request(old_refresh_session, "POST", "/auth/refresh")
    expect_status(response, 401, "old refresh token reuse rejected")

    response = request(
        session,
        "GET",
        "/auth/preferences",
        headers={
            "Authorization": f"Bearer {data['access_token']}",
        },
    )
    expect_status(response, 401, "access token revoked after refresh reuse")

    if not access_token:
        fail_step("missing original access token")

    pass_step("refresh rotation and reuse detection")


def check_missing_invalid_and_token_types(access_token, refresh_token):
    """负责 check_missing_invalid_and_token_types 的函数职责。"""
    session = requests.Session()
    response = request(session, "POST", "/auth/refresh")
    expect_status(response, 401, "missing refresh cookie")

    session.cookies.set(get_auth_cookie_name(), "not-a-token", path="/auth")
    response = request(session, "POST", "/auth/refresh")
    expect_status(response, 401, "invalid refresh token")

    session = requests.Session()
    session.cookies.set(get_auth_cookie_name(), access_token, path="/auth")
    response = request(session, "POST", "/auth/refresh")
    expect_status(response, 401, "access token cannot refresh")

    session = requests.Session()
    response = request(
        session,
        "GET",
        "/auth/preferences",
        headers={
            "Authorization": f"Bearer {refresh_token}",
        },
    )
    expect_status(response, 401, "refresh token cannot access API")
    pass_step("missing/invalid/token-type refresh checks")


def check_logout_revokes(email):
    """负责 check_logout_revokes 的函数职责。"""
    session = requests.Session()
    data, response = login(session, email)
    assert_refresh_cookie(response, session)
    access_token = data["access_token"]

    response = request(
        session,
        "POST",
        "/auth/logout",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )
    expect_status(response, 200, "POST /auth/logout")

    set_cookie = response.headers.get("set-cookie", "").lower()
    if "max-age=0" not in set_cookie and "expires=" not in set_cookie:
        fail_step("logout did not clear refresh cookie", response)

    response = request(session, "POST", "/auth/refresh")
    expect_status(response, 401, "refresh after logout rejected")
    pass_step("logout revokes session and clears cookie")


def check_disabled_user_refresh():
    """负责 check_disabled_user_refresh 的函数职责。"""
    email = unique_email("auth-disabled-refresh")
    session = requests.Session()
    register(session, email)
    user = get_user_auth_by_email(email)
    if not user:
        fail_step("disabled user setup failed")

    set_user_active(user["id"], False)
    try:
        response = request(session, "POST", "/auth/refresh")
        expect_status(response, 401, "disabled user refresh rejected")
    finally:
        set_user_active(user["id"], True)

    pass_step("disabled user cannot refresh")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    email = unique_email("auth-session")
    session = requests.Session()
    data, response = register(session, email)
    assert_refresh_cookie(response, session)
    refresh_token = get_cookie_value(session)
    check_missing_invalid_and_token_types(data["access_token"], refresh_token)
    check_logout_revokes(email)
    check_disabled_user_refresh()

    session = requests.Session()
    data, response = login(session, email)
    assert_refresh_cookie(response, session)
    check_refresh_rotation(session, data["access_token"])
    pass_step("auth session smoke test complete")


if __name__ == "__main__":
    main()

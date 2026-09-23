import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import requests
from fastapi import HTTPException
from starlette.responses import Response


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from auth.oauth import (  # noqa: E402
    OAuthProfile,
    create_oauth_authorization,
    link_oauth_profile,
    pop_oauth_state,
    public_provider_status,
    resolve_or_create_oauth_user,
    unlink_oauth_provider,
)
from auth.session import create_login_session  # noqa: E402
from db import (  # noqa: E402
    create_email_user,
    get_oauth_account,
    get_oauth_account_for_user,
    get_user_by_email,
    init_db,
    public_user_dict,
)
from auth.password import hash_password  # noqa: E402


PASSWORD = "CorrectHorse123"
FORBIDDEN_TEXT = (
    "GOOGLE_CLIENT_SECRET",
    "GITHUB_CLIENT_SECRET",
    "access_token",
    "refresh_token_hash",
    "password_hash",
    "invalid_api_key",
    "OpenAI 401",
)


class FakeRequest:
    """负责 FakeRequest 的类职责。"""
    headers = {"user-agent": "oauth-smoke"}
    client = SimpleNamespace(host="127.0.0.1")


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


def assert_safe_text(text, step_name):
    """负责 assert_safe_text 的函数职责。"""
    lower = text.lower()
    for item in FORBIDDEN_TEXT:
        if item.lower() in lower:
            fail_step(f"{step_name}: leaked forbidden text {item}")


def unique_email(prefix):
    """负责 unique_email 的函数职责。"""
    return f"{prefix}-{int(time.time() * 1000)}@example.test"


def expect_http(response, status, step_name):
    """负责 expect_http 的函数职责。"""
    assert_safe_text(response.text, step_name)
    if response.status_code != status:
        fail_step(f"{step_name}: expected HTTP {status}", response)
    return response


def check_provider_api():
    """负责 check_provider_api 的函数职责。"""
    response = requests.get(f"{API_BASE}/auth/oauth/providers", timeout=15)
    expect_http(response, 200, "GET /auth/oauth/providers")
    data = response.json()
    names = {provider["provider"] for provider in data.get("providers", [])}
    if names != {"github", "google"}:
        fail_step("OAuth providers API did not return google/github", response)
    if "client_secret" in response.text.lower():
        fail_step("OAuth providers API leaked client secret", response)

    response = requests.get(
        f"{API_BASE}/auth/oauth/google/callback?code=x&state=bad-state",
        allow_redirects=False,
        timeout=15,
    )
    expect_http(response, 302, "OAuth invalid state redirects")
    if "oauth_error=" not in response.headers.get("location", ""):
        fail_step("invalid state did not redirect with oauth_error", response)

    response = requests.get(
        f"{API_BASE}/auth/oauth/github/callback?error=access_denied",
        allow_redirects=False,
        timeout=15,
    )
    expect_http(response, 302, "OAuth cancellation redirects")
    if "oauth_error=" not in response.headers.get("location", ""):
        fail_step("cancelled OAuth did not redirect with oauth_error", response)
    pass_step("OAuth provider API and callback error handling")


def check_authorization_state_and_pkce():
    """负责 check_authorization_state_and_pkce 的函数职责。"""
    os.environ["GOOGLE_CLIENT_ID"] = "google-client"
    os.environ["GOOGLE_CLIENT_SECRET"] = "google-secret"
    os.environ["GOOGLE_REDIRECT_URI"] = (
        "http://127.0.0.1:8001/auth/oauth/google/callback"
    )
    authorization = create_oauth_authorization("google", mode="login")
    url = authorization["authorization_url"]
    if "code_challenge=" not in url or "state=" not in url:
        fail_step("Google authorization URL missing state or PKCE challenge")

    try:
        pop_oauth_state("wrong-state", "google")
        fail_step("invalid OAuth state was accepted")
    except HTTPException as exc:
        if exc.status_code != 400:
            fail_step("invalid OAuth state returned wrong status")

    record = pop_oauth_state(authorization["state"], "google")
    if not record.get("code_verifier"):
        fail_step("OAuth state did not store code verifier")
    pass_step("OAuth state and PKCE")


def check_first_login_and_auto_bind():
    """负责 check_first_login_and_auto_bind 的函数职责。"""
    google_email = unique_email("oauth-google-first")
    google_profile = OAuthProfile(
        provider="google",
        provider_user_id=f"google-{google_email}",
        email=google_email,
        display_name="Google User",
        avatar_url="https://example.test/avatar.png",
    )
    user = resolve_or_create_oauth_user(google_profile)
    if user["email"] != google_email or user["auth_provider"] != "google":
        fail_step("Google first login did not create OAuth user")
    if not get_oauth_account("google", google_profile.provider_user_id):
        fail_step("Google first login did not create oauth account")

    repeated = resolve_or_create_oauth_user(google_profile)
    if repeated["id"] != user["id"]:
        fail_step("Repeated Google login created a duplicate user")

    existing_email = unique_email("oauth-existing")
    existing = create_email_user(
        existing_email,
        hash_password(PASSWORD),
        display_name="Existing Email User",
    )
    profile = OAuthProfile(
        provider="google",
        provider_user_id=f"google-existing-{existing_email}",
        email=existing_email,
        display_name="Existing Email User",
    )
    resolved = resolve_or_create_oauth_user(profile)
    if resolved["id"] != existing["id"]:
        fail_step("Google existing email was not auto-bound")
    pass_step("Google first login, repeated login, and existing-email auto-bind")


def check_github_login_and_binding_rules():
    """负责 check_github_login_and_binding_rules 的函数职责。"""
    email = unique_email("oauth-github-first")
    profile = OAuthProfile(
        provider="github",
        provider_user_id=f"github-{email}",
        email=email,
        display_name="GitHub User",
    )
    user = resolve_or_create_oauth_user(profile)
    if user["email"] != email or user["auth_provider"] != "github":
        fail_step("GitHub first login did not create OAuth user")

    user_a = create_email_user(
        unique_email("oauth-link-a"),
        hash_password(PASSWORD),
        display_name="Link A",
    )
    user_b = create_email_user(
        unique_email("oauth-link-b"),
        hash_password(PASSWORD),
        display_name="Link B",
    )
    link_profile = OAuthProfile(
        provider="github",
        provider_user_id=f"github-link-{user_a['id']}",
        email=user_a["email"],
        display_name="Link A",
    )
    link_oauth_profile(user_a["id"], link_profile)
    if not get_oauth_account_for_user(user_a["id"], "github"):
        fail_step("GitHub link did not persist")

    try:
        link_oauth_profile(user_b["id"], link_profile)
        fail_step("cross-user OAuth binding was accepted")
    except HTTPException as exc:
        if exc.status_code != 409:
            fail_step("cross-user OAuth binding returned wrong status")

    unlink_oauth_provider(user_a["id"], "github")
    if get_oauth_account_for_user(user_a["id"], "github"):
        fail_step("OAuth unlink did not remove account")

    try:
        unlink_oauth_provider(user["id"], "github")
        fail_step("unlinking last login method was accepted")
    except HTTPException as exc:
        if exc.status_code != 400:
            fail_step("unlinking last login method returned wrong status")
    pass_step("GitHub login, link, unlink, and cross-user rejection")


def check_session_reuse():
    """负责 check_session_reuse 的函数职责。"""
    email = unique_email("oauth-session")
    profile = OAuthProfile(
        provider="google",
        provider_user_id=f"google-session-{email}",
        email=email,
        display_name="Session User",
    )
    user = resolve_or_create_oauth_user(profile)
    response = Response()
    token, expires_in, session_id = create_login_session(user, FakeRequest(), response)
    body = {
        "short_token_issued": bool(token),
        "expires_in": expires_in,
        "session_id": session_id,
        "user": public_user_dict(user),
    }
    text = str(body)
    assert_safe_text(text, "OAuth session response")
    cookie = response.headers.get("set-cookie", "")
    if "HttpOnly" not in cookie or "mini_chatchat_refresh" not in cookie:
        fail_step("OAuth-created session did not set HttpOnly refresh cookie")
    pass_step("OAuth login reuses HttpOnly refresh session system")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    init_db()

    try:
        health = requests.get(f"{API_BASE}/models", timeout=10)
    except requests.ConnectionError:
        fail_step(f"Backend is not running at {API_BASE}")
    expect_http(health, 200, "GET /models")

    check_provider_api()
    check_authorization_state_and_pkce()
    check_first_login_and_auto_bind()
    check_github_login_and_binding_rules()
    check_session_reuse()

    providers = public_provider_status()
    if {item["provider"] for item in providers} != {"github", "google"}:
        fail_step("public provider status missing providers")
    pass_step("OAuth smoke test complete")


if __name__ == "__main__":
    main()

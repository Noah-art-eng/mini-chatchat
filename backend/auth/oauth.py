import base64
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from fastapi import HTTPException, Request, Response

from db import (
    create_default_kb,
    create_user,
    delete_oauth_account_for_user,
    get_oauth_account,
    get_oauth_account_for_user,
    get_user_by_email,
    get_user_by_id,
    list_oauth_accounts_for_user,
    public_oauth_account,
    upsert_oauth_account,
    user_login_method_count,
)
from .config import get_frontend_base_url, get_oauth_provider_config
from .session import create_login_session


OAUTH_PROVIDERS = {"google", "github"}
OAUTH_STATE_TTL_SECONDS = 10 * 60
_oauth_states: dict[str, dict] = {}


@dataclass(frozen=True)
class OAuthProfile:
    """负责 OAuthProfile 的类职责。"""
    provider: str
    provider_user_id: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None


def cleanup_oauth_states():
    """负责 cleanup_oauth_states 的函数职责。"""
    now = time.time()
    expired = [
        state
        for state, record in _oauth_states.items()
        if record["expires_at"] < now
    ]
    for state in expired:
        _oauth_states.pop(state, None)


def base64_urlsafe_digest(value: bytes):
    """负责 base64_urlsafe_digest 的函数职责。"""
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def create_pkce_pair():
    """负责 create_pkce_pair 的函数职责。"""
    verifier = secrets.token_urlsafe(64)
    challenge = base64_urlsafe_digest(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def get_provider_metadata(provider: str):
    """负责 get_provider_metadata 的函数职责。"""
    if provider == "google":
        return {
            "name": "google",
            "label": "Google",
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
            "scope": "openid email profile",
            "pkce": True,
        }

    if provider == "github":
        return {
            "name": "github",
            "label": "GitHub",
            "authorize_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "userinfo_url": "https://api.github.com/user",
            "emails_url": "https://api.github.com/user/emails",
            "scope": "read:user user:email",
            "pkce": True,
        }

    raise HTTPException(status_code=404, detail="oauth provider not found")


def is_localhost_url(url: str):
    """负责 is_localhost_url 的函数职责。"""
    parsed = urllib.parse.urlparse(url)
    return parsed.hostname in {"127.0.0.1", "localhost"}


def validate_redirect_uri(url: str):
    """负责 validate_redirect_uri 的函数职责。"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "https":
        return

    if parsed.scheme == "http" and is_localhost_url(url):
        return

    raise HTTPException(status_code=500, detail="oauth redirect URI must use HTTPS")


def get_oauth_provider(provider: str):
    """负责 get_oauth_provider 的函数职责。"""
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail="oauth provider not found")

    metadata = get_provider_metadata(provider)
    config = get_oauth_provider_config(provider)
    validate_redirect_uri(config["redirect_uri"])
    configured = bool(config["client_id"] and config["client_secret"])

    return {
        **metadata,
        **config,
        "configured": configured,
    }


def public_provider_status(user_id: int | None = None):
    """负责 public_provider_status 的函数职责。"""
    providers = []
    for provider_name in sorted(OAUTH_PROVIDERS):
        provider = get_oauth_provider(provider_name)
        account = (
            get_oauth_account_for_user(user_id, provider_name)
            if user_id is not None
            else None
        )
        providers.append({
            "provider": provider_name,
            "label": provider["label"],
            "configured": provider["configured"],
            "linked": account is not None,
            "account": public_oauth_account(account) if account else None,
        })
    return providers


def create_oauth_authorization(provider_name: str, mode="login", user_id=None):
    """负责 create_oauth_authorization 的函数职责。"""
    provider = get_oauth_provider(provider_name)
    if not provider["configured"]:
        raise HTTPException(status_code=503, detail="oauth provider is not configured")

    if mode not in {"login", "link"}:
        raise HTTPException(status_code=400, detail="invalid oauth mode")

    verifier, challenge = create_pkce_pair()
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "provider": provider_name,
        "mode": mode,
        "user_id": user_id,
        "code_verifier": verifier,
        "expires_at": time.time() + OAUTH_STATE_TTL_SECONDS,
    }

    query = {
        "client_id": provider["client_id"],
        "redirect_uri": provider["redirect_uri"],
        "response_type": "code",
        "scope": provider["scope"],
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    if provider_name == "google":
        query["access_type"] = "online"
        query["include_granted_scopes"] = "true"
        query["prompt"] = "select_account"
    elif provider_name == "github":
        query["allow_signup"] = "true"

    return {
        "authorization_url": f"{provider['authorize_url']}?{urllib.parse.urlencode(query)}",
        "state": state,
        "provider": provider_name,
        "mode": mode,
    }


def pop_oauth_state(state: str | None, provider_name: str):
    """负责 pop_oauth_state 的函数职责。"""
    cleanup_oauth_states()
    if not state:
        raise HTTPException(status_code=400, detail="oauth state missing")

    record = _oauth_states.pop(state, None)
    if not record or record.get("provider") != provider_name:
        raise HTTPException(status_code=400, detail="oauth state invalid")

    return record


def request_json(url: str, data=None, headers=None, method=None):
    """负责 request_json 的函数职责。"""
    body = None
    request_headers = headers or {}
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        request_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            **request_headers,
        }

    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method or ("POST" if data is not None else "GET"),
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:200]
        raise HTTPException(status_code=502, detail=f"oauth provider error: {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail="oauth provider unavailable") from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        parsed = urllib.parse.parse_qs(text)
        if parsed:
            return {
                key: values[0]
                for key, values in parsed.items()
            }
        raise HTTPException(status_code=502, detail="oauth provider returned invalid JSON") from exc


def exchange_code_for_token(provider_name: str, code: str, code_verifier: str):
    """负责 exchange_code_for_token 的函数职责。"""
    provider = get_oauth_provider(provider_name)
    payload = {
        "client_id": provider["client_id"],
        "client_secret": provider["client_secret"],
        "code": code,
        "redirect_uri": provider["redirect_uri"],
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }
    return request_json(
        provider["token_url"],
        data=payload,
        headers={"Accept": "application/json"},
    )


def get_google_profile(access_token: str):
    """负责 get_google_profile 的函数职责。"""
    data = request_json(
        get_provider_metadata("google")["userinfo_url"],
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="oauth provider email missing")
    return OAuthProfile(
        provider="google",
        provider_user_id=str(data.get("sub")),
        email=email.strip().lower(),
        display_name=data.get("name") or email,
        avatar_url=data.get("picture"),
    )


def get_github_primary_email(access_token: str):
    """负责 get_github_primary_email 的函数职责。"""
    provider = get_provider_metadata("github")
    emails = request_json(
        provider["emails_url"],
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
        },
        method="GET",
    )
    if not isinstance(emails, list):
        return None
    verified = [
        item
        for item in emails
        if item.get("email") and item.get("verified")
    ]
    primary = next((item for item in verified if item.get("primary")), None)
    selected = primary or (verified[0] if verified else None)
    return selected.get("email") if selected else None


def get_github_profile(access_token: str):
    """负责 get_github_profile 的函数职责。"""
    data = request_json(
        get_provider_metadata("github")["userinfo_url"],
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
        },
        method="GET",
    )
    email = data.get("email") or get_github_primary_email(access_token)
    if not email:
        raise HTTPException(status_code=400, detail="oauth provider email missing")
    return OAuthProfile(
        provider="github",
        provider_user_id=str(data.get("id")),
        email=email.strip().lower(),
        display_name=data.get("name") or data.get("login") or email,
        avatar_url=data.get("avatar_url"),
    )


def get_provider_profile(provider_name: str, token_response: dict):
    """负责 get_provider_profile 的函数职责。"""
    access_token = token_response.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="oauth provider token missing")

    if provider_name == "google":
        return get_google_profile(access_token)
    if provider_name == "github":
        return get_github_profile(access_token)

    raise HTTPException(status_code=404, detail="oauth provider not found")


def ensure_provider_profile(profile: OAuthProfile):
    """负责 ensure_provider_profile 的函数职责。"""
    if not profile.provider_user_id or profile.provider_user_id == "None":
        raise HTTPException(status_code=400, detail="oauth provider user id missing")
    if not profile.email:
        raise HTTPException(status_code=400, detail="oauth provider email missing")


def resolve_or_create_oauth_user(profile: OAuthProfile):
    """负责 resolve_or_create_oauth_user 的函数职责。"""
    ensure_provider_profile(profile)
    existing_oauth = get_oauth_account(profile.provider, profile.provider_user_id)
    if existing_oauth:
        user = get_user_by_id(existing_oauth["user_id"])
        if not user or not user.get("is_active"):
            raise HTTPException(status_code=401, detail="account inactive")
        upsert_oauth_account(
            user["id"],
            profile.provider,
            profile.provider_user_id,
            provider_email=profile.email,
            provider_display_name=profile.display_name,
            provider_avatar=profile.avatar_url,
        )
        return get_user_by_id(user["id"])

    existing_user = get_user_by_email(profile.email)
    if existing_user:
        if not existing_user.get("is_active"):
            raise HTTPException(status_code=401, detail="account inactive")
        linked = get_oauth_account_for_user(existing_user["id"], profile.provider)
        if linked and linked["provider_user_id"] != profile.provider_user_id:
            raise HTTPException(status_code=409, detail="oauth provider already linked")
        upsert_oauth_account(
            existing_user["id"],
            profile.provider,
            profile.provider_user_id,
            provider_email=profile.email,
            provider_display_name=profile.display_name,
            provider_avatar=profile.avatar_url,
        )
        return get_user_by_id(existing_user["id"])

    user = create_user(
        email=profile.email,
        display_name=profile.display_name or profile.email,
        avatar_url=profile.avatar_url,
        auth_provider=profile.provider,
        password_hash=None,
        is_guest=False,
        is_active=True,
    )
    create_default_kb(user_id=user["id"])
    upsert_oauth_account(
        user["id"],
        profile.provider,
        profile.provider_user_id,
        provider_email=profile.email,
        provider_display_name=profile.display_name,
        provider_avatar=profile.avatar_url,
    )
    return get_user_by_id(user["id"])


def link_oauth_profile(user_id: int, profile: OAuthProfile):
    """负责 link_oauth_profile 的函数职责。"""
    ensure_provider_profile(profile)
    existing_oauth = get_oauth_account(profile.provider, profile.provider_user_id)
    if existing_oauth and int(existing_oauth["user_id"]) != int(user_id):
        raise HTTPException(status_code=409, detail="oauth account is already linked")

    existing_user_provider = get_oauth_account_for_user(user_id, profile.provider)
    if (
        existing_user_provider
        and existing_user_provider["provider_user_id"] != profile.provider_user_id
    ):
        raise HTTPException(status_code=409, detail="oauth provider already linked")

    user = get_user_by_id(user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="account inactive")

    if user.get("email") and profile.email and user["email"].lower() != profile.email.lower():
        raise HTTPException(status_code=409, detail="oauth email does not match account")

    return upsert_oauth_account(
        user_id,
        profile.provider,
        profile.provider_user_id,
        provider_email=profile.email,
        provider_display_name=profile.display_name,
        provider_avatar=profile.avatar_url,
    )


def unlink_oauth_provider(user_id: int, provider_name: str):
    """负责 unlink_oauth_provider 的函数职责。"""
    if provider_name not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail="oauth provider not found")

    if not get_oauth_account_for_user(user_id, provider_name):
        raise HTTPException(status_code=404, detail="oauth account not linked")

    if user_login_method_count(user_id) <= 1:
        raise HTTPException(status_code=400, detail="cannot unlink the last login method")

    return delete_oauth_account_for_user(user_id, provider_name)


def complete_oauth_callback(
    provider_name: str,
    code: str,
    state: str,
    request: Request,
    response: Response,
):
    """负责 complete_oauth_callback 的函数职责。"""
    state_record = pop_oauth_state(state, provider_name)
    token_response = exchange_code_for_token(
        provider_name,
        code,
        state_record["code_verifier"],
    )
    profile = get_provider_profile(provider_name, token_response)

    if state_record["mode"] == "link":
        account = link_oauth_profile(int(state_record["user_id"]), profile)
        return {
            "mode": "link",
            "account": account,
            "user": get_user_by_id(int(state_record["user_id"])),
        }

    user = resolve_or_create_oauth_user(profile)
    access_token, expires_in, session_id = create_login_session(user, request, response)
    return {
        "mode": "login",
        "access_token": access_token,
        "expires_in": expires_in,
        "session_id": session_id,
        "user": user,
    }


def oauth_success_redirect(mode: str):
    """负责 oauth_success_redirect 的函数职责。"""
    target = "/account" if mode == "link" else "/chat"
    query = urllib.parse.urlencode({
        "oauth": "success",
        "mode": mode,
    })
    return f"{get_frontend_base_url()}{target}?{query}"


def oauth_error_redirect(message: str):
    """负责 oauth_error_redirect 的函数职责。"""
    query = urllib.parse.urlencode({
        "oauth_error": message,
    })
    return f"{get_frontend_base_url()}/login?{query}"

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
    """统一表示第三方登录平台返回的用户身份。

    Google 和 GitHub 的字段名称不同。后续账号查找、绑定和创建用户只依赖
    这个统一结构，不需要重复判断平台响应格式。
    """
    provider: str
    provider_user_id: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None


def cleanup_oauth_states():
    """清理已经过期的一次性 OAuth state，避免旧授权请求长期留在内存。"""
    now = time.time()
    expired = [
        state
        for state, record in _oauth_states.items()
        if record["expires_at"] < now
    ]
    for state in expired:
        _oauth_states.pop(state, None)


def base64_urlsafe_digest(value: bytes):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def create_pkce_pair():
    """生成 OAuth PKCE 校验值，防止授权码被其他客户端截获后直接使用。"""
    verifier = secrets.token_urlsafe(64)
    challenge = base64_urlsafe_digest(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def get_provider_metadata(provider: str):
    """返回 Google 或 GitHub 的固定 OAuth 端点和授权范围。"""
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
    parsed = urllib.parse.urlparse(url)
    return parsed.hostname in {"127.0.0.1", "localhost"}


def validate_redirect_uri(url: str):
    """限制 OAuth 回调使用 HTTPS；本地开发地址允许使用 HTTP。"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "https":
        return

    if parsed.scheme == "http" and is_localhost_url(url):
        return

    raise HTTPException(status_code=500, detail="oauth redirect URI must use HTTPS")


def get_oauth_provider(provider: str):
    """合并平台固定信息和环境配置，并标出该平台当前是否可用。"""
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
    """生成前端可见的平台状态，同时隐藏 client secret 等敏感配置。"""
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
    """创建登录或绑定账号所需的授权地址。

    state 把本次请求的模式、用户和 PKCE verifier 暂存在服务端。回调时只有
    state 能匹配的请求才会继续，避免回调被伪造或串到另一个用户。
    """
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
    """取出并立即消费一次性 state，重复回调不能再次使用同一授权请求。"""
    cleanup_oauth_states()
    if not state:
        raise HTTPException(status_code=400, detail="oauth state missing")

    record = _oauth_states.pop(state, None)
    if not record or record.get("provider") != provider_name:
        raise HTTPException(status_code=400, detail="oauth state invalid")

    return record


def request_json(url: str, data=None, headers=None, method=None):
    """请求 OAuth 平台并把响应统一转成字典。

    平台不可用和异常响应在这里转换成稳定的网关错误，路由层不会把底层网络
    异常直接返回给客户端。GitHub 可能返回表单格式，因此保留兼容解析。
    """
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
    """用授权码和本次 PKCE verifier 换取平台 access token。"""
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
    """读取 Google 用户资料，并转换成统一的 OAuthProfile。"""
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
    """在 GitHub 邮箱列表中优先选择已验证的主邮箱。"""
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
    """读取 GitHub 用户资料；公开资料没有邮箱时再查询邮箱接口。"""
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
    """根据平台选择资料接口，返回后续账号流程使用的统一身份。"""
    access_token = token_response.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="oauth provider token missing")

    if provider_name == "google":
        return get_google_profile(access_token)
    if provider_name == "github":
        return get_github_profile(access_token)

    raise HTTPException(status_code=404, detail="oauth provider not found")


def ensure_provider_profile(profile: OAuthProfile):
    """确认第三方身份包含稳定用户编号和邮箱，缺失时停止账号绑定。"""
    if not profile.provider_user_id or profile.provider_user_id == "None":
        raise HTTPException(status_code=400, detail="oauth provider user id missing")
    if not profile.email:
        raise HTTPException(status_code=400, detail="oauth provider email missing")


def resolve_or_create_oauth_user(profile: OAuthProfile):
    """把第三方身份解析为 Mini ChatChat 用户。

    先按第三方账号查找，其次按邮箱合并已有用户，最后才创建新用户。这个顺序
    可以避免同一身份生成重复账号，同时拒绝把一个平台账号覆盖到错误用户上。
    """
    # 已绑定的平台账号直接登录，并刷新平台侧可能变化的头像和显示名称。
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

    # 首次使用该平台时，优先复用相同邮箱的本地账号。
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

    # 两种查找都没有命中才创建用户，并同时准备用户自己的 default 知识库。
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
    """把第三方身份绑定到当前用户，并阻止跨用户抢占已有绑定。"""
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
    """解除一个第三方登录方式，但不允许删除用户最后一种登录方式。"""
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
    """完成 OAuth 回调中的校验、换 token、取资料和登录或绑定。

    前面的授权入口保存了 state 和 PKCE verifier。这里消费它们后进入平台接口，
    最后只有登录模式会创建本站 session；绑定模式只更新当前用户的登录方式。
    """
    # 先验证回调确实对应本站发起且尚未消费的授权请求。
    state_record = pop_oauth_state(state, provider_name)
    token_response = exchange_code_for_token(
        provider_name,
        code,
        state_record["code_verifier"],
    )
    profile = get_provider_profile(provider_name, token_response)

    # 绑定模式不创建新登录会话，只把平台身份接到 state 中记录的当前用户。
    if state_record["mode"] == "link":
        account = link_oauth_profile(int(state_record["user_id"]), profile)
        return {
            "mode": "link",
            "account": account,
            "user": get_user_by_id(int(state_record["user_id"])),
        }

    # 登录模式解析或创建用户，然后进入统一 session 创建流程。
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
    target = "/account" if mode == "link" else "/chat"
    query = urllib.parse.urlencode({
        "oauth": "success",
        "mode": mode,
    })
    return f"{get_frontend_base_url()}{target}?{query}"


def oauth_error_redirect(message: str):
    query = urllib.parse.urlencode({
        "oauth_error": message,
    })
    return f"{get_frontend_base_url()}/login?{query}"

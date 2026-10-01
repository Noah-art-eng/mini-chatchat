"""用户认证、OAuth、Session 与偏好设置路由。"""

import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from api.schemas import (
    AuthAccountUpdateRequest,
    AuthEmailPasswordRequest,
    AuthPreferencesUpdateRequest,
)
from auth.dependencies import get_current_user, get_current_user_optional
from auth.models import CurrentUser
from auth.oauth import (
    complete_oauth_callback,
    create_oauth_authorization,
    oauth_error_redirect,
    oauth_success_redirect,
    public_provider_status,
    unlink_oauth_provider,
)
from auth.password import hash_password, verify_password
from auth.security import (
    check_auth_rate_limit,
    clear_auth_failures,
    record_auth_failure,
    verify_allowed_origin,
)
from auth.session import (
    create_login_session,
    get_refresh_token_from_request,
    list_public_user_sessions,
    logout_all_sessions,
    logout_other_sessions,
    logout_refresh_session,
    refresh_login_session,
    revoke_user_session,
)
from db import (
    create_default_kb,
    create_email_user,
    get_user_auth_by_email,
    get_user_by_id,
    get_user_preferences,
    public_user_dict,
    update_user_account,
    upsert_user_preferences,
)


router = APIRouter()

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
MAX_DISPLAY_NAME_LENGTH = 80


def normalize_email(email: str):
    """统一邮箱比较和存储时使用的格式。"""
    return (email or "").strip().lower()


def validate_email_password(email: str, password: str):
    """在注册入口执行原有邮箱和密码最小校验。"""
    normalized_email = normalize_email(email)

    if not EMAIL_PATTERN.match(normalized_email):
        raise HTTPException(status_code=400, detail="invalid email or password")

    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail="invalid email or password")

    return normalized_email


def validate_display_name(display_name: str | None):
    """保持账户资料接口对显示名称的原有边界检查。"""
    value = (display_name or "").strip()

    if not value:
        raise HTTPException(status_code=400, detail="display name is required")

    if len(value) > MAX_DISPLAY_NAME_LENGTH:
        raise HTTPException(status_code=400, detail="display name is too long")

    return value


def build_token_response(user, request: Request, response: Response):
    """建立登录 Session，并返回现有认证接口使用的 token 结构。"""
    token, expires_in, session_id = create_login_session(user, request, response)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "session_id": session_id,
        "user": public_user_dict(user),
    }


def public_current_user(current_user: CurrentUser):
    """将真实用户或访客身份转换为公开响应结构。"""
    if current_user.is_guest:
        return {
            "id": "guest",
            "email": None,
            "display_name": "Guest",
            "avatar_url": None,
            "auth_provider": "guest",
            "is_guest": True,
            "is_active": True,
        }

    return public_user_dict(get_user_by_id(int(current_user.id)))


def current_session_id(current_user: CurrentUser):
    """读取认证依赖写入用户上下文的当前 Session ID。"""
    return (current_user.metadata or {}).get("session_id")


@router.post("/auth/register")
def auth_register(
    payload: AuthEmailPasswordRequest,
    http_request: Request,
    response: Response,
):
    """负责 auth_register 的函数职责。"""
    verify_allowed_origin(http_request)
    email = validate_email_password(payload.email, payload.password)
    check_auth_rate_limit("register", http_request, email)

    if get_user_auth_by_email(email):
        record_auth_failure("register", http_request, email)
        raise HTTPException(status_code=400, detail="invalid email or password")

    user = create_email_user(
        email,
        hash_password(payload.password),
        display_name=(payload.display_name or email).strip() or email,
    )
    create_default_kb(user_id=user["id"])
    clear_auth_failures("register", http_request, email)
    return build_token_response(user, http_request, response)


@router.post("/auth/login")
def auth_login(
    payload: AuthEmailPasswordRequest,
    http_request: Request,
    response: Response,
):
    """负责 auth_login 的函数职责。"""
    verify_allowed_origin(http_request)
    email = normalize_email(payload.email)
    check_auth_rate_limit("login", http_request, email)
    user = get_user_auth_by_email(email)

    if (
        user is None
        or user.get("auth_provider") != "email"
        or not user.get("is_active")
        or not verify_password(payload.password, user.get("password_hash"))
    ):
        record_auth_failure("login", http_request, email)
        raise HTTPException(status_code=401, detail="invalid email or password")

    clear_auth_failures("login", http_request, email)
    return build_token_response(user, http_request, response)


@router.post("/auth/logout")
def auth_logout(request: Request, response: Response):
    """负责 auth_logout 的函数职责。"""
    verify_allowed_origin(request)
    logout_refresh_session(request, response)
    return {"message": "logged out"}


@router.post("/auth/logout-all")
def auth_logout_all(
    request: Request,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_logout_all 的函数职责。"""
    verify_allowed_origin(request)
    revoked = logout_all_sessions(int(current_user.id), response)
    return {"message": "logged out all sessions", "revoked_sessions": revoked}


@router.post("/auth/refresh")
def auth_refresh(request: Request, response: Response):
    """负责 auth_refresh 的函数职责。"""
    verify_allowed_origin(request)
    check_auth_rate_limit("refresh", request, None)
    refresh_token = get_refresh_token_from_request(request)
    try:
        result = refresh_login_session(refresh_token, response)
    except HTTPException:
        record_auth_failure("refresh", request, None)
        raise

    clear_auth_failures("refresh", request, None)
    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
        "expires_in": result["expires_in"],
        "session_id": result["session_id"],
        "user": public_user_dict(result["user"]),
    }


@router.get("/auth/me")
def auth_me(current_user: CurrentUser = Depends(get_current_user_optional)):
    """负责 auth_me 的函数职责。"""
    return {
        "user": public_current_user(current_user),
        "authenticated": not current_user.is_guest,
    }


@router.get("/auth/preferences")
def auth_preferences(current_user: CurrentUser = Depends(get_current_user)):
    """负责 auth_preferences 的函数职责。"""
    return {"preferences": get_user_preferences(int(current_user.id))}


@router.patch("/auth/preferences")
def auth_update_preferences(
    request: AuthPreferencesUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_update_preferences 的函数职责。"""
    current = get_user_preferences(int(current_user.id)) or {}
    preferences = upsert_user_preferences(
        int(current_user.id),
        language=request.language if request.language is not None else current.get("language"),
        developer_mode=(
            request.developer_mode
            if request.developer_mode is not None
            else bool(current.get("developer_mode", False))
        ),
        onboarding_completed=(
            request.onboarding_completed
            if request.onboarding_completed is not None
            else bool(current.get("onboarding_completed", False))
        ),
        theme=request.theme if request.theme is not None else current.get("theme", "light"),
        preferred_model=(
            request.preferred_model
            if request.preferred_model is not None
            else current.get("preferred_model")
        ),
    )
    return {"preferences": preferences}


@router.get("/auth/account")
def auth_account(current_user: CurrentUser = Depends(get_current_user)):
    """负责 auth_account 的函数职责。"""
    return {"user": public_current_user(current_user)}


@router.patch("/auth/account")
def auth_update_account(
    request: AuthAccountUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_update_account 的函数职责。"""
    display_name = validate_display_name(request.display_name)
    user = update_user_account(int(current_user.id), display_name)
    if not user:
        raise HTTPException(status_code=404, detail="account not found")
    return {"user": public_user_dict(user)}


@router.get("/auth/sessions")
def auth_sessions(current_user: CurrentUser = Depends(get_current_user)):
    """负责 auth_sessions 的函数职责。"""
    return {
        "sessions": list_public_user_sessions(
            int(current_user.id),
            current_session_id(current_user),
        )
    }


@router.delete("/auth/sessions/{session_id}")
def auth_revoke_session(
    session_id: str,
    request: Request,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_revoke_session 的函数职责。"""
    verify_allowed_origin(request)
    revoked = revoke_user_session(int(current_user.id), session_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="session not found")
    if session_id == current_session_id(current_user):
        logout_refresh_session(request, response)
    return {
        "message": "session revoked",
        "revoked": True,
        "revoked_current": session_id == current_session_id(current_user),
    }


@router.post("/auth/logout-others")
def auth_logout_others(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_logout_others 的函数职责。"""
    verify_allowed_origin(request)
    session_id = current_session_id(current_user)
    if not session_id:
        raise HTTPException(status_code=401, detail="missing token session")
    revoked = logout_other_sessions(int(current_user.id), session_id)
    return {"message": "logged out other sessions", "revoked_sessions": revoked}


@router.get("/auth/oauth/providers")
def auth_oauth_providers(
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 auth_oauth_providers 的函数职责。"""
    user_id = None if current_user.is_guest else int(current_user.id)
    return {"providers": public_provider_status(user_id)}


@router.get("/auth/oauth/{provider}")
def auth_oauth_start(provider: str):
    """负责 auth_oauth_start 的函数职责。"""
    authorization = create_oauth_authorization(provider, mode="login")
    return RedirectResponse(authorization["authorization_url"], status_code=302)


@router.get("/auth/oauth/{provider}/callback")
def auth_oauth_callback(
    provider: str,
    request: Request,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """负责 auth_oauth_callback 的函数职责。"""
    if error:
        return RedirectResponse(
            oauth_error_redirect("oauth authorization was cancelled"), status_code=302
        )
    if not code:
        return RedirectResponse(
            oauth_error_redirect("oauth authorization code missing"), status_code=302
        )
    try:
        result = complete_oauth_callback(provider, code, state, request, response)
    except HTTPException as exc:
        return RedirectResponse(oauth_error_redirect(str(exc.detail)), status_code=302)

    redirect = RedirectResponse(oauth_success_redirect(result["mode"]), status_code=302)
    for header in response.raw_headers:
        if header[0].lower() == b"set-cookie":
            redirect.raw_headers.append(header)
    return redirect


@router.post("/auth/oauth/link/{provider}")
def auth_oauth_link(
    provider: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_oauth_link 的函数职责。"""
    verify_allowed_origin(request)
    authorization = create_oauth_authorization(
        provider, mode="link", user_id=int(current_user.id)
    )
    return {"authorization_url": authorization["authorization_url"], "provider": provider}


@router.delete("/auth/oauth/link/{provider}")
def auth_oauth_unlink(
    provider: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """负责 auth_oauth_unlink 的函数职责。"""
    verify_allowed_origin(request)
    unlinked = unlink_oauth_provider(int(current_user.id), provider)
    return {
        "message": "oauth account unlinked",
        "provider": provider,
        "unlinked": unlinked,
    }

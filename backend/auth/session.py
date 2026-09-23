import hashlib
import hmac
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, Response

from db import (
    cleanup_expired_auth_sessions,
    create_auth_session,
    get_auth_session,
    get_user_by_id,
    list_auth_sessions_by_user,
    revoke_auth_session,
    revoke_auth_session_for_user,
    revoke_other_auth_sessions,
    revoke_user_auth_sessions,
    update_auth_session_refresh,
)
from .config import (
    get_access_token_expire_minutes,
    get_auth_cookie_domain,
    get_auth_cookie_name,
    get_auth_cookie_path,
    get_auth_cookie_samesite,
    get_auth_cookie_secure,
    get_refresh_token_expire_days,
)
from .jwt import (
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)


def hash_refresh_token(token: str):
    """负责 hash_refresh_token 的函数职责。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_expiry_datetime():
    """负责 refresh_expiry_datetime 的函数职责。"""
    return datetime.now() + timedelta(days=get_refresh_token_expire_days())


def format_db_time(value: datetime):
    """负责 format_db_time 的函数职责。"""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def parse_db_time(value: str):
    """负责 parse_db_time 的函数职责。"""
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def mask_ip_address(ip_address: str | None):
    """负责 mask_ip_address 的函数职责。"""
    if not ip_address:
        return None

    if ":" in ip_address:
        parts = ip_address.split(":")
        return ":".join(parts[:2] + ["****"])

    parts = ip_address.split(".")
    if len(parts) == 4:
        return ".".join(parts[:2] + ["*", "*"])

    return "masked"


def summarize_user_agent(user_agent: str | None):
    """负责 summarize_user_agent 的函数职责。"""
    if not user_agent:
        return "Unknown device"

    lowered = user_agent.lower()
    browser = "Browser"
    if "edg/" in lowered:
        browser = "Edge"
    elif "chrome/" in lowered and "chromium" not in lowered:
        browser = "Chrome"
    elif "firefox/" in lowered:
        browser = "Firefox"
    elif "safari/" in lowered and "chrome/" not in lowered:
        browser = "Safari"
    elif "python-requests" in lowered:
        browser = "Python requests"

    platform = "Unknown platform"
    if "mac os" in lowered or "macintosh" in lowered:
        platform = "macOS"
    elif "windows" in lowered:
        platform = "Windows"
    elif "linux" in lowered:
        platform = "Linux"
    elif "iphone" in lowered or "ipad" in lowered:
        platform = "iOS"
    elif "android" in lowered:
        platform = "Android"

    return f"{browser} on {platform}"


def public_auth_session(session: dict, current_session_id: str | None = None):
    """负责 public_auth_session 的函数职责。"""
    is_active = bool(session.get("is_active")) and not session.get("revoked_at")
    return {
        "session_id": session["session_id"],
        "device": summarize_user_agent(session.get("user_agent")),
        "created_at": session.get("created_at"),
        "last_used_at": session.get("last_used_at"),
        "expires_at": session.get("expires_at"),
        "revoked_at": session.get("revoked_at"),
        "is_active": is_active,
        "is_current": session["session_id"] == current_session_id,
        "ip_address": mask_ip_address(session.get("ip_address")),
    }


def get_request_ip(request: Request):
    """负责 get_request_ip 的函数职责。"""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    return request.client.host if request.client else None


def build_access_token(user: dict, session_id: str):
    """负责 build_access_token 的函数职责。"""
    expires_in = get_access_token_expire_minutes() * 60
    token = create_access_token(
        subject=str(user["id"]),
        claims={
            "email": user.get("email"),
            "uid": user["id"],
            "session_id": session_id,
        },
    )
    return token, expires_in


def build_refresh_token(user: dict, session_id: str):
    """负责 build_refresh_token 的函数职责。"""
    expires_at = refresh_expiry_datetime()
    token = create_refresh_token(
        subject=str(user["id"]),
        session_id=session_id,
        claims={
            "uid": user["id"],
            "email": user.get("email"),
        },
    )
    return token, expires_at


def set_refresh_cookie(response: Response, refresh_token: str):
    """负责 set_refresh_cookie 的函数职责。"""
    response.set_cookie(
        get_auth_cookie_name(),
        refresh_token,
        httponly=True,
        secure=get_auth_cookie_secure(),
        samesite=get_auth_cookie_samesite(),
        domain=get_auth_cookie_domain(),
        path=get_auth_cookie_path(),
        max_age=get_refresh_token_expire_days() * 24 * 60 * 60,
    )


def clear_refresh_cookie(response: Response):
    """负责 clear_refresh_cookie 的函数职责。"""
    response.delete_cookie(
        get_auth_cookie_name(),
        domain=get_auth_cookie_domain(),
        path=get_auth_cookie_path(),
        samesite=get_auth_cookie_samesite(),
        secure=get_auth_cookie_secure(),
        httponly=True,
    )


def create_login_session(user: dict, request: Request, response: Response):
    """负责 create_login_session 的函数职责。"""
    session_id = str(uuid.uuid4())
    refresh_token, expires_at = build_refresh_token(user, session_id)
    create_auth_session(
        session_id,
        user["id"],
        hash_refresh_token(refresh_token),
        format_db_time(expires_at),
        user_agent=request.headers.get("user-agent"),
        ip_address=get_request_ip(request),
    )
    set_refresh_cookie(response, refresh_token)
    access_token, expires_in = build_access_token(user, session_id)
    return access_token, expires_in, session_id


def get_refresh_token_from_request(request: Request):
    """负责 get_refresh_token_from_request 的函数职责。"""
    token = request.cookies.get(get_auth_cookie_name())
    if not token:
        raise HTTPException(status_code=401, detail="refresh token missing")
    return token


def validate_refresh_session(refresh_token: str):
    """负责 validate_refresh_session 的函数职责。"""
    try:
        payload = decode_refresh_token(refresh_token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    session_id = payload.get("session_id")
    user_id = payload.get("uid") or payload.get("sub")

    if not session_id or not user_id:
        raise HTTPException(status_code=401, detail="invalid refresh token")

    session = get_auth_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="session not found")

    if (
        not session.get("is_active")
        or session.get("revoked_at")
        or parse_db_time(session["expires_at"]) < datetime.now()
    ):
        raise HTTPException(status_code=401, detail="session expired or revoked")

    expected_hash = session.get("refresh_token_hash") or ""
    actual_hash = hash_refresh_token(refresh_token)
    if not hmac.compare_digest(expected_hash, actual_hash):
        revoke_auth_session(session_id)
        raise HTTPException(status_code=401, detail="refresh token reuse detected")

    user = get_user_by_id(int(user_id))
    if not user or not user.get("is_active") or int(user["id"]) != int(session["user_id"]):
        revoke_auth_session(session_id)
        raise HTTPException(status_code=401, detail="user not found or inactive")

    return payload, session, user


def refresh_login_session(refresh_token: str, response: Response):
    """负责 refresh_login_session 的函数职责。"""
    payload, session, user = validate_refresh_session(refresh_token)
    session_id = session["session_id"]
    new_refresh_token, expires_at = build_refresh_token(user, session_id)

    updated = update_auth_session_refresh(
        session_id,
        hash_refresh_token(new_refresh_token),
        format_db_time(expires_at),
    )

    if not updated:
        raise HTTPException(status_code=401, detail="session expired or revoked")

    set_refresh_cookie(response, new_refresh_token)
    access_token, expires_in = build_access_token(user, session_id)

    return {
        "access_token": access_token,
        "expires_in": expires_in,
        "session_id": session_id,
        "user": user,
        "old_jti": payload.get("jti"),
    }


def logout_refresh_session(request: Request, response: Response):
    """负责 logout_refresh_session 的函数职责。"""
    token = request.cookies.get(get_auth_cookie_name())

    if token:
        try:
            payload = decode_refresh_token(token)
            session_id = payload.get("session_id")
            if session_id:
                revoke_auth_session(session_id)
        except JWTError:
            pass

    clear_refresh_cookie(response)


def logout_all_sessions(user_id: int, response: Response):
    """负责 logout_all_sessions 的函数职责。"""
    revoked = revoke_user_auth_sessions(user_id)
    clear_refresh_cookie(response)
    return revoked


def list_public_user_sessions(user_id: int, current_session_id: str | None):
    """负责 list_public_user_sessions 的函数职责。"""
    cleanup_expired_auth_sessions()
    return [
        public_auth_session(session, current_session_id=current_session_id)
        for session in list_auth_sessions_by_user(user_id)
    ]


def revoke_user_session(user_id: int, session_id: str):
    """负责 revoke_user_session 的函数职责。"""
    return revoke_auth_session_for_user(user_id, session_id)


def logout_other_sessions(user_id: int, current_session_id: str):
    """负责 logout_other_sessions 的函数职责。"""
    return revoke_other_auth_sessions(user_id, current_session_id)

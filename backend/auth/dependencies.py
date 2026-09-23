from datetime import datetime

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import get_auth_session, get_user_by_id
from .jwt import JWTError, decode_access_token
from .models import CurrentUser, guest_user, user_from_record
from .permissions import Permission, has_permission

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """负责 get_current_user_optional 的函数职责。"""
    if credentials is None:
        return guest_user()

    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")
        session_id = payload.get("session_id")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if not subject:
        raise HTTPException(status_code=401, detail="missing token subject")

    if not session_id:
        raise HTTPException(status_code=401, detail="missing token session")

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="invalid token subject") from exc

    user = user_from_record(get_user_by_id(user_id))

    if user.is_guest or not user.is_active:
        raise HTTPException(status_code=401, detail="user not found or inactive")

    session = get_auth_session(session_id)
    if (
        not session
        or int(session["user_id"]) != user_id
        or not session.get("is_active")
        or session.get("revoked_at")
        or datetime.strptime(session["expires_at"], "%Y-%m-%d %H:%M:%S") < datetime.now()
    ):
        raise HTTPException(status_code=401, detail="session expired or revoked")

    return user_from_record({
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "auth_provider": user.auth_provider,
        "is_guest": user.is_guest,
        "is_active": user.is_active,
        "metadata": {
            "session_id": session_id,
        },
    })


def get_current_user(
    current_user: CurrentUser = Depends(get_current_user_optional),
) -> CurrentUser:
    """负责 get_current_user 的函数职责。"""
    if current_user.is_guest:
        raise HTTPException(status_code=401, detail="authentication required")

    return current_user


def get_request_user_id(current_user: CurrentUser) -> int | None:
    """负责 get_request_user_id 的函数职责。"""
    if current_user.is_guest:
        return None

    return int(current_user.id)


def require_permission(user: CurrentUser, permission: Permission):
    """负责 require_permission 的函数职责。"""
    if not has_permission(user, permission):
        raise HTTPException(status_code=403, detail="permission denied")

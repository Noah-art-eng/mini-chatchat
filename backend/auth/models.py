from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AuthProvider(str, Enum):
    """当前支持的本地、第三方和访客身份来源。"""
    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"
    GUEST = "guest"


@dataclass(frozen=True)
class GuestUser:
    """未登录请求使用的固定身份，只获得访客权限和 demo 数据范围。"""
    id: str = "guest"
    email: str | None = None
    display_name: str = "Guest"
    avatar_url: str | None = None
    auth_provider: AuthProvider = AuthProvider.GUEST
    is_guest: bool = True
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuthenticatedUser:
    """从数据库用户记录转换出的请求身份，后续用于权限和用户隔离。"""
    id: int
    email: str | None
    display_name: str | None
    avatar_url: str | None
    auth_provider: str
    is_guest: bool
    is_active: bool
    metadata: dict[str, Any] = field(default_factory=dict)


CurrentUser = GuestUser | AuthenticatedUser


def guest_user():
    return GuestUser()


def user_from_record(record: dict[str, Any] | None) -> CurrentUser:
    if not record:
        return guest_user()

    return AuthenticatedUser(
        id=int(record["id"]),
        email=record.get("email"),
        display_name=record.get("display_name"),
        avatar_url=record.get("avatar_url"),
        auth_provider=record.get("auth_provider") or AuthProvider.EMAIL.value,
        is_guest=bool(record.get("is_guest")),
        is_active=bool(record.get("is_active")),
        metadata=dict(record.get("metadata") or {}),
    )

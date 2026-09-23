from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AuthProvider(str, Enum):
    """负责 AuthProvider 的类职责。"""
    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"
    GUEST = "guest"


@dataclass(frozen=True)
class GuestUser:
    """负责 GuestUser 的类职责。"""
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
    """负责 AuthenticatedUser 的类职责。"""
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
    """负责 guest_user 的函数职责。"""
    return GuestUser()


def user_from_record(record: dict[str, Any] | None) -> CurrentUser:
    """负责 user_from_record 的函数职责。"""
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

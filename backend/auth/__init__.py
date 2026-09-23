from .models import AuthProvider, AuthenticatedUser, CurrentUser, GuestUser
from .permissions import Permission, get_permissions_for_user, has_permission

__all__ = [
    "AuthProvider",
    "AuthenticatedUser",
    "CurrentUser",
    "GuestUser",
    "Permission",
    "get_current_user",
    "get_current_user_optional",
    "get_permissions_for_user",
    "has_permission",
]


def __getattr__(name):
    """负责 __getattr__ 的函数职责。"""
    if name in {"get_current_user", "get_current_user_optional"}:
        from .dependencies import get_current_user, get_current_user_optional

        return {
            "get_current_user": get_current_user,
            "get_current_user_optional": get_current_user_optional,
        }[name]

    raise AttributeError(name)

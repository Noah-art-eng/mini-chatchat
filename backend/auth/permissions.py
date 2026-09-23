from enum import Enum

from .models import CurrentUser


class Permission(str, Enum):
    """负责 Permission 的类职责。"""
    CAN_USE_CHAT = "can_use_chat"
    CAN_USE_SEARCH = "can_use_search"
    CAN_USE_TEMP_FILE = "can_use_temp_file"
    CAN_MANAGE_KB = "can_manage_kb"
    CAN_USE_AGENT = "can_use_agent"
    CAN_USE_MCP = "can_use_mcp"
    CAN_USE_FILESYSTEM = "can_use_filesystem"
    CAN_USE_SQLITE = "can_use_sqlite"
    CAN_ENABLE_DEVELOPER_MODE = "can_enable_developer_mode"


GUEST_PERMISSIONS = {
    Permission.CAN_USE_CHAT,
    Permission.CAN_USE_SEARCH,
    Permission.CAN_USE_TEMP_FILE,
}

AUTHENTICATED_USER_PERMISSIONS = set(Permission)


def get_permissions_for_user(user: CurrentUser) -> set[Permission]:
    """负责 get_permissions_for_user 的函数职责。"""
    if user.is_guest:
        return set(GUEST_PERMISSIONS)

    if not user.is_active:
        return set()

    return set(AUTHENTICATED_USER_PERMISSIONS)


def has_permission(user: CurrentUser, permission: Permission) -> bool:
    """负责 has_permission 的函数职责。"""
    return permission in get_permissions_for_user(user)

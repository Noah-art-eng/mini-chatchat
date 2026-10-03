from enum import Enum

from .models import CurrentUser


class Permission(str, Enum):
    """路由和工具可以要求的能力；访客只获得其中的安全子集。"""
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
    """根据访客、普通用户和管理员身份生成后端权限集合。"""
    if user.is_guest:
        return set(GUEST_PERMISSIONS)

    if not user.is_active:
        return set()

    return set(AUTHENTICATED_USER_PERMISSIONS)


def has_permission(user: CurrentUser, permission: Permission) -> bool:
    """检查用户是否拥有路由要求的权限。"""
    return permission in get_permissions_for_user(user)

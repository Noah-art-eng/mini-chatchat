import type { AuthSession, Permission } from "./types";

export const guestPermissions = new Set<Permission>([
  "can_use_chat",
  "can_use_search",
  "can_use_temp_file"
]);

export const authenticatedPermissions = new Set<Permission>([
  "can_use_chat",
  "can_use_search",
  "can_use_temp_file",
  "can_manage_kb",
  "can_use_agent",
  "can_use_mcp",
  "can_use_filesystem",
  "can_use_sqlite",
  "can_enable_developer_mode"
]);

export function getPermissionsForSession(session: AuthSession) {
  if (session.isGuest || !session.isActive) {
    return guestPermissions;
  }

  return authenticatedPermissions;
}

export function can(session: AuthSession, permission: Permission) {
  return getPermissionsForSession(session).has(permission);
}

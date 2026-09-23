export type AuthStatus = "guest" | "authenticated";

export type AuthProviderName = "guest" | "email" | "google" | "github";

export type Permission =
  | "can_use_chat"
  | "can_use_search"
  | "can_use_temp_file"
  | "can_manage_kb"
  | "can_use_agent"
  | "can_use_mcp"
  | "can_use_filesystem"
  | "can_use_sqlite"
  | "can_enable_developer_mode";

export type GuestSession = {
  apiUserScope: "demo";
  authProvider: "guest";
  avatarUrl: null;
  displayName: "Guest";
  email: null;
  createdAt: null;
  id: "guest";
  isActive: true;
  isGuest: true;
};

export type AuthenticatedSession = {
  apiUserScope: string;
  authProvider: Exclude<AuthProviderName, "guest">;
  avatarUrl: string | null;
  displayName: string;
  email: string | null;
  createdAt: string | null;
  id: string;
  isActive: boolean;
  isGuest: false;
};

export type AuthSession = GuestSession | AuthenticatedSession;

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = {
  displayName?: string;
  email: string;
  password: string;
};

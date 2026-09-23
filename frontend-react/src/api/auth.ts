import { authFetch, requestJson } from "./client";

export type AuthUser = {
  id: number | "guest";
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
  auth_provider: string;
  created_at?: string | null;
  updated_at?: string | null;
  is_guest: boolean;
  is_active: boolean;
};

export type AuthPreferences = {
  user_id: number;
  language: string | null;
  developer_mode: boolean;
  onboarding_completed: boolean;
  theme: string;
  preferred_model: string | null;
  created_at: string;
  updated_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  session_id?: string;
  user: AuthUser;
};

export type AuthMeResponse = {
  authenticated: boolean;
  user: AuthUser;
};

export type AccountSession = {
  session_id: string;
  device: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
  revoked_at: string | null;
  is_active: boolean;
  is_current: boolean;
  ip_address: string | null;
};

export type OAuthProviderStatus = {
  provider: "github" | "google";
  label: string;
  configured: boolean;
  linked: boolean;
  account: {
    provider: string;
    provider_email: string | null;
    provider_display_name: string | null;
    provider_avatar: string | null;
    created_at: string | null;
    updated_at: string | null;
  } | null;
};

/** 用途：负责 registerWithEmail 的界面或数据处理职责。 */
export function registerWithEmail(payload: {
  display_name?: string;
  email: string;
  password: string;
}) {
  return requestJson<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

/** 用途：负责 loginWithEmail 的界面或数据处理职责。 */
export function loginWithEmail(payload: { email: string; password: string }) {
  return requestJson<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

/** 用途：负责 getAuthMe 的界面或数据处理职责。 */
export function getAuthMe() {
  return requestJson<AuthMeResponse>("/auth/me");
}

/** 用途：负责 refreshAuthSession 的界面或数据处理职责。 */
export function refreshAuthSession() {
  return requestJson<AuthResponse>("/auth/refresh", {
    method: "POST"
  });
}

/** 用途：负责 logoutRequest 的界面或数据处理职责。 */
export async function logoutRequest() {
  const response = await authFetch("/auth/logout", {
    method: "POST"
  });

  if (!response.ok) {
    throw new Error(`Logout failed: ${response.status}`);
  }

  return response.json() as Promise<{ message: string }>;
}

/** 用途：负责 getAuthPreferences 的界面或数据处理职责。 */
export function getAuthPreferences() {
  return requestJson<{ preferences: AuthPreferences }>("/auth/preferences");
}

/** 用途：负责 updateAuthPreferences 的界面或数据处理职责。 */
export function updateAuthPreferences(payload: Partial<AuthPreferences>) {
  return requestJson<{ preferences: AuthPreferences }>("/auth/preferences", {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

/** 用途：负责 getAuthAccount 的界面或数据处理职责。 */
export function getAuthAccount() {
  return requestJson<{ user: AuthUser }>("/auth/account");
}

/** 用途：负责 updateAuthAccount 的界面或数据处理职责。 */
export function updateAuthAccount(payload: { display_name: string }) {
  return requestJson<{ user: AuthUser }>("/auth/account", {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

/** 用途：负责 listAuthSessions 的界面或数据处理职责。 */
export function listAuthSessions() {
  return requestJson<{ sessions: AccountSession[] }>("/auth/sessions");
}

/** 用途：负责 revokeAuthSession 的界面或数据处理职责。 */
export function revokeAuthSession(sessionId: string) {
  return requestJson<{
    message: string;
    revoked: boolean;
    revoked_current: boolean;
  }>(`/auth/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE"
  });
}

/** 用途：负责 logoutOtherSessions 的界面或数据处理职责。 */
export function logoutOtherSessions() {
  return requestJson<{
    message: string;
    revoked_sessions: number;
  }>("/auth/logout-others", {
    method: "POST"
  });
}

/** 用途：负责 logoutAllSessions 的界面或数据处理职责。 */
export function logoutAllSessions() {
  return requestJson<{
    message: string;
    revoked_sessions: number;
  }>("/auth/logout-all", {
    method: "POST"
  });
}

/** 用途：负责 listOAuthProviders 的界面或数据处理职责。 */
export function listOAuthProviders() {
  return requestJson<{ providers: OAuthProviderStatus[] }>("/auth/oauth/providers");
}

/** 用途：负责 startOAuthLink 的界面或数据处理职责。 */
export function startOAuthLink(provider: string) {
  return requestJson<{
    authorization_url: string;
    provider: string;
  }>(`/auth/oauth/link/${encodeURIComponent(provider)}`, {
    method: "POST"
  });
}

/** 用途：负责 unlinkOAuthProvider 的界面或数据处理职责。 */
export function unlinkOAuthProvider(provider: string) {
  return requestJson<{
    message: string;
    provider: string;
    unlinked: boolean;
  }>(`/auth/oauth/link/${encodeURIComponent(provider)}`, {
    method: "DELETE"
  });
}

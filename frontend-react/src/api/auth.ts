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

export function loginWithEmail(payload: { email: string; password: string }) {
  return requestJson<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getAuthMe() {
  return requestJson<AuthMeResponse>("/auth/me");
}

export function refreshAuthSession() {
  return requestJson<AuthResponse>("/auth/refresh", {
    method: "POST"
  });
}

export async function logoutRequest() {
  const response = await authFetch("/auth/logout", {
    method: "POST"
  });

  if (!response.ok) {
    throw new Error(`Logout failed: ${response.status}`);
  }

  return response.json() as Promise<{ message: string }>;
}

export function getAuthPreferences() {
  return requestJson<{ preferences: AuthPreferences }>("/auth/preferences");
}

export function updateAuthPreferences(payload: Partial<AuthPreferences>) {
  return requestJson<{ preferences: AuthPreferences }>("/auth/preferences", {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function getAuthAccount() {
  return requestJson<{ user: AuthUser }>("/auth/account");
}

export function updateAuthAccount(payload: { display_name: string }) {
  return requestJson<{ user: AuthUser }>("/auth/account", {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function listAuthSessions() {
  return requestJson<{ sessions: AccountSession[] }>("/auth/sessions");
}

export function revokeAuthSession(sessionId: string) {
  return requestJson<{
    message: string;
    revoked: boolean;
    revoked_current: boolean;
  }>(`/auth/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE"
  });
}

export function logoutOtherSessions() {
  return requestJson<{
    message: string;
    revoked_sessions: number;
  }>("/auth/logout-others", {
    method: "POST"
  });
}

export function logoutAllSessions() {
  return requestJson<{
    message: string;
    revoked_sessions: number;
  }>("/auth/logout-all", {
    method: "POST"
  });
}

export function listOAuthProviders() {
  return requestJson<{ providers: OAuthProviderStatus[] }>("/auth/oauth/providers");
}

export function startOAuthLink(provider: string) {
  return requestJson<{
    authorization_url: string;
    provider: string;
  }>(`/auth/oauth/link/${encodeURIComponent(provider)}`, {
    method: "POST"
  });
}

export function unlinkOAuthProvider(provider: string) {
  return requestJson<{
    message: string;
    provider: string;
    unlinked: boolean;
  }>(`/auth/oauth/link/${encodeURIComponent(provider)}`, {
    method: "DELETE"
  });
}

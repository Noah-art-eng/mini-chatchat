import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";
import {
  getAuthMe,
  getAuthPreferences,
  loginWithEmail,
  logoutRequest,
  refreshAuthSession,
  registerWithEmail,
  updateAuthAccount,
  updateAuthPreferences,
  type AuthPreferences,
  type AuthUser
} from "../api/auth";
import {
  clearAuthSession,
  clearLegacyStoredAccessToken,
  hasLegacyStoredAccessToken,
  hasStoredAuthSessionHint,
  onAuthExpired,
  setStoredAuthSessionHint,
  setStoredAccessToken
} from "../api/client";
import { can, getPermissionsForSession } from "./permissions";
import type {
  AuthProviderName,
  AuthSession,
  AuthStatus,
  LoginPayload,
  Permission,
  RegisterPayload
} from "./types";

const guestSession = {
  apiUserScope: "demo",
  authProvider: "guest",
  avatarUrl: null,
  createdAt: null,
  displayName: "Guest",
  email: null,
  id: "guest",
  isActive: true,
  isGuest: true
} as const satisfies AuthSession;

/** 把后端用户记录转换成前端统一使用的会话身份。 */
function sessionFromUser(user: AuthUser): AuthSession {
  if (user.is_guest) return guestSession;

  return {
    apiUserScope: `user:${user.id}`,
    authProvider: user.auth_provider as Exclude<AuthProviderName, "guest">,
    avatarUrl: user.avatar_url,
    createdAt: user.created_at || null,
    displayName: user.display_name || user.email || "User",
    email: user.email,
    id: String(user.id),
    isActive: user.is_active,
    isGuest: false
  };
}

type AuthContextValue = {
  error: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  permissions: Set<Permission>;
  preferences: AuthPreferences | null;
  session: AuthSession;
  status: AuthStatus;
  user: AuthSession;
  can: (permission: Permission) => boolean;
  clearError: () => void;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  resetToGuest: () => void;
  setSession: (session: AuthSession) => void;
  updateAccount: (payload: { displayName: string }) => Promise<AuthSession>;
  updatePreferences: (payload: Partial<AuthPreferences>) => Promise<AuthPreferences | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * 维护浏览器中的登录身份、偏好和权限。
 * 启动时用 refresh cookie 恢复会话；API 层通知令牌失效时统一退回访客状态。
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<AuthSession>(guestSession);
  const [preferences, setPreferences] = useState<AuthPreferences | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const resetToGuest = useCallback(() => {
    clearAuthSession();
    setSessionState(guestSession);
    setPreferences(null);
  }, []);

  const refreshSession = useCallback(async () => {
    // access token 只保存在内存；刷新页面后用 HttpOnly cookie 恢复，不把新令牌写回 localStorage。
    const hasLegacyToken = hasLegacyStoredAccessToken();
    const hasSessionHint = hasStoredAuthSessionHint();

    if (hasLegacyToken) {
      clearLegacyStoredAccessToken();
    }

    if (!hasLegacyToken && !hasSessionHint) {
      setSessionState(guestSession);
      setPreferences(null);
      setIsLoading(false);
      return;
    }

    try {
      const refreshed = await refreshAuthSession();
      setStoredAccessToken(refreshed.access_token);
      setStoredAuthSessionHint(true);
      const me = await getAuthMe();
      const nextSession = sessionFromUser(me.user);
      setSessionState(nextSession);

      if (!nextSession.isGuest) {
        const preferenceResponse = await getAuthPreferences();
        setPreferences(preferenceResponse.preferences);
      } else {
        setPreferences(null);
      }
    } catch {
      clearAuthSession();
      setSessionState(guestSession);
      setPreferences(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshSession().catch(() => {
      resetToGuest();
      setIsLoading(false);
    });

    return onAuthExpired(() => {
      resetToGuest();
    });
  }, [refreshSession, resetToGuest]);

  const setSession = useCallback((nextSession: AuthSession) => {
    setSessionState(nextSession);
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    setError(null);
    const response = await loginWithEmail(payload);
    setStoredAccessToken(response.access_token);
    setStoredAuthSessionHint(true);
    setSessionState(sessionFromUser(response.user));
    const preferenceResponse = await getAuthPreferences();
    setPreferences(preferenceResponse.preferences);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    setError(null);
    const response = await registerWithEmail({
      display_name: payload.displayName,
      email: payload.email,
      password: payload.password
    });
    setStoredAccessToken(response.access_token);
    setStoredAuthSessionHint(true);
    setSessionState(sessionFromUser(response.user));
    const preferenceResponse = await getAuthPreferences();
    setPreferences(preferenceResponse.preferences);
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      // Stateless JWT logout is completed by local token removal.
    } finally {
      resetToGuest();
    }
  }, [resetToGuest]);

  const updatePreferences = useCallback(
    async (payload: Partial<AuthPreferences>) => {
      if (session.isGuest) return null;

      const response = await updateAuthPreferences(payload);
      setPreferences(response.preferences);
      return response.preferences;
    },
    [session.isGuest]
  );

  const updateAccount = useCallback(async (payload: { displayName: string }) => {
    const response = await updateAuthAccount({
      display_name: payload.displayName
    });
    const nextSession = sessionFromUser(response.user);
    setSessionState(nextSession);
    return nextSession;
  }, []);

  const permissions = useMemo(() => getPermissionsForSession(session), [session]);
  const value = useMemo<AuthContextValue>(
    () => ({
      error,
      isAuthenticated: !session.isGuest,
      isLoading,
      permissions,
      preferences,
      session,
      status: session.isGuest ? "guest" : "authenticated",
      user: session,
      can: (permission: Permission) => can(session, permission),
      clearError: () => setError(null),
      login,
      logout,
      refreshSession,
      register,
      resetToGuest,
      setSession,
      updateAccount,
      updatePreferences
    }),
    [
      error,
      isLoading,
      login,
      logout,
      permissions,
      preferences,
      refreshSession,
      register,
      resetToGuest,
      session,
      setSession,
      updateAccount,
      updatePreferences
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** 取得 AuthProvider 维护的当前身份、权限和会话操作。 */
export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }

  return context;
}

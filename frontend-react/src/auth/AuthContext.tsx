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

/** 用途：负责 sessionFromUser 的界面或数据处理职责。 */
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

/** 用途：负责 AuthProvider 的界面或数据处理职责。 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<AuthSession>(guestSession);
  const [preferences, setPreferences] = useState<AuthPreferences | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const resetToGuest = useCallback(() => {
    /** 用途：负责 clearAuthSession 的界面或数据处理职责。 */
    clearAuthSession();
    /** 用途：负责 setSessionState 的界面或数据处理职责。 */
    setSessionState(guestSession);
    /** 用途：负责 setPreferences 的界面或数据处理职责。 */
    setPreferences(null);
  }, []);

  const refreshSession = useCallback(async () => {
    const hasLegacyToken = hasLegacyStoredAccessToken();
    const hasSessionHint = hasStoredAuthSessionHint();

    if (hasLegacyToken) {
      /** 用途：负责 clearLegacyStoredAccessToken 的界面或数据处理职责。 */
      clearLegacyStoredAccessToken();
    }

    if (!hasLegacyToken && !hasSessionHint) {
      /** 用途：负责 setSessionState 的界面或数据处理职责。 */
      setSessionState(guestSession);
      /** 用途：负责 setPreferences 的界面或数据处理职责。 */
      setPreferences(null);
      /** 用途：负责 setIsLoading 的界面或数据处理职责。 */
      setIsLoading(false);
      return;
    }

    try {
      const refreshed = await refreshAuthSession();
      /** 用途：负责 setStoredAccessToken 的界面或数据处理职责。 */
      setStoredAccessToken(refreshed.access_token);
      /** 用途：负责 setStoredAuthSessionHint 的界面或数据处理职责。 */
      setStoredAuthSessionHint(true);
      const me = await getAuthMe();
      const nextSession = sessionFromUser(me.user);
      /** 用途：负责 setSessionState 的界面或数据处理职责。 */
      setSessionState(nextSession);

      if (!nextSession.isGuest) {
        const preferenceResponse = await getAuthPreferences();
        /** 用途：负责 setPreferences 的界面或数据处理职责。 */
        setPreferences(preferenceResponse.preferences);
      } else {
        /** 用途：负责 setPreferences 的界面或数据处理职责。 */
        setPreferences(null);
      }
    } catch {
      /** 用途：负责 clearAuthSession 的界面或数据处理职责。 */
      clearAuthSession();
      /** 用途：负责 setSessionState 的界面或数据处理职责。 */
      setSessionState(guestSession);
      /** 用途：负责 setPreferences 的界面或数据处理职责。 */
      setPreferences(null);
    } finally {
      /** 用途：负责 setIsLoading 的界面或数据处理职责。 */
      setIsLoading(false);
    }
  }, []);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    /** 用途：负责 refreshSession 的界面或数据处理职责。 */
    refreshSession().catch(() => {
      /** 用途：负责 resetToGuest 的界面或数据处理职责。 */
      resetToGuest();
      /** 用途：负责 setIsLoading 的界面或数据处理职责。 */
      setIsLoading(false);
    });

    return onAuthExpired(() => {
      /** 用途：负责 resetToGuest 的界面或数据处理职责。 */
      resetToGuest();
    });
  }, [refreshSession, resetToGuest]);

  const setSession = useCallback((nextSession: AuthSession) => {
    /** 用途：负责 setSessionState 的界面或数据处理职责。 */
    setSessionState(nextSession);
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);
    const response = await loginWithEmail(payload);
    /** 用途：负责 setStoredAccessToken 的界面或数据处理职责。 */
    setStoredAccessToken(response.access_token);
    /** 用途：负责 setStoredAuthSessionHint 的界面或数据处理职责。 */
    setStoredAuthSessionHint(true);
    /** 用途：负责 setSessionState 的界面或数据处理职责。 */
    setSessionState(sessionFromUser(response.user));
    const preferenceResponse = await getAuthPreferences();
    /** 用途：负责 setPreferences 的界面或数据处理职责。 */
    setPreferences(preferenceResponse.preferences);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);
    const response = await registerWithEmail({
      display_name: payload.displayName,
      email: payload.email,
      password: payload.password
    });
    /** 用途：负责 setStoredAccessToken 的界面或数据处理职责。 */
    setStoredAccessToken(response.access_token);
    /** 用途：负责 setStoredAuthSessionHint 的界面或数据处理职责。 */
    setStoredAuthSessionHint(true);
    /** 用途：负责 setSessionState 的界面或数据处理职责。 */
    setSessionState(sessionFromUser(response.user));
    const preferenceResponse = await getAuthPreferences();
    /** 用途：负责 setPreferences 的界面或数据处理职责。 */
    setPreferences(preferenceResponse.preferences);
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      // Stateless JWT logout is completed by local token removal.
    } finally {
      /** 用途：负责 resetToGuest 的界面或数据处理职责。 */
      resetToGuest();
    }
  }, [resetToGuest]);

  const updatePreferences = useCallback(
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (payload: Partial<AuthPreferences>) => {
      if (session.isGuest) return null;

      const response = await updateAuthPreferences(payload);
      /** 用途：负责 setPreferences 的界面或数据处理职责。 */
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
    /** 用途：负责 setSessionState 的界面或数据处理职责。 */
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

/** 用途：负责 useAuth 的界面或数据处理职责。 */
export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }

  return context;
}

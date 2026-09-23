/** 用途：负责 getDefaultApiBase 的界面或数据处理职责。 */
function getDefaultApiBase() {
  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000";
  }

  const viteDevPorts = new Set(["5173", "5174", "5175"]);
  return viteDevPorts.has(window.location.port)
    ? "http://127.0.0.1:8000"
    : "/api";
}

export const API_BASE = import.meta.env.VITE_API_BASE_URL || getDefaultApiBase();

const TOKEN_KEY = "mini-chatchat:access-token";
const SESSION_HINT_KEY = "mini-chatchat:has-auth-session";
const AUTH_EXPIRED_EVENT = "mini-chatchat:auth-expired";
let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

/** 用途：负责 getStoredAccessToken 的界面或数据处理职责。 */
export function getStoredAccessToken() {
  return accessToken;
}

/** 用途：负责 setStoredAccessToken 的界面或数据处理职责。 */
export function setStoredAccessToken(token: string | null) {
  accessToken = token;
}

/** 用途：负责 clearLegacyStoredAccessToken 的界面或数据处理职责。 */
export function clearLegacyStoredAccessToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
}

/** 用途：负责 hasStoredAuthSessionHint 的界面或数据处理职责。 */
export function hasStoredAuthSessionHint() {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(SESSION_HINT_KEY) === "true";
}

/** 用途：负责 setStoredAuthSessionHint 的界面或数据处理职责。 */
export function setStoredAuthSessionHint(enabled: boolean) {
  if (typeof window === "undefined") return;

  if (enabled) {
    localStorage.setItem(SESSION_HINT_KEY, "true");
  } else {
    localStorage.removeItem(SESSION_HINT_KEY);
  }
}

/** 用途：负责 hasLegacyStoredAccessToken 的界面或数据处理职责。 */
export function hasLegacyStoredAccessToken() {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(TOKEN_KEY) !== null;
}

/** 用途：负责 clearAuthSession 的界面或数据处理职责。 */
export function clearAuthSession() {
  accessToken = null;
  /** 用途：负责 clearLegacyStoredAccessToken 的界面或数据处理职责。 */
  clearLegacyStoredAccessToken();
  /** 用途：负责 setStoredAuthSessionHint 的界面或数据处理职责。 */
  setStoredAuthSessionHint(false);
}

/** 用途：负责 refreshAccessToken 的界面或数据处理职责。 */
async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/auth/refresh`, {
      credentials: "include",
      method: "POST"
    })
      .then(async response => {
        if (!response.ok) return null;
        const data = (await response.json()) as { access_token?: string };
        accessToken = data.access_token || null;
        /** 用途：负责 setStoredAuthSessionHint 的界面或数据处理职责。 */
        setStoredAuthSessionHint(Boolean(accessToken));
        return accessToken;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

/** 用途：负责 notifyAuthExpired 的界面或数据处理职责。 */
export function notifyAuthExpired() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

/** 用途：负责 onAuthExpired 的界面或数据处理职责。 */
export function onAuthExpired(listener: () => void) {
  window.addEventListener(AUTH_EXPIRED_EVENT, listener);
  /** 用途：负责 return 的界面或数据处理职责。 */
  return () => window.removeEventListener(AUTH_EXPIRED_EVENT, listener);
}

/** 用途：负责 authFetch 的界面或数据处理职责。 */
export async function authFetch(path: string, init?: RequestInit) {
  const retry = (init as RequestInit & { __authRetry?: boolean } | undefined)?.__authRetry;
  const token = accessToken;
  const headers = new Headers(init?.headers || {});

  if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers
  });

  if (
    response.status === 401
    && !retry
    && !path.startsWith("/auth/refresh")
    && !path.startsWith("/auth/login")
    && !path.startsWith("/auth/register")
  ) {
    const refreshedToken = await refreshAccessToken();

    if (refreshedToken) {
      return authFetch(path, {
        ...init,
        __authRetry: true
      } as RequestInit & { __authRetry: boolean });
    }

    /** 用途：负责 clearAuthSession 的界面或数据处理职责。 */
    clearAuthSession();
    /** 用途：负责 notifyAuthExpired 的界面或数据处理职责。 */
    notifyAuthExpired();
  }

  return response;
}

/** 用途：负责 requestJson 的界面或数据处理职责。 */
export async function requestJson<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await authFetch(path, init);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

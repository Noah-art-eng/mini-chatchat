/** 根据开发或部署环境选择后端地址；Vite 开发环境直连 8000，部署后走同源 /api。 */
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

export function getStoredAccessToken() {
  return accessToken;
}

export function setStoredAccessToken(token: string | null) {
  accessToken = token;
}

export function clearLegacyStoredAccessToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
}

export function hasStoredAuthSessionHint() {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(SESSION_HINT_KEY) === "true";
}

export function setStoredAuthSessionHint(enabled: boolean) {
  if (typeof window === "undefined") return;

  if (enabled) {
    localStorage.setItem(SESSION_HINT_KEY, "true");
  } else {
    localStorage.removeItem(SESSION_HINT_KEY);
  }
}

export function hasLegacyStoredAccessToken() {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(TOKEN_KEY) !== null;
}

/** 清除内存中的访问令牌和浏览器里的会话提示，让前端回到未登录状态。 */
export function clearAuthSession() {
  accessToken = null;
  clearLegacyStoredAccessToken();
  setStoredAuthSessionHint(false);
}

/**
 * 使用 HttpOnly refresh cookie 换取新的访问令牌。
 * 多个请求同时遇到 401 时共享同一个 Promise，避免并发刷新和令牌轮换互相冲突。
 */
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
        setStoredAuthSessionHint(Boolean(accessToken));
        return accessToken;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

export function notifyAuthExpired() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

export function onAuthExpired(listener: () => void) {
  window.addEventListener(AUTH_EXPIRED_EVENT, listener);
  return () => window.removeEventListener(AUTH_EXPIRED_EVENT, listener);
}

/**
 * 所有需要认证的前端 API 都从这里发出。
 * 请求收到 401 时只尝试刷新并重放一次；再次失败就清理会话并通知 AuthContext 跳回登录态。
 */
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

    clearAuthSession();
    notifyAuthExpired();
  }

  return response;
}

/** 在 authFetch 之上处理普通 JSON API；流式接口会直接使用 authFetch 读取响应体。 */
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

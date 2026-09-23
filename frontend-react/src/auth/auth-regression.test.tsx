import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  authFetch,
  getStoredAccessToken,
  setStoredAccessToken
} from "../api/client";
import { renderWithI18n } from "../test/render";
import { AuthProvider, useAuth } from "./AuthContext";

/** 用途：负责 jsonResponse 的界面或数据处理职责。 */
function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: {
      "Content-Type": "application/json"
    },
    status
  });
}

/** 用途：负责 AuthLoginProbe 的界面或数据处理职责。 */
function AuthLoginProbe() {
  const auth = useAuth();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div>
      <span data-testid="auth-status">{auth.status}</span>
      <span data-testid="auth-email">{auth.user.email ?? "none"}</span>
      <button
        type="button"
        onClick={() =>
          auth.login({
            email: "auth@example.test",
            password: "CorrectHorse123"
          })
        }
      >
        Login
      </button>
    </div>
  );
}

describe("auth regression", () => {
  /** 用途：负责 afterEach 的界面或数据处理职责。 */
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("attaches Bearer token to API requests", async () => {
    /** 用途：负责 setStoredAccessToken 的界面或数据处理职责。 */
    setStoredAccessToken("token-123");
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
      void _input;
      void _init;
      return jsonResponse({ ok: true });
    });
    vi.stubGlobal("fetch", fetchMock);

    await authFetch("/models");

    const [, init] = fetchMock.mock.calls[0];
    const headers = init?.headers as Headers;
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(headers.get("Authorization")).toBe("Bearer token-123");
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(localStorage.getItem("mini-chatchat:access-token")).toBeNull();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("clears stale token and emits auth expired when refresh fails", async () => {
    /** 用途：负责 setStoredAccessToken 的界面或数据处理职责。 */
    setStoredAccessToken("stale-token");
    const fetchMock = vi.fn(async () => jsonResponse({ detail: "invalid token" }, 401));
    const expiredListener = vi.fn();
    window.addEventListener("mini-chatchat:auth-expired", expiredListener);
    vi.stubGlobal("fetch", fetchMock);

    await authFetch("/auth/me");

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(getStoredAccessToken()).toBeNull();
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(expiredListener).toHaveBeenCalledTimes(1);
    window.removeEventListener("mini-chatchat:auth-expired", expiredListener);
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("stores access token in memory and exposes authenticated user after login", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/auth/login")) {
        return jsonResponse({
          access_token: "login-token",
          expires_in: 3600,
          token_type: "bearer",
          user: {
            auth_provider: "email",
            avatar_url: null,
            display_name: "Auth User",
            email: "auth@example.test",
            id: 123,
            is_active: true,
            is_guest: false
          }
        });
      }

      if (url.endsWith("/auth/preferences")) {
        return jsonResponse({
          preferences: {
            created_at: "2026-01-01 00:00:00",
            developer_mode: false,
            language: "en",
            onboarding_completed: true,
            preferred_model: null,
            theme: "light",
            updated_at: "2026-01-01 00:00:00",
            user_id: 123
          }
        });
      }

      return jsonResponse({ detail: "not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(
      <AuthProvider>
        <AuthLoginProbe />
      </AuthProvider>
    );

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("auth-status")).toHaveTextContent("guest");
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByTestId("auth-status")).toHaveTextContent("authenticated");
    });
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("auth-email")).toHaveTextContent("auth@example.test");
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(getStoredAccessToken()).toBe("login-token");
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(localStorage.getItem("mini-chatchat:access-token")).toBeNull();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("clears legacy localStorage token and restores session through refresh", async () => {
    localStorage.setItem("mini-chatchat:access-token", "legacy-token");
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/auth/refresh")) {
        return jsonResponse({
          access_token: "refreshed-token",
          expires_in: 900,
          token_type: "bearer",
          user: {
            auth_provider: "email",
            avatar_url: null,
            display_name: "Refresh User",
            email: "refresh@example.test",
            id: 321,
            is_active: true,
            is_guest: false
          }
        });
      }

      if (url.endsWith("/auth/me")) {
        return jsonResponse({
          authenticated: true,
          user: {
            auth_provider: "email",
            avatar_url: null,
            display_name: "Refresh User",
            email: "refresh@example.test",
            id: 321,
            is_active: true,
            is_guest: false
          }
        });
      }

      if (url.endsWith("/auth/preferences")) {
        return jsonResponse({
          preferences: {
            created_at: "2026-01-01 00:00:00",
            developer_mode: false,
            language: "en",
            onboarding_completed: true,
            preferred_model: null,
            theme: "light",
            updated_at: "2026-01-01 00:00:00",
            user_id: 321
          }
        });
      }

      return jsonResponse({ detail: "not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(
      <AuthProvider>
        <AuthLoginProbe />
      </AuthProvider>
    );

    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByTestId("auth-status")).toHaveTextContent("authenticated");
    });
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(getStoredAccessToken()).toBe("refreshed-token");
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(localStorage.getItem("mini-chatchat:access-token")).toBeNull();
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/auth/refresh"))).toBe(true);
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/auth/me"))).toBe(true);
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("refreshes expired access token and retries original request once", async () => {
    /** 用途：负责 setStoredAccessToken 的界面或数据处理职责。 */
    setStoredAccessToken("expired-token");
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const headers = init?.headers as Headers;

      if (url.endsWith("/auth/refresh")) {
        return jsonResponse({
          access_token: "new-token",
          expires_in: 900,
          token_type: "bearer",
          user: {}
        });
      }

      if (headers.get("Authorization") === "Bearer expired-token") {
        return jsonResponse({ detail: "expired" }, 401);
      }

      return jsonResponse({ ok: true });
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await authFetch("/protected");

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(response.status).toBe(200);
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(getStoredAccessToken()).toBe("new-token");
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/auth/refresh"))).toHaveLength(1);
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/protected"))).toHaveLength(2);
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("shares one refresh request across concurrent 401 responses", async () => {
    /** 用途：负责 setStoredAccessToken 的界面或数据处理职责。 */
    setStoredAccessToken("expired-token");
    let refreshCount = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const headers = init?.headers as Headers;

      if (url.endsWith("/auth/refresh")) {
        refreshCount += 1;
        return jsonResponse({
          access_token: "shared-token",
          expires_in: 900,
          token_type: "bearer",
          user: {}
        });
      }

      if (headers.get("Authorization") === "Bearer expired-token") {
        return jsonResponse({ detail: "expired" }, 401);
      }

      return jsonResponse({ ok: true });
    });
    vi.stubGlobal("fetch", fetchMock);

    const [first, second] = await Promise.all([
      /** 用途：负责 authFetch 的界面或数据处理职责。 */
      authFetch("/protected-a"),
      /** 用途：负责 authFetch 的界面或数据处理职责。 */
      authFetch("/protected-b")
    ]);

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(first.status).toBe(200);
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(second.status).toBe(200);
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(refreshCount).toBe(1);
  });
});

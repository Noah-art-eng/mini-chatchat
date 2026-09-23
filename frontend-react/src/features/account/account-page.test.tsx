import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../../auth";
import { ToastProvider } from "../../components/ui";
import { renderWithI18n } from "../../test/render";
import { AccountPage } from "./AccountPage";

/** 用途：负责 jsonResponse 的界面或数据处理职责。 */
function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status
  });
}

const user = {
  auth_provider: "email",
  avatar_url: null,
  display_name: "Account User",
  email: "account@example.test",
  id: 456,
  is_active: true,
  is_guest: false
};

const preferences = {
  created_at: "2026-01-01 00:00:00",
  developer_mode: false,
  language: "en",
  onboarding_completed: true,
  preferred_model: null,
  theme: "light",
  updated_at: "2026-01-01 00:00:00",
  user_id: 456
};

const sessions = [
  {
    created_at: "2026-01-01 00:00:00",
    device: "Chrome on macOS",
    expires_at: "2026-02-01 00:00:00",
    ip_address: "127.0.*.*",
    is_active: true,
    is_current: true,
    last_used_at: "2026-01-02 00:00:00",
    revoked_at: null,
    session_id: "session-current"
  },
  {
    created_at: "2026-01-01 01:00:00",
    device: "Safari on iOS",
    expires_at: "2026-02-01 01:00:00",
    ip_address: "10.0.*.*",
    is_active: true,
    is_current: false,
    last_used_at: "2026-01-02 01:00:00",
    revoked_at: null,
    session_id: "session-other"
  }
];

const providers = [
  {
    account: null,
    configured: true,
    label: "Google",
    linked: false,
    provider: "google"
  },
  {
    account: {
      created_at: "2026-01-01 00:00:00",
      provider: "github",
      provider_avatar: null,
      provider_display_name: "Account User",
      provider_email: "account@example.test",
      updated_at: "2026-01-01 00:00:00"
    },
    configured: true,
    label: "GitHub",
    linked: true,
    provider: "github"
  }
];

/** 用途：负责 renderAccountPage 的界面或数据处理职责。 */
function renderAccountPage() {
  localStorage.setItem("mini-chatchat:has-auth-session", "true");

  return renderWithI18n(
    <ToastProvider>
      <AuthProvider>
        <AccountPage />
      </AuthProvider>
    </ToastProvider>
  );
}

/** 用途：负责 installFetchMock 的界面或数据处理职责。 */
function installFetchMock() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method || "GET";

    if (url.endsWith("/auth/refresh")) {
      return jsonResponse({
        access_token: "account-token",
        expires_in: 900,
        token_type: "bearer",
        user
      });
    }

    if (url.endsWith("/auth/me")) {
      return jsonResponse({ authenticated: true, user });
    }

    if (url.endsWith("/auth/preferences")) {
      return jsonResponse({ preferences });
    }

    if (url.endsWith("/auth/sessions") && method === "GET") {
      return jsonResponse({ sessions });
    }

    if (url.endsWith("/auth/oauth/providers")) {
      return jsonResponse({ providers });
    }

    if (url.endsWith("/auth/account") && method === "PATCH") {
      return jsonResponse({
        user: {
          ...user,
          display_name: "Renamed User"
        }
      });
    }

    if (url.includes("/auth/sessions/session-other") && method === "DELETE") {
      return jsonResponse({
        message: "session revoked",
        revoked: true,
        revoked_current: false
      });
    }

    if (url.endsWith("/auth/logout-others")) {
      return jsonResponse({
        message: "logged out other sessions",
        revoked_sessions: 1
      });
    }

    if (url.endsWith("/auth/logout-all")) {
      return jsonResponse({
        message: "logged out all sessions",
        revoked_sessions: 2
      });
    }

    if (url.endsWith("/auth/oauth/link/google") && method === "POST") {
      return jsonResponse({
        authorization_url: "https://accounts.google.com/o/oauth2/v2/auth",
        provider: "google"
      });
    }

    if (url.endsWith("/auth/oauth/link/github") && method === "DELETE") {
      return jsonResponse({
        message: "oauth account unlinked",
        provider: "github",
        unlinked: true
      });
    }

    return jsonResponse({ detail: "not found" }, 404);
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("AccountPage", () => {
  /** 用途：负责 afterEach 的界面或数据处理职责。 */
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("loads account profile and session list", async () => {
    /** 用途：负责 installFetchMock 的界面或数据处理职责。 */
    installFetchMock();
    /** 用途：负责 renderAccountPage 的界面或数据处理职责。 */
    renderAccountPage();

    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByDisplayValue("Account User")).toBeInTheDocument();
    });

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getAllByText("account@example.test").length).toBeGreaterThan(0);
    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByText("Current device")).toBeInTheDocument();
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByText("Other device")).toBeInTheDocument();
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByText("Chrome on macOS")).toBeInTheDocument();
    });
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("updates display name and shows a toast", async () => {
    /** 用途：负责 installFetchMock 的界面或数据处理职责。 */
    installFetchMock();
    /** 用途：负责 renderAccountPage 的界面或数据处理职责。 */
    renderAccountPage();

    const input = await screen.findByDisplayValue("Account User");
    fireEvent.change(input, { target: { value: "Renamed User" } });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByText("Profile updated.")).toBeInTheDocument();
    });
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("revokes another device with confirmation", async () => {
    const fetchMock = installFetchMock();
    /** 用途：负责 renderAccountPage 的界面或数据处理职责。 */
    renderAccountPage();

    const otherRow = await screen.findByText("Safari on iOS");
    fireEvent.click(
      /** 用途：负责 within 的界面或数据处理职责。 */
      within(otherRow.closest(".session-row") as HTMLElement).getByRole(
        "button",
        { name: "Revoke" }
      )
    );

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByText("Revoke session")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByText("Session revoked.")).toBeInTheDocument();
    });
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(fetchMock.mock.calls.some(([input]) =>
      /** 用途：负责 String 的界面或数据处理职责。 */
      String(input).includes("/auth/sessions/session-other")
    )).toBe(true);
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("logs out other devices and all devices", async () => {
    const fetchMock = installFetchMock();
    /** 用途：负责 renderAccountPage 的界面或数据处理职责。 */
    renderAccountPage();

    await screen.findByText("Safari on iOS");
    fireEvent.click(screen.getByRole("button", { name: "Logout other devices" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByText("Other sessions revoked.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Logout all devices" }));
    fireEvent.click(screen.getByRole("button", { name: "Logout all" }));

    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(fetchMock.mock.calls.some(([input]) =>
        /** 用途：负责 String 的界面或数据处理职责。 */
        String(input).endsWith("/auth/logout-all")
      )).toBe(true);
    });
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("shows OAuth bindings and unlinks a provider with confirmation", async () => {
    const fetchMock = installFetchMock();
    /** 用途：负责 renderAccountPage 的界面或数据处理职责。 */
    renderAccountPage();

    await screen.findByText("GitHub");
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByText("Google")).toBeInTheDocument();
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getAllByText("account@example.test").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Unlink" }));
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByText("Unlink account")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByText("Account unlinked.")).toBeInTheDocument();
    });
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(fetchMock.mock.calls.some(([input]) =>
      /** 用途：负责 String 的界面或数据处理职责。 */
      String(input).endsWith("/auth/oauth/link/github")
    )).toBe(true);
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("renders Chinese account labels", async () => {
    localStorage.setItem("mini-chatchat:language", "zh-CN");
    /** 用途：负责 installFetchMock 的界面或数据处理职责。 */
    installFetchMock();
    /** 用途：负责 renderAccountPage 的界面或数据处理职责。 */
    renderAccountPage();

    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByText("账户设置")).toBeInTheDocument();
    });
    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByText("当前设备")).toBeInTheDocument();
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.getByText("退出其他设备")).toBeInTheDocument();
    });
  });
});

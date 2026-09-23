import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AuthProvider, GuestRoute, ProtectedRoute, useAuth } from "./index";
import { renderWithI18n } from "../test/render";

/** 用途：负责 AuthProbe 的界面或数据处理职责。 */
function AuthProbe() {
  const auth = useAuth();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div>
      <span data-testid="auth-status">{auth.status}</span>
      <span data-testid="can-chat">{String(auth.can("can_use_chat"))}</span>
      <span data-testid="can-agent">{String(auth.can("can_use_agent"))}</span>
      <span data-testid="can-kb">{String(auth.can("can_manage_kb"))}</span>
    </div>
  );
}

describe("auth foundation", () => {
  /** 用途：负责 it 的界面或数据处理职责。 */
  it("defaults to a guest session with limited permissions", () => {
    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("auth-status")).toHaveTextContent("guest");
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("can-chat")).toHaveTextContent("true");
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("can-agent")).toHaveTextContent("false");
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("can-kb")).toHaveTextContent("false");
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("supports guest and protected route wrappers without routing changes", () => {
    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(
      <AuthProvider>
        <GuestRoute fallback={<span>not guest</span>}>
          <span>guest content</span>
        </GuestRoute>
        <ProtectedRoute fallback={<span>auth required</span>}>
          <span>protected content</span>
        </ProtectedRoute>
      </AuthProvider>
    );

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByText("guest content")).toBeInTheDocument();
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByText("auth required")).toBeInTheDocument();
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
  });
});

import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Button, ConfirmDialog, StatusBadge } from "./index";
import { renderWithI18n } from "../../test/render";

describe("UI foundation", () => {
  /** 用途：负责 it 的界面或数据处理职责。 */
  it("renders Button with loading disabled state", () => {
    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(<Button loading>Save</Button>);

    const button = screen.getByRole("button", { name: /loadingsave/i });
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(button).toBeDisabled();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("renders StatusBadge with semantic label", () => {
    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(<StatusBadge status="ok" />);

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByText("OK")).toBeInTheDocument();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("renders ConfirmDialog and handles actions", () => {
    const onCancel = vi.fn();
    const onConfirm = vi.fn();

    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(
      <ConfirmDialog
        description="Delete this conversation?"
        isOpen
        onCancel={onCancel}
        onConfirm={onConfirm}
        title="Delete Conversation"
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(onCancel).toHaveBeenCalledTimes(1);
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../../components/ui";
import { I18nProvider } from "../../i18n";
import { ConversationProvider } from "../../stores/conversationStore";
import {
  deleteConversations,
  getConversationMessages,
  listConversations
} from "../../api/conversations";
import { ConversationSidebar } from "./ConversationSidebar";

vi.mock("../../api/conversations", () => ({
  deleteConversation: vi.fn(),
  deleteConversations: vi.fn(),
  getConversationMessages: vi.fn(),
  listConversations: vi.fn(),
  renameConversation: vi.fn()
}));

describe("conversation destructive actions", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("confirms clear-all, deletes persisted conversations, and refreshes the list", async () => {
    let deleted = false;
    vi.mocked(listConversations).mockImplementation(async () => ({
      conversations: deleted
        ? []
        : [
            {
              id: 41,
              title: "Release review",
              create_time: "2026-10-02T10:00:00Z"
            }
          ]
    }));
    vi.mocked(getConversationMessages).mockResolvedValue({
      conversation_id: 41,
      messages: []
    });
    vi.mocked(deleteConversations).mockImplementation(async ids => {
      deleted = true;
      return {
        results: ids.map(conversationId => ({
          conversation_id: conversationId,
          deleted: true,
          missing: false
        }))
      };
    });

    render(
      <I18nProvider>
        <ToastProvider>
          <ConversationProvider>
            <ConversationSidebar onStartNewConversation={vi.fn()} />
          </ConversationProvider>
        </ToastProvider>
      </I18nProvider>
    );

    await screen.findByText("Release review");
    fireEvent.click(screen.getByRole("button", { name: "Clear All" }));
    const dialog = screen.getByRole("dialog", { name: "Clear all conversations" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Clear All" }));

    await waitFor(() => {
      expect(deleteConversations).toHaveBeenCalledWith([41]);
      expect(screen.queryByText("Release review")).not.toBeInTheDocument();
    });
  });
});

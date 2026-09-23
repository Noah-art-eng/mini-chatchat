import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChatArea } from "./ChatArea";
import { ToastProvider } from "../../components/ui";
import { ConversationProvider } from "../../stores/conversationStore";
import { renderWithI18n } from "../../test/render";

/** 用途：负责 makeSseResponse 的界面或数据处理职责。 */
function makeSseResponse() {
  return new Response(
    [
      'data: {"type":"sources","sources":[],"conversation_id":101}',
      "",
      'data: {"type":"token","content":"Search answer"}',
      "",
      'data: {"type":"done","assistant_message_id":202,"conversation_id":101}',
      "",
      ""
    ].join("\n"),
    {
      headers: {
        "Content-Type": "text/event-stream"
      },
      status: 200
    }
  );
}

/** 用途：负责 renderChatArea 的界面或数据处理职责。 */
function renderChatArea() {
  return renderWithI18n(
    <ToastProvider>
      <ConversationProvider>
        <ChatArea preferredMode="chat" />
      </ConversationProvider>
    </ToastProvider>
  );
}

describe("chat mode payloads", () => {
  /** 用途：负责 beforeEach 的界面或数据处理职责。 */
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.includes("/conversations") && !url.includes("/messages")) {
          return new Response(JSON.stringify({ conversations: [] }), {
            headers: { "Content-Type": "application/json" },
            status: 200
          });
        }

        if (url.includes("/kb_chat")) {
          return makeSseResponse();
        }

        return new Response(JSON.stringify({}), {
          headers: { "Content-Type": "application/json" },
          status: 200
        });
      })
    );
  });

  /** 用途：负责 afterEach 的界面或数据处理职责。 */
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("sends search_engine mode without kb_name after selecting Search", async () => {
    /** 用途：负责 renderChatArea 的界面或数据处理职责。 */
    renderChatArea();

    fireEvent.click(await screen.findByTestId("chat-mode-search-engine"));
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("search-engine-mode-status")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Ask Mini ChatChat/i), {
      target: { value: "新西兰现在几点" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      const kbChatCall = vi
        .mocked(fetch)
        .mock.calls.find(([input]) => String(input).includes("/kb_chat"));

      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(kbChatCall).toBeDefined();
      const payload = JSON.parse(String(kbChatCall?.[1]?.body));

      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(payload.mode).toBe("search_engine");
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(payload.query).toBe("新西兰现在几点");
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(payload.stream).toBe(true);
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(payload).not.toHaveProperty("kb_name");
    });
  });
});

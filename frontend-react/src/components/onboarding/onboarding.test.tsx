import { createRef } from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChatEmptyState } from "../ChatEmptyState";
import { ChatWorkspace } from "../../features/chat/ChatWorkspace";
import { App } from "../../pages/App";
import { AuthProvider } from "../../auth";
import { ConversationProvider } from "../../stores/conversationStore";
import { renderWithI18n } from "../../test/render";
import { ToastProvider } from "../ui";
import { AppRouter } from "../../router";
import {
  DEVELOPER_MODE_INTRO_SEEN_KEY,
  ONBOARDING_COMPLETED_KEY
} from "../../onboarding/preferences";

/** 用途：负责 renderApp 的界面或数据处理职责。 */
function renderApp(path = "/chat") {
  return renderWithI18n(
    <AppRouter initialPath={path}>
      <ToastProvider>
        <AuthProvider>
          <ConversationProvider>
            <App />
          </ConversationProvider>
        </AuthProvider>
      </ToastProvider>
    </AppRouter>
  );
}

/** 用途：负责 mockFetch 的界面或数据处理职责。 */
function mockFetch() {
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

      if (url.includes("/models")) {
        return new Response(
          JSON.stringify({
            chat: {
              provider: "deepseek",
              default_model: "deepseek-chat",
              base_url: "https://api.deepseek.com",
              temperature: 0.7,
              max_tokens: null
            },
            embedding: { default_model: "all-MiniLM-L6-v2" }
          }),
          { headers: { "Content-Type": "application/json" }, status: 200 }
        );
      }

      if (url.includes("/health/deps")) {
        return new Response(
          JSON.stringify({
            status: "ok",
            checks: {
              database: "ok",
              data_dir: "ok",
              uploads_dir: "ok",
              chat_provider: "ok",
              embedding_model: "ok"
            }
          }),
          { headers: { "Content-Type": "application/json" }, status: 200 }
        );
      }

      if (url.includes("/health")) {
        return new Response(
          JSON.stringify({
            status: "ok",
            service: "mini-chatchat",
            version: "0.1.0",
            provider: "deepseek"
          }),
          { headers: { "Content-Type": "application/json" }, status: 200 }
        );
      }

      if (url.includes("/agent/tools")) {
        return new Response(JSON.stringify({ tools: [] }), {
          headers: { "Content-Type": "application/json" },
          status: 200
        });
      }

      if (url.includes("/agent/mcp")) {
        return new Response(JSON.stringify({ servers: [], tools: [], enabled: true }), {
          headers: { "Content-Type": "application/json" },
          status: 200
        });
      }

      return new Response(JSON.stringify({}), {
        headers: { "Content-Type": "application/json" },
        status: 200
      });
    })
  );
}

/** 用途：负责 renderChatWorkspace 的界面或数据处理职责。 */
function renderChatWorkspace(overrides = {}) {
  return renderWithI18n(
    <ToastProvider>
      <ConversationProvider>
        <ChatWorkspace
          activeModeDescription="Knowledge mode"
          activeModeLabel="Local KB"
          agentError={null}
          chatMode="local_kb"
          chatModes={["local_kb", "search_engine", "temp_kb", "agent"]}
          conversationId={null}
          detailsTab="sources"
          disabledReason={null}
          error={null}
          hasMessages={false}
          input=""
          isAgentRunning={false}
          isLoadingMessages={false}
          isSending={false}
          isStreaming={false}
          isUploadingTempFile={false}
          kbName="default"
          messages={[]}
          onChangeDetailsTab={vi.fn()}
          onChangeInput={vi.fn()}
          onChangeKbName={vi.fn()}
          onChangeMode={vi.fn()}
          onChangeSelectedTempFile={vi.fn()}
          onOpenAssistantSources={vi.fn()}
          onOpenModeGuide={vi.fn()}
          onSelectAssistantMessage={vi.fn()}
          onStartEmptyMode={vi.fn()}
          onSubmit={vi.fn()}
          onTempFileUpload={vi.fn()}
          preferredMode="chat"
          selectedAssistantMessageId={null}
          selectedTempFile={null}
          streamStatus={null}
          streamTokenText=""
          streamingMessage=""
          tempFileInputRef={createRef<HTMLInputElement>()}
          tempFileName={null}
          tempFileStatus={null}
          tempKbId={null}
          visibleAgentResult={null}
          {...overrides}
        />
      </ConversationProvider>
    </ToastProvider>
  );
}

describe("onboarding and first-run guidance", () => {
  /** 用途：负责 beforeEach 的界面或数据处理职责。 */
  beforeEach(() => {
    localStorage.clear();
    /** 用途：负责 mockFetch 的界面或数据处理职责。 */
    mockFetch();
  });

  /** 用途：负责 afterEach 的界面或数据处理职责。 */
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("shows the welcome guide on first visit and saves completion on Skip", async () => {
    /** 用途：负责 renderApp 的界面或数据处理职责。 */
    renderApp();

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(await screen.findByText("Welcome to Mini ChatChat")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Skip" }));

    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.queryByText("Welcome to Mini ChatChat")).not.toBeInTheDocument();
    });
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(localStorage.getItem(ONBOARDING_COMPLETED_KEY)).toBe("true");
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("does not show the welcome guide when onboarding is completed", () => {
    localStorage.setItem(ONBOARDING_COMPLETED_KEY, "true");
    /** 用途：负责 renderApp 的界面或数据处理职责。 */
    renderApp();

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.queryByText("Welcome to Mini ChatChat")).not.toBeInTheDocument();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("opens the guides again from System", async () => {
    localStorage.setItem(ONBOARDING_COMPLETED_KEY, "true");
    /** 用途：负责 renderApp 的界面或数据处理职责。 */
    renderApp("/system");

    fireEvent.click(await screen.findByRole("button", { name: "Show welcome guide again" }));
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(await screen.findByText("Welcome to Mini ChatChat")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    fireEvent.click(await screen.findByRole("button", { name: "Mode guide" }));
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(await screen.findByText("How chat modes work")).toBeInTheDocument();
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getAllByText("Knowledge Base").length).toBeGreaterThan(0);
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByText("Web Search")).toBeInTheDocument();
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByText("Temporary File")).toBeInTheDocument();
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getAllByText("Agent").length).toBeGreaterThan(0);
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("empty action cards switch modes without sending", () => {
    const onStartMode = vi.fn();
    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(
      <ChatEmptyState
        mode="local_kb"
        onStartMode={onStartMode}
        onUseSuggestion={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId("empty-action-search-engine"));
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(onStartMode).toHaveBeenCalledWith("search_engine");
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("agent examples fill the composer without submitting", () => {
    const onUseSuggestion = vi.fn();
    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(
      <ChatEmptyState
        mode="agent"
        onStartMode={vi.fn()}
        onUseSuggestion={onUseSuggestion}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "What time is it in New Zealand?" }));
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(onUseSuggestion).toHaveBeenCalledWith("What time is it in New Zealand?");
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("Developer Mode intro supports cancel and confirm", async () => {
    const onChangeDetailsTab = vi.fn();
    /** 用途：负责 renderChatWorkspace 的界面或数据处理职责。 */
    renderChatWorkspace({ onChangeDetailsTab });

    fireEvent.click(screen.getByRole("button", { name: "Developer Mode" }));
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(await screen.findByText("Enable Developer Mode?")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => {
      /** 用途：负责 expect 的界面或数据处理职责。 */
      expect(screen.queryByText("Enable Developer Mode?")).not.toBeInTheDocument();
    });
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(localStorage.getItem(DEVELOPER_MODE_INTRO_SEEN_KEY)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Developer Mode" }));
    fireEvent.click(await screen.findByRole("button", { name: "Enable Developer Mode" }));
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(localStorage.getItem(DEVELOPER_MODE_INTRO_SEEN_KEY)).toBe("true");
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByRole("button", { name: "Developer Tools" })).toBeInTheDocument();
  });
});

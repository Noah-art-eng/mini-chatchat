import { createRef } from "react";
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AgentWorkspace } from "./agent";
import { KnowledgeWorkspace } from "./kb";
import { SystemWorkspace } from "./system";
import { ChatWorkspace } from "../features/chat/ChatWorkspace";
import { renderWithI18n } from "../test/render";

describe("workspace smoke tests", () => {
  /** 用途：负责 it 的界面或数据处理职责。 */
  it("renders ChatWorkspace in agent mode", () => {
    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(
      <ChatWorkspace
        activeModeDescription="Agent mode"
        activeModeLabel="Agent"
        agentError={null}
        chatMode="agent"
        chatModes={["local_kb", "search_engine", "temp_kb", "agent"]}
        conversationId={null}
        detailsTab="trace"
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
        preferredMode="agent"
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
      />
    );

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("agent-mode-status")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Agent Steps" }));
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByText("Agent Trace")).toBeInTheDocument();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("renders KnowledgeWorkspace with empty documents", () => {
    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(
      <KnowledgeWorkspace
        activeDocumentAction={null}
        documentActionStatus={null}
        documents={[]}
        error={null}
        fileInputRef={createRef<HTMLInputElement>()}
        importInputRef={createRef<HTMLInputElement>()}
        isKbActionLoading={false}
        isLoading={false}
        isUploading={false}
        kbActionStatus={null}
        kbName="default"
        knowledgeBases={[{ id: 1, kb_name: "default" }]}
        onChangeImportFile={vi.fn()}
        onChangeUploadFile={vi.fn()}
        onDeleteDocument={vi.fn()}
        onDownloadDocument={vi.fn()}
        onExportKb={vi.fn()}
        onImportKb={vi.fn()}
        onRefreshDocuments={vi.fn()}
        onReindexDocument={vi.fn()}
        onSelectKnowledgeBase={vi.fn()}
        onUploadDocument={vi.fn()}
        selectedFile={null}
        selectedImportFile={null}
        uploadStatus={null}
      />
    );

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("kb-panel")).toBeInTheDocument();
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(
      screen.getAllByText("No documents in this knowledge base yet.")[0]
    ).toBeInTheDocument();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("renders AgentWorkspace result", () => {
    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(
      <AgentWorkspace
        error={null}
        isRunning={false}
        result={{
          answer: "The result is 200.",
          error: null,
          tool_call: {
            tool: "calculator",
            arguments: { expression: "25 * 8" },
            reason: "Need arithmetic."
          },
          tool_result: {
            ok: true,
            result: 200
          },
          trace: []
        }}
      />
    );

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("agent-tool-call")).toBeInTheDocument();
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("agent-tool-result")).toBeInTheDocument();
    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByTestId("agent-final-answer")).toBeInTheDocument();
  });

  /** 用途：负责 it 的界面或数据处理职责。 */
  it("renders SystemWorkspace status", () => {
    /** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
    renderWithI18n(
      <SystemWorkspace
        chatMode="local_kb"
        deps={{
          status: "ok",
          checks: {
            database: "ok",
            data_dir: "ok",
            uploads_dir: "ok",
            chat_provider: "ok",
            embedding_model: "ok"
          }
        }}
        error={null}
        health={{
          status: "ok",
          service: "mini-chatchat",
          version: "0.1.0",
          provider: "deepseek"
        }}
        kbName="default"
        mcpError={null}
        mcpServers={{ servers: [] }}
        mcpTools={{ tools: [], enabled: true, provider: "mcp" }}
        models={{
          chat: {
            provider: "deepseek",
            default_model: "deepseek-chat",
            base_url: "https://api.deepseek.com",
            temperature: 0.7,
            max_tokens: null
          },
          embedding: {
            default_model: "all-MiniLM-L6-v2"
          }
        }}
        status="ready"
        tools={[]}
        toolsError={null}
        onShowModeGuide={vi.fn()}
        onShowWelcomeGuide={vi.fn()}
      />
    );

    /** 用途：负责 expect 的界面或数据处理职责。 */
    expect(screen.getByLabelText(/system/i)).toBeInTheDocument();
  });
});

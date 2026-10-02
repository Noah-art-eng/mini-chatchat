import { useEffect, useState, type RefObject } from "react";
import { AgentTracePanel } from "../../components/AgentTracePanel";
import { ChatComposer } from "../../components/ChatComposer";
import { ChatEmptyState } from "../../components/ChatEmptyState";
import { ChatMessageList } from "../../components/ChatMessageList";
import { ContextPanel } from "../../components/ContextPanel";
import { RetrievalDebugPanel } from "../../components/RetrievalDebugPanel";
import { SourcesPanel } from "../../components/SourcesPanel";
import {
  ChatHeader,
  ChatMessageViewport,
  ChatModeControls,
  TempFilePanel
} from "../../components/chat";
import { chatStyles } from "../../components/chat/chatStyles";
import { cx } from "../../components/ui/utils";
import { DeveloperModeIntroDialog } from "../../components/onboarding";
import { useI18n } from "../../i18n";
import {
  isDeveloperModeIntroSeen,
  setDeveloperModeIntroSeen
} from "../../onboarding/preferences";
import type { AgentRunResponse } from "../../types/agent";
import type { ChatMode } from "../../types/chat";
import type { ChatMessage } from "../../types/conversation";

export type DetailsTab = "sources" | "debug" | "trace";

const developerToggleClass =
  "developer-toggle text-mc-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mc-border-focus";
const activeDeveloperToggleClass =
  "developer-toggle active border-[color-mix(in_srgb,var(--color-info)_24%,var(--color-border-subtle))] bg-mc-info-soft text-mc-info focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mc-border-focus";

type ChatWorkspaceProps = {
  activeModeDescription: string;
  activeModeLabel: string;
  agentError: string | null;
  chatMode: ChatMode;
  chatModes: ChatMode[];
  conversationId: number | null;
  detailsTab: DetailsTab;
  disabledReason: string | null;
  error: string | null;
  hasMessages: boolean;
  input: string;
  isAgentRunning: boolean;
  isLoadingMessages: boolean;
  isSending: boolean;
  isStreaming: boolean;
  isUploadingTempFile: boolean;
  kbName: string;
  knowledgeBaseNames: string[];
  messages: ChatMessage[];
  onChangeDetailsTab: (tab: DetailsTab) => void;
  onChangeInput: (value: string) => void;
  onChangeKbName: (kbName: string) => void;
  onChangeMode: (mode: ChatMode) => void;
  onChangeSelectedTempFile: (file: File | null) => void;
  onOpenAssistantSources: (messageId: number) => void;
  onOpenModeGuide: () => void;
  onSelectAssistantMessage: (messageId: number) => void;
  onStartEmptyMode: (mode: ChatMode) => void;
  onSubmit: () => void;
  onStop: () => void;
  onTempFileUpload: () => void;
  preferredMode: "chat" | "agent";
  selectedAssistantMessageId: number | null;
  selectedTempFile: File | null;
  streamStatus: string | null;
  streamTokenText: string;
  streamingMessage: string;
  tempFileInputRef: RefObject<HTMLInputElement | null>;
  tempFileName: string | null;
  tempFileStatus: string | null;
  tempKbId: string | null;
  visibleAgentResult: AgentRunResponse | null;
};

/** 用途：负责 ChatWorkspace 的界面或数据处理职责。 */
export function ChatWorkspace({
  activeModeDescription,
  activeModeLabel,
  agentError,
  chatMode,
  chatModes,
  conversationId,
  detailsTab,
  disabledReason,
  error,
  hasMessages,
  input,
  isAgentRunning,
  isLoadingMessages,
  isSending,
  isStreaming,
  isUploadingTempFile,
  kbName,
  knowledgeBaseNames,
  messages,
  onChangeDetailsTab,
  onChangeInput,
  onChangeKbName,
  onChangeMode,
  onChangeSelectedTempFile,
  onOpenAssistantSources,
  onOpenModeGuide,
  onSelectAssistantMessage,
  onStartEmptyMode,
  onSubmit,
  onStop,
  onTempFileUpload,
  preferredMode,
  selectedAssistantMessageId,
  selectedTempFile,
  streamStatus,
  streamTokenText,
  streamingMessage,
  tempFileInputRef,
  tempFileName,
  tempFileStatus,
  tempKbId,
  visibleAgentResult
}: ChatWorkspaceProps) {
  const { t } = useI18n();
  const [isContextOpen, setIsContextOpen] = useState(false);
  const [isDeveloperMode, setIsDeveloperMode] = useState(false);
  const [isDeveloperIntroOpen, setIsDeveloperIntroOpen] = useState(false);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    if (!isDeveloperMode && detailsTab === "debug") {
      /** 用途：负责 onChangeDetailsTab 的界面或数据处理职责。 */
      onChangeDetailsTab("sources");
      /** 用途：负责 setIsContextOpen 的界面或数据处理职责。 */
      setIsContextOpen(false);
    }
  }, [detailsTab, isDeveloperMode, onChangeDetailsTab]);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    /** 用途：负责 handleShortcut 的界面或数据处理职责。 */
    function handleShortcut(event: KeyboardEvent) {
      const target = event.target;
      const isTyping =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        (target instanceof HTMLElement && target.isContentEditable);

      if (event.key === "Escape" && isContextOpen) {
        event.preventDefault();
        /** 用途：负责 setIsContextOpen 的界面或数据处理职责。 */
        setIsContextOpen(false);
        return;
      }

      const shouldFocusComposer =
        event.key === "/" || ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "l");

      if (!shouldFocusComposer || (isTyping && event.key === "/")) {
        return;
      }

      const composer = document.querySelector<HTMLTextAreaElement>(
        ".chat-composer textarea"
      );

      if (composer) {
        event.preventDefault();
        composer.focus();
      }
    }

    window.addEventListener("keydown", handleShortcut);
    /** 用途：负责 return 的界面或数据处理职责。 */
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [isContextOpen]);

  /** 用途：负责 openDetails 的界面或数据处理职责。 */
  function openDetails(tab: DetailsTab) {
    /** 用途：负责 onChangeDetailsTab 的界面或数据处理职责。 */
    onChangeDetailsTab(tab);
    /** 用途：负责 setIsContextOpen 的界面或数据处理职责。 */
    setIsContextOpen(true);
  }

  /** 用途：负责 toggleDeveloperMode 的界面或数据处理职责。 */
  function toggleDeveloperMode() {
    if (isDeveloperMode) {
      /** 用途：负责 setIsDeveloperMode 的界面或数据处理职责。 */
      setIsDeveloperMode(false);
      if (detailsTab === "debug") {
        /** 用途：负责 onChangeDetailsTab 的界面或数据处理职责。 */
        onChangeDetailsTab("sources");
        /** 用途：负责 setIsContextOpen 的界面或数据处理职责。 */
        setIsContextOpen(false);
      }
      return;
    }

    if (isDeveloperModeIntroSeen()) {
      /** 用途：负责 setIsDeveloperMode 的界面或数据处理职责。 */
      setIsDeveloperMode(true);
      return;
    }

    /** 用途：负责 setIsDeveloperIntroOpen 的界面或数据处理职责。 */
    setIsDeveloperIntroOpen(true);
  }

  /** 用途：负责 confirmDeveloperMode 的界面或数据处理职责。 */
  function confirmDeveloperMode() {
    /** 用途：负责 setDeveloperModeIntroSeen 的界面或数据处理职责。 */
    setDeveloperModeIntroSeen(true);
    /** 用途：负责 setIsDeveloperMode 的界面或数据处理职责。 */
    setIsDeveloperMode(true);
    /** 用途：负责 setIsDeveloperIntroOpen 的界面或数据处理职责。 */
    setIsDeveloperIntroOpen(false);
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section className={chatStyles.area} aria-label={t("chat.title")}>
      <ChatHeader
        activeModeDescription={activeModeDescription}
        activeModeLabel={activeModeLabel}
        chatMode={chatMode}
        conversationId={conversationId}
        kbName={kbName}
        preferredMode={preferredMode}
        tempFileName={tempFileName}
      />

      <ChatModeControls
        chatMode={chatMode}
        kbName={kbName}
        knowledgeBaseNames={knowledgeBaseNames}
        modes={chatModes}
        onChangeKbName={onChangeKbName}
        onChangeMode={onChangeMode}
        onOpenModeGuide={onOpenModeGuide}
      />

      <div
        className={cx(chatStyles.workbench, isContextOpen ? "context-open" : "context-collapsed")}
      >
        <div className={chatStyles.primaryPanel}>
          <div className={chatStyles.modeContext} aria-label={t("chat.runtimeSummary")}>
            {chatMode === "search_engine" && (
              <span className={chatStyles.status} data-testid="search-engine-mode-status">
                {t("chat.searchModeStatus")}
              </span>
            )}
            {chatMode === "agent" && (
              <span className={chatStyles.status} data-testid="agent-mode-status">
                {t("chat.agentModeStatus")}
              </span>
            )}
            <div className={chatStyles.details}>
              {chatMode === "agent" ? (
                <>
                  <button
                    onClick={() => openDetails("trace")}
                    type="button"
                  >
                    {isDeveloperMode ? t("chat.viewTrace") : t("chat.viewAgentSteps")}
                  </button>
                  <button
                    aria-pressed={isDeveloperMode}
                    className={isDeveloperMode ? activeDeveloperToggleClass : developerToggleClass}
                    onClick={toggleDeveloperMode}
                    type="button"
                  >
                    {t("chat.developerMode")}
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => openDetails("sources")}
                    type="button"
                  >
                    {t("chat.viewSources")}
                  </button>
                  <button
                    aria-pressed={isDeveloperMode}
                    className={isDeveloperMode ? activeDeveloperToggleClass : developerToggleClass}
                    onClick={toggleDeveloperMode}
                    type="button"
                  >
                    {t("chat.developerMode")}
                  </button>
                  {isDeveloperMode && (
                    <button
                      onClick={() => openDetails("debug")}
                      type="button"
                    >
                      {t("chat.developerTools")}
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          {chatMode === "temp_kb" && (
            <TempFilePanel
              inputRef={tempFileInputRef}
              isUploading={isUploadingTempFile}
              onChangeFile={onChangeSelectedTempFile}
              onUpload={onTempFileUpload}
              selectedFile={selectedTempFile}
              status={tempFileStatus}
              tempFileName={tempFileName}
              tempKbId={tempKbId}
            />
          )}

          <ChatMessageViewport
            hasMessages={hasMessages}
            isLoadingMessages={isLoadingMessages}
            loadingLabel={t("chat.loadingMessages")}
          >
            {!hasMessages && (
              <ChatEmptyState
                mode={chatMode}
                onStartMode={onStartEmptyMode}
                onUseSuggestion={onChangeInput}
              />
            )}

            {hasMessages && (
              <ChatMessageList
                messages={messages}
                onOpenAssistantSources={messageId => {
                  /** 用途：负责 onOpenAssistantSources 的界面或数据处理职责。 */
                  onOpenAssistantSources(messageId);
                  /** 用途：负责 setIsContextOpen 的界面或数据处理职责。 */
                  setIsContextOpen(true);
                }}
                onSelectAssistantMessage={onSelectAssistantMessage}
                selectedAssistantMessageId={selectedAssistantMessageId}
                streamingMessage={streamingMessage}
              />
            )}
          </ChatMessageViewport>

          {(streamStatus || isStreaming) && (
            <div className={chatStyles.streamStatus} data-testid="agent-stream-status">
              <span className="live-dot h-mc-2 w-mc-2 rounded-full bg-mc-success" aria-hidden="true" />
              {streamStatus || t("chat.streamingNow")}
            </div>
          )}
          {chatMode === "agent" && isAgentRunning && (
            <div className="agent-progress-summary flex items-center justify-between gap-mc-3 rounded-mc-md border border-mc-border-subtle bg-mc-brand-soft px-mc-3 py-mc-2 text-mc-body-small text-mc-secondary [&>strong]:text-mc-text" aria-live="polite">
              <strong>{streamStatus || t("agent.thinking")}</strong>
              <span>
                {t("agent.steps")}: {visibleAgentResult?.steps?.length || 0}
                {" · "}
                {t("agent.toolCall")}: {visibleAgentResult?.tool_count || 0}
              </span>
            </div>
          )}
          {error && chatMode !== "agent" && <p className="m-[0] rounded-mc-md border border-mc-danger-soft bg-mc-danger-soft px-mc-3 py-[10px] text-[13px] text-mc-danger">{error}</p>}

          <ChatComposer
            disabledReason={disabledReason}
            input={input}
            isSending={isSending}
            onChangeInput={onChangeInput}
            onStop={onStop}
            onSubmit={onSubmit}
          />
        </div>

        <ContextPanel
          activeTab={detailsTab}
          ariaLabel={t("chat.details")}
          onChangeTab={tab => onChangeDetailsTab(tab as DetailsTab)}
          isOpen={isContextOpen}
          onClose={() => setIsContextOpen(false)}
          onOpen={() => setIsContextOpen(true)}
          tabs={
            chatMode === "agent"
              ? [{ id: "trace", label: t("chat.trace") }]
              : [
                  { id: "sources", label: t("chat.sources") },
                  { id: "debug", label: t("chat.debug") }
                ]
          }
          title={
            chatMode === "agent"
              ? t("chat.trace")
              : detailsTab === "debug"
                ? t("chat.debug")
                : t("chat.sources")
          }
          workspace={chatMode === "agent" ? "agent" : "chat"}
        >
          {chatMode === "agent" && (
            <AgentTracePanel
              error={agentError}
              isRunning={isAgentRunning}
              result={visibleAgentResult}
              showDeveloperDetails={isDeveloperMode}
              streamStatus={streamStatus}
              streamTokenText={streamTokenText}
            />
          )}
          {chatMode !== "agent" && detailsTab === "sources" && <SourcesPanel />}
          {chatMode !== "agent" && detailsTab === "debug" && <RetrievalDebugPanel />}
        </ContextPanel>
      </div>
      <DeveloperModeIntroDialog
        isOpen={isDeveloperIntroOpen}
        onCancel={() => setIsDeveloperIntroOpen(false)}
        onConfirm={confirmDeveloperMode}
      />
    </section>
  );
}

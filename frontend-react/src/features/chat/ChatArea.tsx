import { useEffect, useMemo, useRef, useState } from "react";
import { uploadTempFile } from "../../api/chat";
import { useAgentRun } from "../../hooks/useAgentRun";
import { useChatStream } from "../../hooks/useChatStream";
import { useI18n } from "../../i18n";
import { useConversationStore } from "../../stores/conversationStore";
import type { AgentRunResponse } from "../../types/agent";
import type { ChatMode } from "../../types/chat";
import type { ChatMessage } from "../../types/conversation";
import { ChatWorkspace, type DetailsTab } from "./ChatWorkspace";

type ChatAreaProps = {
  onOpenModeGuide?: () => void;
  preferredMode?: "chat" | "agent";
};

const chatModes: ChatMode[] = ["local_kb", "search_engine", "temp_kb", "agent"];

/** 用途：负责 buildPersistedAgentResult 的界面或数据处理职责。 */
function buildPersistedAgentResult(
  message: ChatMessage | undefined
): AgentRunResponse | null {
  const metadata = message?.metadata;

  if (!message || !metadata?.agent) {
    return null;
  }

  return {
    answer: message.content,
    tool_call: metadata.tool_call || null,
    tool_result: metadata.tool_result || null,
    planner: metadata.planner || null,
    steps: metadata.steps || [],
    trace: metadata.trace || [],
    tool_count: metadata.tool_count || 0,
    error: null
  };
}

/** 用途：负责 ChatArea 的界面或数据处理职责。 */
export function ChatArea({
  onOpenModeGuide = () => undefined,
  preferredMode = "chat"
}: ChatAreaProps) {
  const { t } = useI18n();
  const {
    chatMode,
    conversationId,
    isLoadingMessages,
    kbName,
    messages,
    selectedAssistantMessageId,
    setChatMode,
    setKbName,
    setSelectedAssistantMessageId,
    setTempFileName,
    setTempKbId,
    streamingMessage,
    tempFileName,
    tempKbId
  } = useConversationStore();
  const { error, isStreaming, sendMessage } = useChatStream();
  const {
    agentResult,
    error: agentError,
    isRunning: isAgentRunning,
    sendAgentMessage,
    streamStatus,
    streamTokenText
  } = useAgentRun();
  const [input, setInput] = useState("");
  const [detailsTab, setDetailsTab] = useState<DetailsTab>("sources");
  const [selectedTempFile, setSelectedTempFile] = useState<File | null>(null);
  const [isUploadingTempFile, setIsUploadingTempFile] = useState(false);
  const [tempFileStatus, setTempFileStatus] = useState<string | null>(null);
  const tempFileInputRef = useRef<HTMLInputElement | null>(null);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    if (preferredMode === "agent" && chatMode !== "agent") {
      /** 用途：负责 setChatMode 的界面或数据处理职责。 */
      setChatMode("agent");
    }
  }, [chatMode, preferredMode, setChatMode]);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    if (chatMode !== "agent" && detailsTab === "trace") {
      /** 用途：负责 setDetailsTab 的界面或数据处理职责。 */
      setDetailsTab("sources");
    }

    if (chatMode === "agent" && detailsTab !== "trace") {
      /** 用途：负责 setDetailsTab 的界面或数据处理职责。 */
      setDetailsTab("trace");
    }
  }, [chatMode, detailsTab]);

  const persistedAgentResult = useMemo(() => {
    const selectedMessage = messages.find(
      message =>
        message.id === selectedAssistantMessageId &&
        message.role === "assistant" &&
        message.metadata?.agent
    );
    const latestAgentMessage = [...messages]
      .reverse()
      .find(message => message.role === "assistant" && message.metadata?.agent);

    return buildPersistedAgentResult(selectedMessage || latestAgentMessage);
  }, [messages, selectedAssistantMessageId]);

  const visibleAgentResult = agentResult || persistedAgentResult;
  const isSending = isStreaming || isAgentRunning;
  const hasMessages = messages.length > 0 || Boolean(streamingMessage);
  const disabledReason =
    chatMode === "temp_kb" && !tempKbId ? t("chat.disabledTempFile") : null;
  const activeModeLabel = t(`modes.${chatMode}`);
  const activeModeDescription =
    chatMode === "agent"
      ? t("chat.agentModeDescription")
      : chatMode === "search_engine"
        ? t("chat.searchModeDescription")
        : chatMode === "temp_kb"
          ? t("chat.tempModeDescription")
          : t("chat.localModeDescription");

  /** 用途：负责 handleTempFileUpload 的界面或数据处理职责。 */
  async function handleTempFileUpload() {
    if (!selectedTempFile) {
      /** 用途：负责 setTempFileStatus 的界面或数据处理职责。 */
      setTempFileStatus(t("chat.chooseTempFile"));
      return;
    }

    /** 用途：负责 setIsUploadingTempFile 的界面或数据处理职责。 */
    setIsUploadingTempFile(true);
    /** 用途：负责 setTempFileStatus 的界面或数据处理职责。 */
    setTempFileStatus(t("chat.uploadingTemp", { name: selectedTempFile.name }));

    try {
      const response = await uploadTempFile(selectedTempFile);
      const nextTempKbId =
        response.temp_kb_id || response.temp_id || response.kb_name || null;

      if (response.error || !nextTempKbId) {
        /** 用途：负责 setTempFileStatus 的界面或数据处理职责。 */
        setTempFileStatus(response.error || t("chat.tempUploadMissing"));
        return;
      }

      /** 用途：负责 setTempKbId 的界面或数据处理职责。 */
      setTempKbId(nextTempKbId);
      /** 用途：负责 setTempFileName 的界面或数据处理职责。 */
      setTempFileName(selectedTempFile.name);
      /** 用途：负责 setTempFileStatus 的界面或数据处理职责。 */
      setTempFileStatus(
        /** 用途：负责 t 的界面或数据处理职责。 */
        t("chat.tempUploaded", {
          name: selectedTempFile.name,
          id: nextTempKbId
        })
      );
      /** 用途：负责 setSelectedTempFile 的界面或数据处理职责。 */
      setSelectedTempFile(null);
      if (tempFileInputRef.current) {
        tempFileInputRef.current.value = "";
      }
    } catch (uploadError) {
      /** 用途：负责 setTempFileStatus 的界面或数据处理职责。 */
      setTempFileStatus(
        uploadError instanceof Error ? uploadError.message : t("chat.tempUploadFailed")
      );
    } finally {
      /** 用途：负责 setIsUploadingTempFile 的界面或数据处理职责。 */
      setIsUploadingTempFile(false);
    }
  }

  /** 用途：负责 submitInput 的界面或数据处理职责。 */
  async function submitInput() {
    const value = input;
    /** 用途：负责 setInput 的界面或数据处理职责。 */
    setInput("");

    if (chatMode === "agent") {
      /** 用途：负责 setDetailsTab 的界面或数据处理职责。 */
      setDetailsTab("trace");
      await sendAgentMessage(value);
      return;
    }

    await sendMessage(value);
    /** 用途：负责 setDetailsTab 的界面或数据处理职责。 */
    setDetailsTab("sources");
  }

  /** 用途：负责 focusComposer 的界面或数据处理职责。 */
  function focusComposer() {
    window.setTimeout(() => {
      document.querySelector<HTMLTextAreaElement>(".chat-composer textarea")?.focus();
    }, 0);
  }

  /** 用途：负责 handleStartEmptyMode 的界面或数据处理职责。 */
  function handleStartEmptyMode(nextMode: ChatMode) {
    /** 用途：负责 setChatMode 的界面或数据处理职责。 */
    setChatMode(nextMode);
    if (nextMode === "temp_kb") {
      window.setTimeout(() => tempFileInputRef.current?.focus(), 0);
      return;
    }

    /** 用途：负责 focusComposer 的界面或数据处理职责。 */
    focusComposer();
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <ChatWorkspace
      activeModeDescription={activeModeDescription}
      activeModeLabel={activeModeLabel}
      agentError={agentError}
      chatMode={chatMode}
      chatModes={chatModes}
      conversationId={conversationId}
      detailsTab={detailsTab}
      disabledReason={disabledReason}
      error={error}
      hasMessages={hasMessages}
      input={input}
      isAgentRunning={isAgentRunning}
      isLoadingMessages={isLoadingMessages}
      isSending={isSending}
      isStreaming={isStreaming}
      isUploadingTempFile={isUploadingTempFile}
      kbName={kbName}
      messages={messages}
      onChangeDetailsTab={setDetailsTab}
      onChangeInput={setInput}
      onChangeKbName={setKbName}
      onChangeMode={setChatMode}
      onChangeSelectedTempFile={setSelectedTempFile}
      onOpenAssistantSources={messageId => {
        /** 用途：负责 setSelectedAssistantMessageId 的界面或数据处理职责。 */
        setSelectedAssistantMessageId(messageId);
        /** 用途：负责 setDetailsTab 的界面或数据处理职责。 */
        setDetailsTab("sources");
      }}
      onOpenModeGuide={onOpenModeGuide}
      onSelectAssistantMessage={setSelectedAssistantMessageId}
      onStartEmptyMode={handleStartEmptyMode}
      onSubmit={() => {
        void submitInput();
      }}
      onTempFileUpload={() => {
        void handleTempFileUpload();
      }}
      preferredMode={preferredMode}
      selectedAssistantMessageId={selectedAssistantMessageId}
      selectedTempFile={selectedTempFile}
      streamStatus={streamStatus}
      streamTokenText={streamTokenText}
      streamingMessage={streamingMessage}
      tempFileInputRef={tempFileInputRef}
      tempFileName={tempFileName}
      tempFileStatus={tempFileStatus}
      tempKbId={tempKbId}
      visibleAgentResult={visibleAgentResult}
    />
  );
}

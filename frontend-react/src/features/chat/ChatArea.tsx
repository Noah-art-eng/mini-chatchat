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
import { useNavigate } from "../../router";
import { listKnowledgeBases, switchKnowledgeBase } from "../../api/kb";

type ChatAreaProps = {
  onOpenModeGuide?: () => void;
  preferredMode?: "chat" | "agent";
};

const chatModes: ChatMode[] = ["local_kb", "search_engine", "temp_kb", "agent"];

/** 从历史消息 metadata 恢复 Agent 步骤和 trace，使刷新后的详情面板仍能展示上次执行过程。 */
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

/**
 * 连接聊天页面、共享会话状态和两种流式 Hook。
 * 普通模式进入 useChatStream，Agent 模式进入 useAgentRun，最后把统一状态交给 ChatWorkspace 渲染。
 */
export function ChatArea({
  onOpenModeGuide = () => undefined,
  preferredMode = "chat"
}: ChatAreaProps) {
  const { t } = useI18n();
  const navigate = useNavigate();
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
  const { error, isStreaming, sendMessage, stopGeneration } = useChatStream();
  const {
    agentResult,
    error: agentError,
    isRunning: isAgentRunning,
    sendAgentMessage,
    stopAgentRun,
    streamStatus,
    streamTokenText
  } = useAgentRun();
  const [knowledgeBaseNames, setKnowledgeBaseNames] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [detailsTab, setDetailsTab] = useState<DetailsTab>("sources");
  const [selectedTempFile, setSelectedTempFile] = useState<File | null>(null);
  const [isUploadingTempFile, setIsUploadingTempFile] = useState(false);
  const [tempFileStatus, setTempFileStatus] = useState<string | null>(null);
  const tempFileInputRef = useRef<HTMLInputElement | null>(null);
  const appliedPreferredModeRef = useRef<"chat" | "agent" | null>(null);

  useEffect(() => {
    if (appliedPreferredModeRef.current === preferredMode) return;
    appliedPreferredModeRef.current = preferredMode;

    if (preferredMode === "agent" && chatMode !== "agent") {
      setChatMode("agent");
    } else if (preferredMode === "chat" && chatMode === "agent") {
      setChatMode("local_kb");
    }
  }, [chatMode, preferredMode, setChatMode]);

  useEffect(() => {
    listKnowledgeBases()
      .then(result => setKnowledgeBaseNames(result.knowledge_bases.map(kb => kb.kb_name)))
      .catch(() => setKnowledgeBaseNames([]));
  }, []);

  function changeMode(nextMode: ChatMode) {
    setChatMode(nextMode);
    navigate(nextMode === "agent" ? "/agent" : "/chat");
  }

  async function changeKnowledgeBase(nextKbName: string) {
    const result = await switchKnowledgeBase(nextKbName);
    setKbName(result.current_kb);
  }

  useEffect(() => {
    if (chatMode !== "agent" && detailsTab === "trace") {
      setDetailsTab("sources");
    }

    if (chatMode === "agent" && detailsTab !== "trace") {
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

  /** 上传临时文件并保存后端返回的 temp_kb_id，随后 temp_kb 问答会携带该编号。 */
  async function handleTempFileUpload() {
    if (!selectedTempFile) {
      setTempFileStatus(t("chat.chooseTempFile"));
      return;
    }

    setIsUploadingTempFile(true);
    setTempFileStatus(t("chat.uploadingTemp", { name: selectedTempFile.name }));

    try {
      const response = await uploadTempFile(selectedTempFile);
      const nextTempKbId =
        response.temp_kb_id || response.temp_id || response.kb_name || null;

      if (response.error || !nextTempKbId) {
        setTempFileStatus(response.error || t("chat.tempUploadMissing"));
        return;
      }

      setTempKbId(nextTempKbId);
      setTempFileName(selectedTempFile.name);
      setTempFileStatus(
        t("chat.tempUploaded", {
          name: selectedTempFile.name,
          id: nextTempKbId
        })
      );
      setSelectedTempFile(null);
      if (tempFileInputRef.current) {
        tempFileInputRef.current.value = "";
      }
    } catch (uploadError) {
      setTempFileStatus(
        uploadError instanceof Error ? uploadError.message : t("chat.tempUploadFailed")
      );
    } finally {
      setIsUploadingTempFile(false);
    }
  }

  /** 根据当前模式把输入交给 RAG 或 Agent 流式 Hook。 */
  async function submitInput() {
    const value = input;
    setInput("");

    if (chatMode === "agent") {
      setDetailsTab("trace");
      await sendAgentMessage(value);
      return;
    }

    await sendMessage(value);
    setDetailsTab("sources");
  }

  function focusComposer() {
    window.setTimeout(() => {
      document.querySelector<HTMLTextAreaElement>(".chat-composer textarea")?.focus();
    }, 0);
  }

  function handleStartEmptyMode(nextMode: ChatMode) {
    setChatMode(nextMode);
    if (nextMode === "temp_kb") {
      window.setTimeout(() => tempFileInputRef.current?.focus(), 0);
      return;
    }

    focusComposer();
  }

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
      knowledgeBaseNames={knowledgeBaseNames}
      messages={messages}
      onChangeDetailsTab={setDetailsTab}
      onChangeInput={setInput}
      onChangeKbName={nextKbName => {
        void changeKnowledgeBase(nextKbName).catch(() => undefined);
      }}
      onChangeMode={changeMode}
      onChangeSelectedTempFile={setSelectedTempFile}
      onOpenAssistantSources={messageId => {
        setSelectedAssistantMessageId(messageId);
        setDetailsTab("sources");
      }}
      onOpenModeGuide={onOpenModeGuide}
      onSelectAssistantMessage={setSelectedAssistantMessageId}
      onStartEmptyMode={handleStartEmptyMode}
      onSubmit={() => {
        void submitInput();
      }}
      onStop={chatMode === "agent" ? stopAgentRun : stopGeneration}
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

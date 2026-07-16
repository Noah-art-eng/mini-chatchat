import { FormEvent, useMemo, useRef, useState } from "react";
import { AgentTracePanel } from "../../components/AgentTracePanel";
import { FeedbackControls } from "../../components/FeedbackControls";
import { uploadTempFile } from "../../api/chat";
import { useAgentRun } from "../../hooks/useAgentRun";
import { useChatStream } from "../../hooks/useChatStream";
import { useConversationStore } from "../../stores/conversationStore";
import type { AgentRunResponse } from "../../types/agent";
import type { ChatMode } from "../../types/chat";
import type { ChatMessage } from "../../types/conversation";

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

export function ChatArea() {
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
  const tempFileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedTempFile, setSelectedTempFile] = useState<File | null>(null);
  const [isUploadingTempFile, setIsUploadingTempFile] = useState(false);
  const [tempFileStatus, setTempFileStatus] = useState<string | null>(null);
  const persistedAgentResult = useMemo(() => {
    const selectedMessage = messages.find(
      message =>
        message.id === selectedAssistantMessageId &&
        message.role === "assistant" &&
        message.metadata?.agent
    );
    const latestAgentMessage = [...messages]
      .reverse()
      .find(
        message => message.role === "assistant" && message.metadata?.agent
      );

    return buildPersistedAgentResult(selectedMessage || latestAgentMessage);
  }, [messages, selectedAssistantMessageId]);

  function switchChatMode(nextMode: ChatMode) {
    setChatMode(nextMode);
  }

  async function handleTempFileUpload() {
    if (!selectedTempFile) {
      setTempFileStatus("Choose a temp file first.");
      return;
    }

    setIsUploadingTempFile(true);
    setTempFileStatus(`Uploading ${selectedTempFile.name}...`);

    try {
      const response = await uploadTempFile(selectedTempFile);
      const nextTempKbId =
        response.temp_kb_id || response.temp_id || response.kb_name || null;

      if (response.error || !nextTempKbId) {
        setTempFileStatus(response.error || "Temp upload did not return an id.");
        return;
      }

      setTempKbId(nextTempKbId);
      setTempFileName(selectedTempFile.name);
      setTempFileStatus(
        `${selectedTempFile.name} uploaded. temp_kb_id: ${nextTempKbId}`
      );
      setSelectedTempFile(null);
      if (tempFileInputRef.current) {
        tempFileInputRef.current.value = "";
      }
    } catch (uploadError) {
      setTempFileStatus(
        uploadError instanceof Error
          ? uploadError.message
          : "Temp upload failed."
      );
    } finally {
      setIsUploadingTempFile(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = input;
    setInput("");

    if (chatMode === "agent") {
      await sendAgentMessage(value);
      return;
    }

    await sendMessage(value);
  }

  const isSending = isStreaming || isAgentRunning;
  const shouldShowAgentTrace = chatMode === "agent" || Boolean(persistedAgentResult);

  return (
    <section className="chat-area" aria-label="Chat">
      <header className="chat-header">
        <div>
          <p className="eyebrow">
            {chatMode}
            {chatMode === "local_kb" ? ` · ${kbName}` : ""}
          </p>
          <h2>
            {conversationId
              ? `Conversation ${conversationId}`
              : "New Conversation"}
          </h2>
        </div>

        <div className="chat-controls">
          <div className="mode-toggle" aria-label="Chat mode">
            <button
              className={chatMode === "local_kb" ? "active" : ""}
              data-testid="chat-mode-local-kb"
              onClick={() => switchChatMode("local_kb")}
              type="button"
            >
              local_kb
            </button>
            <button
              className={chatMode === "search_engine" ? "active" : ""}
              data-testid="chat-mode-search-engine"
              onClick={() => switchChatMode("search_engine")}
              type="button"
            >
              search_engine
            </button>
            <button
              className={chatMode === "temp_kb" ? "active" : ""}
              data-testid="chat-mode-temp-kb"
              onClick={() => switchChatMode("temp_kb")}
              type="button"
            >
              temp_kb
            </button>
            <button
              className={chatMode === "agent" ? "active" : ""}
              data-testid="chat-mode-agent"
              onClick={() => switchChatMode("agent")}
              type="button"
            >
              agent
            </button>
          </div>

          <label>
            Mode
            <select
              onChange={event => {
                const value = event.target.value;
                if (
                  value === "local_kb" ||
                  value === "search_engine" ||
                  value === "temp_kb" ||
                  value === "agent"
                ) {
                  switchChatMode(value);
                }
              }}
              data-testid="chat-mode-select"
              value={chatMode}
            >
              <option value="local_kb">local_kb</option>
              <option value="search_engine">search_engine</option>
              <option value="temp_kb">temp_kb</option>
              <option value="agent">agent</option>
            </select>
          </label>

          <label>
            KB
            <input
              disabled={chatMode !== "local_kb" && chatMode !== "agent"}
              onChange={event => setKbName(event.target.value || "default")}
              value={kbName}
            />
          </label>
        </div>
      </header>

      {chatMode === "search_engine" && (
        <div
          className="mode-status"
          data-testid="search-engine-mode-status"
        >
          Web Search Mode
        </div>
      )}

      {chatMode === "temp_kb" && (
        <div className="temp-file-panel">
          <div className="mode-status" data-testid="temp-file-mode-status">
            Temp File Mode
          </div>
          <div className="temp-file-upload">
            <input
              accept=".txt,.pdf,.docx,.md,.csv"
              data-testid="temp-file-input"
              onChange={event => {
                setSelectedTempFile(event.target.files?.[0] || null);
              }}
              ref={tempFileInputRef}
              type="file"
            />
            <button
              data-testid="temp-file-upload-button"
              disabled={isUploadingTempFile || !selectedTempFile}
              onClick={() => {
                void handleTempFileUpload();
              }}
              type="button"
            >
              {isUploadingTempFile ? "Uploading" : "Upload Temp File"}
            </button>
          </div>
          <p className="temp-file-status" data-testid="temp-file-status">
            {tempFileStatus ||
              (tempKbId && tempFileName
                ? `${tempFileName} · temp_kb_id: ${tempKbId}`
                : "Upload a temp file before asking in temp_kb mode.")}
          </p>
        </div>
      )}

      {chatMode === "agent" && (
        <div className="mode-status" data-testid="agent-mode-status">
          Agent Mode · tools: calculator, current_time, kb_search, sqlite, filesystem, browser_read
        </div>
      )}

      <div className="message-list">
        {isLoadingMessages && <p className="muted">Loading messages...</p>}

        {!isLoadingMessages && messages.length === 0 && !streamingMessage && (
          <div className="empty-chat">
            <h3>Ask a question to start a conversation.</h3>
            <p>
              Phase 1 focuses on the React shell, conversation state, and the
              core chat surface.
            </p>
          </div>
        )}

        {messages.map((message, index) => (
          <article
            className={[
              "message",
              message.role,
              message.role === "assistant" &&
              message.id === selectedAssistantMessageId
                ? "selected"
                : ""
            ]
              .filter(Boolean)
              .join(" ")}
            key={message.id || index}
            onClick={() => {
              if (message.role === "assistant" && message.id) {
                setSelectedAssistantMessageId(message.id);
              }
            }}
          >
            <span>{message.role}</span>
            <p>{message.content}</p>

            {message.role === "assistant" && (
              <FeedbackControls
                feedbackScore={message.feedback_score}
                messageId={message.id}
              />
            )}
          </article>
        ))}

        {streamingMessage && (
          <article className="message assistant streaming">
            <span>assistant</span>
            <p>{streamingMessage}</p>
          </article>
        )}
      </div>

      {shouldShowAgentTrace && (
        <AgentTracePanel
          error={agentError}
          isRunning={isAgentRunning}
          result={agentResult || persistedAgentResult}
          streamStatus={streamStatus}
          streamTokenText={streamTokenText}
        />
      )}

      {error && chatMode !== "agent" && <p className="inline-error">{error}</p>}

      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          aria-label="Message"
          onChange={event => setInput(event.target.value)}
          placeholder="Ask Mini ChatChat..."
          value={input}
        />
        <button disabled={isSending || input.trim().length === 0} type="submit">
          {isSending ? "Sending" : "Send"}
        </button>
      </form>
    </section>
  );
}

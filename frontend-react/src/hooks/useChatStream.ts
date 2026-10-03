import { useEffect, useRef, useState } from "react";
import { readSSE, startKbChat } from "../api/chat";
import { useConversationStore } from "../stores/conversationStore";
import type { KBChatRequest } from "../types/chat";
import type { ChatMessage, Source } from "../types/conversation";

type ChatRun = {
  controller: AbortController;
  id: number;
  initialConversationId: number | null;
  serverConversationId?: number;
};

function isAbortError(error: unknown) {
  return error instanceof Error && error.name === "AbortError";
}

export function useChatStream() {
  /**
   * 管理一次 RAG 流式问答从发出请求到写回界面的完整过程。
   * Hook 会解析后端的 sources/token/error/done 事件，并用请求编号、会话归属和
   * AbortController 阻止旧请求在切换会话或开始新请求后继续修改当前界面。
   */
  const {
    appendStreamingMessage,
    chatMode,
    conversationId,
    kbName,
    messages,
    refreshConversations,
    setConversationId,
    setMessages,
    setSelectedAssistantMessageId,
    setSources,
    setStreamingMessage,
    tempKbId
  } = useConversationStore();
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeRunRef = useRef<ChatRun | null>(null);
  const conversationIdRef = useRef(conversationId);
  const nextRunIdRef = useRef(0);

  function isCurrentRun(run: ChatRun) {
    // 只有仍持有执行权、未取消，并且属于当前会话的请求才能更新界面。
    // 新会话第一次请求会由后端创建 conversation_id，因此也接受服务端刚返回的会话编号。
    const currentConversationId = conversationIdRef.current;
    return (
      activeRunRef.current?.id === run.id &&
      !run.controller.signal.aborted &&
      (currentConversationId === run.initialConversationId ||
        (run.serverConversationId !== undefined &&
          currentConversationId === run.serverConversationId))
    );
  }

  function abortRun(run: ChatRun) {
    if (activeRunRef.current?.id === run.id) {
      activeRunRef.current = null;
    }
    run.controller.abort();
  }

  function stopGeneration() {
    const run = activeRunRef.current;
    if (!run) return;
    abortRun(run);
    setIsStreaming(false);
  }

  useEffect(() => {
    // 切换会话会立即撤销旧流的界面写入权，避免迟到的 token、Sources 或错误串到新会话。
    conversationIdRef.current = conversationId;
    const run = activeRunRef.current;
    if (run && !isCurrentRun(run)) {
      abortRun(run);
      setError(null);
      setIsStreaming(false);
    }
  }, [conversationId]);

  useEffect(() => {
    return () => {
      const run = activeRunRef.current;
      if (run) abortRun(run);
    };
  }, []);

  async function sendMessage(query: string) {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    if (chatMode === "temp_kb" && !tempKbId) {
      setError("Please upload a temp file first.");
      return;
    }

    const previousRun = activeRunRef.current;
    // 同一个聊天工作区只允许最新请求继续更新状态；新请求开始前先取消旧请求。
    if (previousRun) abortRun(previousRun);

    const run: ChatRun = {
      controller: new AbortController(),
      id: ++nextRunIdRef.current,
      initialConversationId: conversationId
    };
    activeRunRef.current = run;

    setError(null);
    setSources([]);
    setSelectedAssistantMessageId(null);
    setStreamingMessage("");
    setMessages([
      ...messages,
      {
        role: "user",
        content: trimmedQuery
      }
    ]);
    setIsStreaming(true);

    let assistantText = "";
    let assistantMessageId: number | undefined;
    let currentSources: Source[] = [];

    try {
      const payload: KBChatRequest = {
        mode: chatMode,
        query: trimmedQuery,
        stream: true,
        conversation_id: conversationId,
        top_k: 3,
        score_threshold: 0.8,
        prompt_name: "default",
        rerank: false,
        rerank_top_n: 3
      };

      if (chatMode === "local_kb") {
        payload.kb_name = kbName;
      }

      if (chatMode === "temp_kb" && tempKbId) {
        payload.temp_kb_id = tempKbId;
      }

      const response = await startKbChat(payload, run.controller.signal);

      // 这里进入 api/chat.ts 的 SSE 解析器。每个事件回到当前回调后，先确认请求仍属于当前会话，
      // 再分别更新来源、增量回答、错误状态或最终消息编号。
      await readSSE(response, event => {
        if (!isCurrentRun(run)) return;

        if ("conversation_id" in event && event.conversation_id) {
          run.serverConversationId = event.conversation_id;
          setConversationId(event.conversation_id);
          localStorage.setItem(
            "mini-chatchat:lastConversationId",
            String(event.conversation_id)
          );
        }

        if (event.type === "sources") {
          currentSources = event.sources;
          setSources(event.sources);
        }

        if (event.type === "token") {
          assistantText += event.content;
          appendStreamingMessage(event.content);
        }

        if (event.type === "error") {
          setError(event.message);
          // 后端若已生成部分回答，会把同一段内容保存进数据库并标记 partial_response。
          // 此时保留界面已有文本，只记录失败状态，保证刷新前后的消息内容一致。
          const keepPartialAnswer =
            "partial_response" in event &&
            event.partial_response === true &&
            assistantText.length > 0;
          if (!keepPartialAnswer) {
            assistantText = event.message;
            setStreamingMessage(event.message);
          }
        }

        if (event.type === "done") {
          assistantMessageId = event.assistant_message_id;
          if (event.conversation_id) {
            setConversationId(event.conversation_id);
            localStorage.setItem(
              "mini-chatchat:lastConversationId",
              String(event.conversation_id)
            );
          }
        }
      }, run.controller.signal);

      if (!isCurrentRun(run)) return;

      // 流结束后才把临时累积的回答写入正式消息列表；过期请求会在上面的归属检查处退出。
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: assistantText || "No answer returned.",
        feedback_score: null,
        sources: currentSources
      };

      setMessages([
        ...messages,
        {
          role: "user",
          content: trimmedQuery
        },
        assistantMessage
      ]);
      if (assistantMessageId) {
        setSelectedAssistantMessageId(assistantMessageId);
      }
      setStreamingMessage("");
      await refreshConversations();
    } catch (chatError) {
      if (isAbortError(chatError) || !isCurrentRun(run)) return;

      const message =
        chatError instanceof Error ? chatError.message : "Chat failed.";
      setError(message);
      setStreamingMessage(message);
      setMessages([
        ...messages,
        {
          role: "user",
          content: trimmedQuery
        },
        {
          role: "assistant",
          content: message,
          sources: currentSources
        }
      ]);
      await refreshConversations();
    } finally {
      if (isCurrentRun(run)) {
        activeRunRef.current = null;
        setStreamingMessage("");
        setIsStreaming(false);
      }
    }
  }

  return {
    error,
    isStreaming,
    sendMessage,
    stopGeneration
  };
}

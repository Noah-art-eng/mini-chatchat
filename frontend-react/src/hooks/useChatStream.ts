import { useState } from "react";
import { readSSE, startKbChat } from "../api/chat";
import { useConversationStore } from "../stores/conversationStore";
import type { KBChatRequest } from "../types/chat";
import type { ChatMessage, Source } from "../types/conversation";

/** 用途：负责 useChatStream 的界面或数据处理职责。 */
export function useChatStream() {
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

  /** 用途：负责 sendMessage 的界面或数据处理职责。 */
  async function sendMessage(query: string) {
    const trimmedQuery = query.trim();
    if (!trimmedQuery || isStreaming) return;

    if (chatMode === "temp_kb" && !tempKbId) {
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError("Please upload a temp file first.");
      return;
    }

    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);
    /** 用途：负责 setSources 的界面或数据处理职责。 */
    setSources([]);
    /** 用途：负责 setSelectedAssistantMessageId 的界面或数据处理职责。 */
    setSelectedAssistantMessageId(null);
    /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
    setStreamingMessage("");
    /** 用途：负责 setMessages 的界面或数据处理职责。 */
    setMessages([
      ...messages,
      {
        role: "user",
        content: trimmedQuery
      }
    ]);
    /** 用途：负责 setIsStreaming 的界面或数据处理职责。 */
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

      const response = await startKbChat(payload);

      await readSSE(response, event => {
        if ("conversation_id" in event && event.conversation_id) {
          /** 用途：负责 setConversationId 的界面或数据处理职责。 */
          setConversationId(event.conversation_id);
          localStorage.setItem(
            "mini-chatchat:lastConversationId",
            /** 用途：负责 String 的界面或数据处理职责。 */
            String(event.conversation_id)
          );
        }

        if (event.type === "sources") {
          currentSources = event.sources;
          /** 用途：负责 setSources 的界面或数据处理职责。 */
          setSources(event.sources);
        }

        if (event.type === "token") {
          assistantText += event.content;
          /** 用途：负责 appendStreamingMessage 的界面或数据处理职责。 */
          appendStreamingMessage(event.content);
        }

        if (event.type === "error") {
          /** 用途：负责 setError 的界面或数据处理职责。 */
          setError(event.message);
          assistantText = event.message;
          /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
          setStreamingMessage(event.message);
        }

        if (event.type === "done") {
          assistantMessageId = event.assistant_message_id;
          if (event.conversation_id) {
            /** 用途：负责 setConversationId 的界面或数据处理职责。 */
            setConversationId(event.conversation_id);
            localStorage.setItem(
              "mini-chatchat:lastConversationId",
              /** 用途：负责 String 的界面或数据处理职责。 */
              String(event.conversation_id)
            );
          }
        }
      });

      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: assistantText || "No answer returned.",
        feedback_score: null,
        sources: currentSources
      };

      /** 用途：负责 setMessages 的界面或数据处理职责。 */
      setMessages([
        ...messages,
        {
          role: "user",
          content: trimmedQuery
        },
        assistantMessage
      ]);
      if (assistantMessageId) {
        /** 用途：负责 setSelectedAssistantMessageId 的界面或数据处理职责。 */
        setSelectedAssistantMessageId(assistantMessageId);
      }
      /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
      setStreamingMessage("");
      await refreshConversations();
    } catch (chatError) {
      const message =
        chatError instanceof Error ? chatError.message : "Chat failed.";
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(message);
      /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
      setStreamingMessage(message);
      /** 用途：负责 setMessages 的界面或数据处理职责。 */
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
      /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
      setStreamingMessage("");
      /** 用途：负责 setIsStreaming 的界面或数据处理职责。 */
      setIsStreaming(false);
    }
  }

  return {
    error,
    isStreaming,
    sendMessage
  };
}

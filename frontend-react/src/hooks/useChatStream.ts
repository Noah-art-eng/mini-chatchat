import { useState } from "react";
import { readSSE, startKbChat } from "../api/chat";
import { useConversationStore } from "../stores/conversationStore";
import type { KBChatRequest } from "../types/chat";
import type { ChatMessage, Source } from "../types/conversation";

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

  async function sendMessage(query: string) {
    const trimmedQuery = query.trim();
    if (!trimmedQuery || isStreaming) return;

    if (chatMode === "temp_kb" && !tempKbId) {
      setError("Please upload a temp file first.");
      return;
    }

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

      const response = await startKbChat(payload);

      await readSSE(response, event => {
        if ("conversation_id" in event && event.conversation_id) {
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
          assistantText = event.message;
          setStreamingMessage(event.message);
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
      });

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
      setStreamingMessage("");
      setIsStreaming(false);
    }
  }

  return {
    error,
    isStreaming,
    sendMessage
  };
}

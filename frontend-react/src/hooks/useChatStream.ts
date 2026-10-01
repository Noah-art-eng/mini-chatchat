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

  useEffect(() => {
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
      }, run.controller.signal);

      if (!isCurrentRun(run)) return;

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
    sendMessage
  };
}

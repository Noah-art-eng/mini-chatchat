import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import {
  deleteConversation,
  deleteConversations,
  getConversationMessages,
  listConversations,
  renameConversation
} from "../api/conversations";
import type { ChatMessage, Conversation } from "../types/conversation";
import type { ChatMode } from "../types/chat";
import type { Source } from "../types/conversation";

const LAST_CONVERSATION_KEY = "mini-chatchat:lastConversationId";

type ConversationState = {
  conversations: Conversation[];
  conversationId: number | null;
  messages: ChatMessage[];
  streamingMessage: string;
  sources: Source[];
  selectedAssistantMessageId: number | null;
  chatMode: ChatMode;
  kbName: string;
  tempFileName: string | null;
  tempKbId: string | null;
  isLoadingConversations: boolean;
  isLoadingMessages: boolean;
  setConversationId: (conversationId: number | null) => void;
  setMessages: (messages: ChatMessage[]) => void;
  setStreamingMessage: (message: string) => void;
  setSources: (sources: Source[]) => void;
  setSelectedAssistantMessageId: (messageId: number | null) => void;
  setChatMode: (chatMode: ChatMode) => void;
  setKbName: (kbName: string) => void;
  setTempFileName: (fileName: string | null) => void;
  setTempKbId: (tempKbId: string | null) => void;
  updateMessageFeedback: (messageId: number, score: number) => void;
  appendStreamingMessage: (token: string) => void;
  refreshConversations: () => Promise<void>;
  loadConversation: (conversation: Conversation) => Promise<void>;
  startNewConversation: () => void;
  renameConversationById: (
    conversationId: number,
    title: string
  ) => Promise<void>;
  deleteConversationById: (conversationId: number) => Promise<void>;
  deleteConversationsByIds: (conversationIds: number[]) => Promise<void>;
};

const ConversationContext = createContext<ConversationState | null>(null);

/**
 * 集中保存当前会话、消息、聊天模式和 Sources 等跨页面状态。
 * API Hook 通过这里写入流式结果，侧栏和聊天工作区读取同一份状态，避免各组件各自维护副本。
 */
export function ConversationProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingMessage, setStreamingMessage] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedAssistantMessageId, setSelectedAssistantMessageId] = useState<
    number | null
  >(null);
  const [chatMode, setChatMode] = useState<ChatMode>("local_kb");
  const [kbName, setKbName] = useState("default");
  const [tempFileName, setTempFileName] = useState<string | null>(null);
  const [tempKbId, setTempKbId] = useState<string | null>(null);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const messageRequestIdRef = useRef(0);

  const setActiveConversationId = useCallback((nextConversationId: number | null) => {
    setConversationId(nextConversationId);

    // 保存最后一次打开的会话，页面刷新后可以恢复；新会话尚无编号时清除旧记录。
    if (nextConversationId === null) {
      localStorage.removeItem(LAST_CONVERSATION_KEY);
      return;
    }

    localStorage.setItem(LAST_CONVERSATION_KEY, String(nextConversationId));
  }, []);

  const refreshConversations = useCallback(async () => {
    setIsLoadingConversations(true);
    try {
      const data = await listConversations();
      setConversations(data.conversations);
    } finally {
      setIsLoadingConversations(false);
    }
  }, []);

  const loadConversation = useCallback(async (conversation: Conversation) => {
    // 每次加载都取得新的请求编号。快速切换会话时，较早返回的响应不能覆盖后来选择的会话。
    const requestId = ++messageRequestIdRef.current;
    setConversationId(conversation.id);
    localStorage.setItem(LAST_CONVERSATION_KEY, String(conversation.id));
    setStreamingMessage("");
    setSources([]);
    setSelectedAssistantMessageId(null);
    setIsLoadingMessages(true);
    try {
      const data = await getConversationMessages(conversation.id);
      if (messageRequestIdRef.current !== requestId) return;
      setMessages(data.messages);
    } finally {
      if (messageRequestIdRef.current === requestId) {
        setIsLoadingMessages(false);
      }
    }
  }, []);

  const startNewConversation = useCallback(() => {
    // 新建会话会让正在加载的旧历史失效，同时清空只属于上一会话的消息和 Sources。
    messageRequestIdRef.current += 1;
    setConversationId(null);
    localStorage.removeItem(LAST_CONVERSATION_KEY);
    setMessages([]);
    setStreamingMessage("");
    setSources([]);
    setSelectedAssistantMessageId(null);
  }, []);

  const appendStreamingMessage = useCallback((token: string) => {
    setStreamingMessage(current => `${current}${token}`);
  }, []);

  const updateMessageFeedback = useCallback(
    (messageId: number, score: number) => {
      setMessages(currentMessages =>
        currentMessages.map(message =>
          message.id === messageId
            ? {
                ...message,
                feedback_score: score
              }
            : message
        )
      );
    },
    []
  );

  const renameConversationById = useCallback(
    async (targetConversationId: number, title: string) => {
      const result = await renameConversation(targetConversationId, title);

      setConversations(currentConversations =>
        currentConversations.map(conversation =>
          conversation.id === targetConversationId
            ? result.conversation
            : conversation
        )
      );

      await refreshConversations();
    },
    [refreshConversations]
  );

  const deleteConversationById = useCallback(
    async (targetConversationId: number) => {
      await deleteConversation(targetConversationId);
      await refreshConversations();

      if (targetConversationId === conversationId) {
        setConversationId(null);
        localStorage.removeItem(LAST_CONVERSATION_KEY);
        setMessages([]);
        setStreamingMessage("");
        setSources([]);
        setSelectedAssistantMessageId(null);
      }
    },
    [conversationId, refreshConversations]
  );

  const deleteConversationsByIds = useCallback(
    async (targetConversationIds: number[]) => {
      await deleteConversations(targetConversationIds);
      setConversationId(null);
      localStorage.removeItem(LAST_CONVERSATION_KEY);
      setMessages([]);
      setStreamingMessage("");
      setSources([]);
      setSelectedAssistantMessageId(null);
      await refreshConversations();
    },
    [refreshConversations]
  );

  useEffect(() => {
    let ignore = false;

    // Provider 初始化时先读取会话列表，再恢复上次会话；没有保存记录时打开最新可用会话。
    async function restoreLastConversation() {
      const data = await listConversations();
      if (ignore) return;

      setConversations(data.conversations);

      const savedId = Number(localStorage.getItem(LAST_CONVERSATION_KEY));
      const conversation =
        data.conversations.find(item => item.id === savedId) ||
        data.conversations[0];

      if (conversation) {
        await loadConversation(conversation);
      }
    }

    restoreLastConversation().catch(() => undefined);

    return () => {
      ignore = true;
    };
  }, [loadConversation]);

  const value = useMemo<ConversationState>(
    () => ({
      conversations,
      conversationId,
      messages,
      streamingMessage,
      sources,
      selectedAssistantMessageId,
      chatMode,
      kbName,
      tempFileName,
      tempKbId,
      isLoadingConversations,
      isLoadingMessages,
      setConversationId: setActiveConversationId,
      setMessages,
      setStreamingMessage,
      setSources,
      setSelectedAssistantMessageId,
      setChatMode,
      setKbName,
      setTempFileName,
      setTempKbId,
      updateMessageFeedback,
      appendStreamingMessage,
      refreshConversations,
      loadConversation,
      startNewConversation,
      renameConversationById,
      deleteConversationById,
      deleteConversationsByIds
    }),
    [
      appendStreamingMessage,
      chatMode,
      conversationId,
      conversations,
      isLoadingConversations,
      isLoadingMessages,
      kbName,
      loadConversation,
      messages,
      deleteConversationById,
      deleteConversationsByIds,
      refreshConversations,
      renameConversationById,
      selectedAssistantMessageId,
      setActiveConversationId,
      sources,
      startNewConversation,
      streamingMessage,
      tempFileName,
      tempKbId,
      updateMessageFeedback
    ]
  );

  return (
    <ConversationContext.Provider value={value}>
      {children}
    </ConversationContext.Provider>
  );
}

/** 取得 ConversationProvider 维护的共享会话状态。 */
export function useConversationStore() {
  const context = useContext(ConversationContext);

  if (!context) {
    throw new Error(
      "useConversationStore must be used within ConversationProvider."
    );
  }

  return context;
}

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
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

/** 用途：负责 ConversationProvider 的界面或数据处理职责。 */
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

  const setActiveConversationId = useCallback((nextConversationId: number | null) => {
    /** 用途：负责 setConversationId 的界面或数据处理职责。 */
    setConversationId(nextConversationId);

    if (nextConversationId === null) {
      localStorage.removeItem(LAST_CONVERSATION_KEY);
      return;
    }

    localStorage.setItem(LAST_CONVERSATION_KEY, String(nextConversationId));
  }, []);

  const refreshConversations = useCallback(async () => {
    /** 用途：负责 setIsLoadingConversations 的界面或数据处理职责。 */
    setIsLoadingConversations(true);
    try {
      const data = await listConversations();
      /** 用途：负责 setConversations 的界面或数据处理职责。 */
      setConversations(data.conversations);
    } finally {
      /** 用途：负责 setIsLoadingConversations 的界面或数据处理职责。 */
      setIsLoadingConversations(false);
    }
  }, []);

  const loadConversation = useCallback(async (conversation: Conversation) => {
    /** 用途：负责 setConversationId 的界面或数据处理职责。 */
    setConversationId(conversation.id);
    localStorage.setItem(LAST_CONVERSATION_KEY, String(conversation.id));
    /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
    setStreamingMessage("");
    /** 用途：负责 setSources 的界面或数据处理职责。 */
    setSources([]);
    /** 用途：负责 setSelectedAssistantMessageId 的界面或数据处理职责。 */
    setSelectedAssistantMessageId(null);
    /** 用途：负责 setIsLoadingMessages 的界面或数据处理职责。 */
    setIsLoadingMessages(true);
    try {
      const data = await getConversationMessages(conversation.id);
      /** 用途：负责 setMessages 的界面或数据处理职责。 */
      setMessages(data.messages);
    } finally {
      /** 用途：负责 setIsLoadingMessages 的界面或数据处理职责。 */
      setIsLoadingMessages(false);
    }
  }, []);

  const startNewConversation = useCallback(() => {
    /** 用途：负责 setConversationId 的界面或数据处理职责。 */
    setConversationId(null);
    localStorage.removeItem(LAST_CONVERSATION_KEY);
    /** 用途：负责 setMessages 的界面或数据处理职责。 */
    setMessages([]);
    /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
    setStreamingMessage("");
    /** 用途：负责 setSources 的界面或数据处理职责。 */
    setSources([]);
    /** 用途：负责 setSelectedAssistantMessageId 的界面或数据处理职责。 */
    setSelectedAssistantMessageId(null);
  }, []);

  const appendStreamingMessage = useCallback((token: string) => {
    /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
    setStreamingMessage(current => `${current}${token}`);
  }, []);

  const updateMessageFeedback = useCallback(
    (messageId: number, score: number) => {
      /** 用途：负责 setMessages 的界面或数据处理职责。 */
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
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (targetConversationId: number, title: string) => {
      const result = await renameConversation(targetConversationId, title);

      /** 用途：负责 setConversations 的界面或数据处理职责。 */
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
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (targetConversationId: number) => {
      await deleteConversation(targetConversationId);
      await refreshConversations();

      if (targetConversationId === conversationId) {
        /** 用途：负责 setConversationId 的界面或数据处理职责。 */
        setConversationId(null);
        localStorage.removeItem(LAST_CONVERSATION_KEY);
        /** 用途：负责 setMessages 的界面或数据处理职责。 */
        setMessages([]);
        /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
        setStreamingMessage("");
        /** 用途：负责 setSources 的界面或数据处理职责。 */
        setSources([]);
        /** 用途：负责 setSelectedAssistantMessageId 的界面或数据处理职责。 */
        setSelectedAssistantMessageId(null);
      }
    },
    [conversationId, refreshConversations]
  );

  const deleteConversationsByIds = useCallback(
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (targetConversationIds: number[]) => {
      await deleteConversations(targetConversationIds);
      /** 用途：负责 setConversationId 的界面或数据处理职责。 */
      setConversationId(null);
      localStorage.removeItem(LAST_CONVERSATION_KEY);
      /** 用途：负责 setMessages 的界面或数据处理职责。 */
      setMessages([]);
      /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
      setStreamingMessage("");
      /** 用途：负责 setSources 的界面或数据处理职责。 */
      setSources([]);
      /** 用途：负责 setSelectedAssistantMessageId 的界面或数据处理职责。 */
      setSelectedAssistantMessageId(null);
      await refreshConversations();
    },
    [refreshConversations]
  );

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    let ignore = false;

    /** 用途：负责 restoreLastConversation 的界面或数据处理职责。 */
    async function restoreLastConversation() {
      const data = await listConversations();
      if (ignore) return;

      /** 用途：负责 setConversations 的界面或数据处理职责。 */
      setConversations(data.conversations);

      const savedId = Number(localStorage.getItem(LAST_CONVERSATION_KEY));
      const conversation =
        data.conversations.find(item => item.id === savedId) ||
        data.conversations[0];

      if (conversation) {
        await loadConversation(conversation);
      }
    }

    /** 用途：负责 restoreLastConversation 的界面或数据处理职责。 */
    restoreLastConversation().catch(() => undefined);

    /** 用途：负责 return 的界面或数据处理职责。 */
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

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <ConversationContext.Provider value={value}>
      {children}
    </ConversationContext.Provider>
  );
}

/** 用途：负责 useConversationStore 的界面或数据处理职责。 */
export function useConversationStore() {
  const context = useContext(ConversationContext);

  if (!context) {
    throw new Error(
      "useConversationStore must be used within ConversationProvider."
    );
  }

  return context;
}

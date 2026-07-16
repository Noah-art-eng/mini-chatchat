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
};

const ConversationContext = createContext<ConversationState | null>(null);

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
    setConversationId(nextConversationId);

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
    setConversationId(conversation.id);
    localStorage.setItem(LAST_CONVERSATION_KEY, String(conversation.id));
    setStreamingMessage("");
    setSources([]);
    setSelectedAssistantMessageId(null);
    setIsLoadingMessages(true);
    try {
      const data = await getConversationMessages(conversation.id);
      setMessages(data.messages);
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  const startNewConversation = useCallback(() => {
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

  useEffect(() => {
    let ignore = false;

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

    restoreLastConversation().catch(console.error);

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
      deleteConversationById
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

export function useConversationStore() {
  const context = useContext(ConversationContext);

  if (!context) {
    throw new Error(
      "useConversationStore must be used within ConversationProvider."
    );
  }

  return context;
}

import {
  AssistantMessage,
  StreamingMessage,
  UserMessage
} from "./chat";
import type { ChatMessage } from "../types/conversation";
import { chatStyles } from "./chat/chatStyles";

type ChatMessageListProps = {
  messages: ChatMessage[];
  onOpenAssistantSources?: (messageId: number) => void;
  onSelectAssistantMessage: (messageId: number) => void;
  selectedAssistantMessageId: number | null;
  streamingMessage: string;
};

export function ChatMessageList({
  messages,
  onOpenAssistantSources,
  onSelectAssistantMessage,
  selectedAssistantMessageId,
  streamingMessage
}: ChatMessageListProps) {
  return (
    <div className={chatStyles.list} data-testid="message-list">
      {messages.map((message, index) => {
        if (message.role === "user") {
          return <UserMessage key={message.id || index} message={message} />;
        }

        const isSelected =
          message.role === "assistant" && message.id === selectedAssistantMessageId;
        const fallbackSelectId = message.id || 0;

        return (
          <AssistantMessage
            isSelected={isSelected}
            key={message.id || index}
            message={message}
            onOpenSources={() => {
              if (fallbackSelectId) {
                onOpenAssistantSources?.(fallbackSelectId);
              }
            }}
            onSelect={() => {
              if (fallbackSelectId) {
                onSelectAssistantMessage(fallbackSelectId);
              }
            }}
          />
        );
      })}

      {streamingMessage && <StreamingMessage content={streamingMessage} />}
    </div>
  );
}

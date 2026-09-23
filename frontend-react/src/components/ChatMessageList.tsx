import {
  AssistantMessage,
  StreamingMessage,
  UserMessage
} from "./chat";
import type { ChatMessage } from "../types/conversation";

type ChatMessageListProps = {
  messages: ChatMessage[];
  onOpenAssistantSources?: (messageId: number) => void;
  onSelectAssistantMessage: (messageId: number) => void;
  selectedAssistantMessageId: number | null;
  streamingMessage: string;
};

/** 用途：负责 ChatMessageList 的界面或数据处理职责。 */
export function ChatMessageList({
  messages,
  onOpenAssistantSources,
  onSelectAssistantMessage,
  selectedAssistantMessageId,
  streamingMessage
}: ChatMessageListProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="message-list" data-testid="message-list">
      {messages.map((message, index) => {
        if (message.role === "user") {
          return <UserMessage key={message.id || index} message={message} />;
        }

        const isSelected =
          message.role === "assistant" && message.id === selectedAssistantMessageId;
        const fallbackSelectId = message.id || 0;

        /** 用途：负责 return 的界面或数据处理职责。 */
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
                /** 用途：负责 onSelectAssistantMessage 的界面或数据处理职责。 */
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

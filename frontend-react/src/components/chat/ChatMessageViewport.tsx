import type { ReactNode } from "react";

type ChatMessageViewportProps = {
  children: ReactNode;
  hasMessages: boolean;
  isLoadingMessages: boolean;
  loadingLabel: string;
};

/** 用途：负责 ChatMessageViewport 的界面或数据处理职责。 */
export function ChatMessageViewport({
  children,
  hasMessages,
  isLoadingMessages,
  loadingLabel
}: ChatMessageViewportProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className={hasMessages ? "chat-thread has-messages" : "chat-thread"}>
      {isLoadingMessages && <p className="muted">{loadingLabel}</p>}
      {!isLoadingMessages && children}
    </div>
  );
}

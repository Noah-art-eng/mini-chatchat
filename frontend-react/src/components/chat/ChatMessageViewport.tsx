import type { ReactNode } from "react";
import { cx } from "../ui/utils";
import { chatStyles } from "./chatStyles";

type ChatMessageViewportProps = {
  children: ReactNode;
  hasMessages: boolean;
  isLoadingMessages: boolean;
  loadingLabel: string;
};

export function ChatMessageViewport({
  children,
  hasMessages,
  isLoadingMessages,
  loadingLabel
}: ChatMessageViewportProps) {
  return (
    <div className={cx(chatStyles.thread, hasMessages && chatStyles.threadWithMessages)}>
      {isLoadingMessages && <p className="muted">{loadingLabel}</p>}
      {!isLoadingMessages && children}
    </div>
  );
}

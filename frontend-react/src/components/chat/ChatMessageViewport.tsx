import type { ReactNode } from "react";
import { cx } from "../ui/utils";
import { chatStyles } from "./chatStyles";

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
    <div className={cx(chatStyles.thread, hasMessages && chatStyles.threadWithMessages)}>
      {isLoadingMessages && <p className="muted">{loadingLabel}</p>}
      {!isLoadingMessages && children}
    </div>
  );
}

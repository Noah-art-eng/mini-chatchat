import { MarkdownContent } from "./MarkdownContent";
import { Bot } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import { chatStyles } from "./chatStyles";

type StreamingMessageProps = {
  content: string;
};

/** 用途：负责 StreamingMessage 的界面或数据处理职责。 */
export function StreamingMessage({ content }: StreamingMessageProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className={`${chatStyles.message} ${chatStyles.assistantMessage} streaming`}>
      <div className={chatStyles.avatar} aria-hidden="true">
        <Icon icon={Bot} size="sm" tone="brand" />
      </div>
      <div className={`${chatStyles.content} ${chatStyles.streamingContent}`}>
        <div className={chatStyles.meta}>
          <span className={chatStyles.role}>{t("chat.messageRoleAssistant")}</span>
          <span className="thinking-label text-mc-caption text-mc-brand">{t("chat.thinking")}</span>
          <span className="typing-indicator">
            <span />
            <span />
            <span />
          </span>
        </div>
        {content ? (
          <MarkdownContent content={content} />
        ) : (
          <div className="skeleton-bubble" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        )}
      </div>
    </article>
  );
}

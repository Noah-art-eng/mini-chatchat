import { MarkdownContent } from "./MarkdownContent";
import { Bot } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";

type StreamingMessageProps = {
  content: string;
};

/** 用途：负责 StreamingMessage 的界面或数据处理职责。 */
export function StreamingMessage({ content }: StreamingMessageProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="message assistant streaming">
      <div className="message-avatar" aria-hidden="true">
        <Icon icon={Bot} size="sm" tone="brand" />
      </div>
      <div className="message-content">
        <div className="message-meta-row">
          <span className="message-role">{t("chat.messageRoleAssistant")}</span>
          <span className="thinking-label">{t("chat.thinking")}</span>
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

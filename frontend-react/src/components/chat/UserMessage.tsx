import { MarkdownContent } from "./MarkdownContent";
import { UserRound } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { ChatMessage } from "../../types/conversation";

type UserMessageProps = {
  message: ChatMessage;
};

/** 用途：负责 UserMessage 的界面或数据处理职责。 */
export function UserMessage({ message }: UserMessageProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="message user">
      <div className="message-avatar" aria-hidden="true">
        <Icon icon={UserRound} size="sm" tone="muted" />
      </div>
      <div className="message-content">
        <div className="message-meta-row">
          <span className="message-role">{t("chat.messageRoleUser")}</span>
        </div>
        <MarkdownContent content={message.content} />
      </div>
    </article>
  );
}

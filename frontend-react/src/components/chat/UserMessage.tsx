import { MarkdownContent } from "./MarkdownContent";
import { UserRound } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { ChatMessage } from "../../types/conversation";
import { chatStyles } from "./chatStyles";

type UserMessageProps = {
  message: ChatMessage;
};

export function UserMessage({ message }: UserMessageProps) {
  const { t } = useI18n();

  return (
    <article className={`${chatStyles.message} ${chatStyles.userMessage}`}>
      <div className={`${chatStyles.avatar} order-2`} aria-hidden="true">
        <Icon icon={UserRound} size="sm" tone="muted" />
      </div>
      <div className={`${chatStyles.content} ${chatStyles.userContent} order-1`}>
        <div className={chatStyles.meta}>
          <span className={chatStyles.role}>{t("chat.messageRoleUser")}</span>
        </div>
        <MarkdownContent content={message.content} />
      </div>
    </article>
  );
}

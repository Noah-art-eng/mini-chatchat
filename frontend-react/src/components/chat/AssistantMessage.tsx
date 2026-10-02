import { MarkdownContent } from "./MarkdownContent";
import { MessageActions } from "./MessageActions";
import { SourceReferenceList } from "./SourceReferenceList";
import { Bot } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { ChatMessage, Source } from "../../types/conversation";
import { cx } from "../ui/utils";
import { chatStyles } from "./chatStyles";

type AssistantMessageProps = {
  isSelected: boolean;
  message: ChatMessage;
  onOpenSources: () => void;
  onSelect: () => void;
};

/** 用途：负责 getMessageSources 的界面或数据处理职责。 */
function getMessageSources(message: ChatMessage): Source[] {
  return message.sources || message.metadata?.sources || [];
}

/** 用途：负责 AssistantMessage 的界面或数据处理职责。 */
export function AssistantMessage({
  isSelected,
  message,
  onOpenSources,
  onSelect
}: AssistantMessageProps) {
  const { t } = useI18n();
  const sources = getMessageSources(message);

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article
      className={cx("group", chatStyles.message, chatStyles.assistantMessage, isSelected && chatStyles.selectedMessage, message.metadata?.agent && "agent-message")}
      onClick={onSelect}
    >
      <div className={chatStyles.avatar} aria-hidden="true">
        <Icon icon={Bot} size="sm" tone={message.metadata?.agent ? "mcp" : "brand"} />
      </div>
      <div className={cx(chatStyles.content, isSelected && chatStyles.selectedContent)}>
        <div className={chatStyles.meta}>
          <span className={chatStyles.role}>
            {message.metadata?.agent ? t("nav.agent") : t("chat.messageRoleAssistant")}
          </span>
          <span className={chatStyles.hint}>
            {message.metadata?.agent
              ? t("agent.trace")
              : sources.length > 0
                ? t("sources.messageSources")
                : t("sources.missing")}
          </span>
        </div>
        <MarkdownContent content={message.content} />
        {!message.metadata?.agent && (
          <SourceReferenceList onOpenSources={onOpenSources} sources={sources} />
        )}
        <MessageActions
          content={message.content}
          feedbackScore={message.feedback_score}
          messageId={message.id}
        />
      </div>
    </article>
  );
}

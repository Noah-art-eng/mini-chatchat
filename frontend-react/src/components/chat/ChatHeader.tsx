import { useI18n } from "../../i18n";
import type { ChatMode } from "../../types/chat";
import { chatStyles } from "./chatStyles";

type ChatHeaderProps = {
  activeModeDescription: string;
  activeModeLabel: string;
  chatMode: ChatMode;
  conversationId: number | null;
  kbName: string;
  preferredMode: "chat" | "agent";
  tempFileName: string | null;
};

export function ChatHeader({
  activeModeDescription,
  activeModeLabel,
  chatMode,
  conversationId,
  kbName,
  preferredMode,
  tempFileName
}: ChatHeaderProps) {
  const { t } = useI18n();

  return (
    <header className={chatStyles.header}>
      <div>
        <p className="eyebrow">
          {conversationId
            ? `${t("chat.conversation")} ${conversationId}`
            : t("chat.newConversation")}
        </p>
        <h1 className={chatStyles.heroTitle}>{preferredMode === "agent" ? t("chat.agentTitle") : t("chat.title")}</h1>
        <p className={chatStyles.intro}>{activeModeDescription}</p>
      </div>
      <div className={chatStyles.heroStatus}>
        <span>{t("chat.activeWorkspace")}</span>
        <strong>{activeModeLabel}</strong>
        <small>
          {chatMode === "search_engine"
            ? t("chat.webEvidence")
            : chatMode === "agent"
              ? t("chat.toolReasoning")
              : chatMode === "temp_kb"
                ? tempFileName || t("chat.noTempFile")
                : kbName}
        </small>
      </div>
    </header>
  );
}

import { useI18n } from "../../i18n";
import type { ChatMode } from "../../types/chat";

type ChatHeaderProps = {
  activeModeDescription: string;
  activeModeLabel: string;
  chatMode: ChatMode;
  conversationId: number | null;
  kbName: string;
  preferredMode: "chat" | "agent";
  tempFileName: string | null;
};

/** 用途：负责 ChatHeader 的界面或数据处理职责。 */
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

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <header className="chat-header product-hero">
      <div>
        <p className="eyebrow">
          {conversationId
            ? `${t("chat.conversation")} ${conversationId}`
            : t("chat.newConversation")}
        </p>
        <h1>{preferredMode === "agent" ? t("chat.agentTitle") : t("chat.title")}</h1>
        <p className="page-intro">{activeModeDescription}</p>
      </div>
      <div className="hero-status-card">
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

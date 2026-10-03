import { useState } from "react";
import { FeedbackControls } from "../FeedbackControls";
import { useToast } from "../ui";
import { useI18n } from "../../i18n";
import { chatStyles } from "./chatStyles";

type MessageActionsProps = {
  content: string;
  feedbackScore?: number | null;
  messageId?: number;
};

export function MessageActions({
  content,
  feedbackScore,
  messageId
}: MessageActionsProps) {
  const { t } = useI18n();
  const { showToast } = useToast();
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  async function copyMessage() {
    try {
      await navigator.clipboard.writeText(content);
      setCopyStatus(t("chat.copied"));
      showToast({ message: t("chat.copied"), variant: "success" });
      window.setTimeout(() => setCopyStatus(null), 1400);
    } catch (error) {
      console.error(error);
      setCopyStatus(t("chat.copyFailed"));
      showToast({ message: t("chat.copyFailed"), variant: "error" });
    }
  }

  return (
    <div
      className={chatStyles.actions}
      onClick={event => {
        event.stopPropagation();
      }}
    >
      <button onClick={() => void copyMessage()} type="button">
        {t("chat.copy")}
      </button>
      <FeedbackControls feedbackScore={feedbackScore} messageId={messageId} />
      {copyStatus && <span>{copyStatus}</span>}
    </div>
  );
}

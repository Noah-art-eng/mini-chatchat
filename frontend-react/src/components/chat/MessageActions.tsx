import { useState } from "react";
import { FeedbackControls } from "../FeedbackControls";
import { useToast } from "../ui";
import { useI18n } from "../../i18n";

type MessageActionsProps = {
  content: string;
  feedbackScore?: number | null;
  messageId?: number;
};

/** 用途：负责 MessageActions 的界面或数据处理职责。 */
export function MessageActions({
  content,
  feedbackScore,
  messageId
}: MessageActionsProps) {
  const { t } = useI18n();
  const { showToast } = useToast();
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  /** 用途：负责 copyMessage 的界面或数据处理职责。 */
  async function copyMessage() {
    try {
      await navigator.clipboard.writeText(content);
      /** 用途：负责 setCopyStatus 的界面或数据处理职责。 */
      setCopyStatus(t("chat.copied"));
      /** 用途：负责 showToast 的界面或数据处理职责。 */
      showToast({ message: t("chat.copied"), variant: "success" });
      window.setTimeout(() => setCopyStatus(null), 1400);
    } catch (error) {
      console.error(error);
      /** 用途：负责 setCopyStatus 的界面或数据处理职责。 */
      setCopyStatus(t("chat.copyFailed"));
      /** 用途：负责 showToast 的界面或数据处理职责。 */
      showToast({ message: t("chat.copyFailed"), variant: "error" });
    }
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div
      className="message-actions"
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

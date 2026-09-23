import { useState } from "react";
import { sendMessageFeedback } from "../api/feedback";
import { useI18n } from "../i18n";
import { useConversationStore } from "../stores/conversationStore";
import { useToast } from "./ui";

type FeedbackControlsProps = {
  messageId?: number;
  feedbackScore?: number | null;
};

/** 用途：负责 FeedbackControls 的界面或数据处理职责。 */
export function FeedbackControls({
  messageId,
  feedbackScore
}: FeedbackControlsProps) {
  const { t } = useI18n();
  const { showToast } = useToast();
  const { updateMessageFeedback } = useConversationStore();
  const [isSaving, setIsSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(
    feedbackScore === 1
      ? t("feedback.liked")
      : feedbackScore === -1
        ? t("feedback.disliked")
        : null
  );

  /** 用途：负责 submitFeedback 的界面或数据处理职责。 */
  async function submitFeedback(score: 1 | -1) {
    if (!messageId || isSaving) return;

    const reason =
      score === -1
        ? window.prompt(t("feedback.reasonPrompt")) || null
        : null;

    /** 用途：负责 setIsSaving 的界面或数据处理职责。 */
    setIsSaving(true);
    try {
      await sendMessageFeedback(messageId, score, reason);
      /** 用途：负责 updateMessageFeedback 的界面或数据处理职责。 */
      updateMessageFeedback(messageId, score);
      /** 用途：负责 setStatus 的界面或数据处理职责。 */
      setStatus(score === 1 ? t("feedback.liked") : t("feedback.disliked"));
      /** 用途：负责 showToast 的界面或数据处理职责。 */
      showToast({
        message: score === 1 ? t("feedback.liked") : t("feedback.disliked"),
        variant: "success"
      });
    } catch (error) {
      console.error(error);
      /** 用途：负责 setStatus 的界面或数据处理职责。 */
      setStatus(t("feedback.failed"));
      /** 用途：负责 showToast 的界面或数据处理职责。 */
      showToast({ message: t("feedback.failed"), variant: "error" });
    } finally {
      /** 用途：负责 setIsSaving 的界面或数据处理职责。 */
      setIsSaving(false);
    }
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="feedback-controls">
      <button
        disabled={!messageId || isSaving}
        onClick={event => {
          event.stopPropagation();
          void submitFeedback(1);
        }}
        type="button"
      >
        {t("feedback.like")}
      </button>
      <button
        disabled={!messageId || isSaving}
        onClick={event => {
          event.stopPropagation();
          void submitFeedback(-1);
        }}
        type="button"
      >
        {t("feedback.dislike")}
      </button>
      <span>
        {status ||
          (messageId
            ? t("feedback.empty")
            : t("feedback.unavailable"))}
      </span>
    </div>
  );
}

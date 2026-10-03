import { useState } from "react";
import { sendMessageFeedback } from "../api/feedback";
import { useI18n } from "../i18n";
import { useConversationStore } from "../stores/conversationStore";
import { useToast } from "./ui";
import { chatStyles } from "./chat/chatStyles";

type FeedbackControlsProps = {
  messageId?: number;
  feedbackScore?: number | null;
};

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

  async function submitFeedback(score: 1 | -1) {
    if (!messageId || isSaving) return;

    const reason =
      score === -1
        ? window.prompt(t("feedback.reasonPrompt")) || null
        : null;

    setIsSaving(true);
    try {
      await sendMessageFeedback(messageId, score, reason);
      updateMessageFeedback(messageId, score);
      setStatus(score === 1 ? t("feedback.liked") : t("feedback.disliked"));
      showToast({
        message: score === 1 ? t("feedback.liked") : t("feedback.disliked"),
        variant: "success"
      });
    } catch (error) {
      console.error(error);
      setStatus(t("feedback.failed"));
      showToast({ message: t("feedback.failed"), variant: "error" });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className={chatStyles.feedback}>
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

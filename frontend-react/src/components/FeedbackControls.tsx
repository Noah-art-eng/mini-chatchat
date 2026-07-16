import { useState } from "react";
import { sendMessageFeedback } from "../api/feedback";
import { useConversationStore } from "../stores/conversationStore";

type FeedbackControlsProps = {
  messageId?: number;
  feedbackScore?: number | null;
};

export function FeedbackControls({
  messageId,
  feedbackScore
}: FeedbackControlsProps) {
  const { updateMessageFeedback } = useConversationStore();
  const [isSaving, setIsSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(
    feedbackScore === 1
      ? "Liked"
      : feedbackScore === -1
        ? "Disliked"
        : null
  );

  async function submitFeedback(score: 1 | -1) {
    if (!messageId || isSaving) return;

    const reason =
      score === -1
        ? window.prompt("Why was this answer not helpful?") || null
        : null;

    setIsSaving(true);
    try {
      await sendMessageFeedback(messageId, score, reason);
      updateMessageFeedback(messageId, score);
      setStatus(score === 1 ? "Liked" : "Disliked");
    } catch (error) {
      console.error(error);
      setStatus("Feedback failed");
    } finally {
      setIsSaving(false);
    }
  }

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
        Like
      </button>
      <button
        disabled={!messageId || isSaving}
        onClick={event => {
          event.stopPropagation();
          void submitFeedback(-1);
        }}
        type="button"
      >
        Dislike
      </button>
      <span>
        {status ||
          (messageId
            ? "No feedback yet"
            : "Feedback unavailable for this message")}
      </span>
    </div>
  );
}

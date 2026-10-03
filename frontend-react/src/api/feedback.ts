import { requestJson } from "./client";

export async function sendMessageFeedback(
  messageId: number,
  score: 1 | -1,
  reason: string | null = null
) {
  return requestJson<{
    message: string;
    message_id: number;
    feedback_score: number;
    feedback_reason: string | null;
  }>("/chat/feedback", {
    method: "POST",
    body: JSON.stringify({
      message_id: messageId,
      score,
      reason
    })
  });
}

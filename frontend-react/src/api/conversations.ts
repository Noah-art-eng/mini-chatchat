import { requestJson } from "./client";
import type { ChatMessage, Conversation } from "../types/conversation";

export async function listConversations() {
  return requestJson<{ conversations: Conversation[] }>("/conversations");
}

export async function getConversationMessages(conversationId: number) {
  return requestJson<{
    conversation_id: number;
    messages: ChatMessage[];
  }>(`/conversations/${conversationId}/messages`);
}

export async function renameConversation(
  conversationId: number,
  title: string
) {
  return requestJson<{ conversation: Conversation }>(
    `/conversations/${conversationId}`,
    {
      method: "PATCH",
      body: JSON.stringify({
        title
      })
    }
  );
}

export async function deleteConversation(conversationId: number) {
  return requestJson<{
    message: string;
    conversation_id: number;
  }>(`/conversations/${conversationId}`, {
    method: "DELETE"
  });
}

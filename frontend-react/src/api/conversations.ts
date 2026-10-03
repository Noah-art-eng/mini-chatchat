import { authFetch, requestJson } from "./client";
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

export async function deleteConversations(conversationIds: number[]) {
  const results: Array<{
    conversation_id: number;
    deleted: boolean;
    missing: boolean;
  }> = [];

  for (const conversationId of conversationIds) {
    const response = await authFetch(`/conversations/${conversationId}`, {
      method: "DELETE"
    });

    if (response.status === 404) {
      results.push({
        conversation_id: conversationId,
        deleted: false,
        missing: true
      });
      continue;
    }

    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    results.push({
      conversation_id: conversationId,
      deleted: true,
      missing: false
    });
  }

  return { results };
}

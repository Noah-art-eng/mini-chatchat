import { authFetch, requestJson } from "./client";
import type { ChatMessage, Conversation } from "../types/conversation";

/** 用途：负责 listConversations 的界面或数据处理职责。 */
export async function listConversations() {
  return requestJson<{ conversations: Conversation[] }>("/conversations");
}

/** 用途：负责 getConversationMessages 的界面或数据处理职责。 */
export async function getConversationMessages(conversationId: number) {
  return requestJson<{
    conversation_id: number;
    messages: ChatMessage[];
  }>(`/conversations/${conversationId}/messages`);
}

/** 用途：负责 renameConversation 的界面或数据处理职责。 */
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

/** 用途：负责 deleteConversation 的界面或数据处理职责。 */
export async function deleteConversation(conversationId: number) {
  return requestJson<{
    message: string;
    conversation_id: number;
  }>(`/conversations/${conversationId}`, {
    method: "DELETE"
  });
}

/** 用途：负责 deleteConversations 的界面或数据处理职责。 */
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

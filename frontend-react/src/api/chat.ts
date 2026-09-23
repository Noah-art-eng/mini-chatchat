import { authFetch } from "./client";
import type { KBChatRequest, StreamEvent } from "../types/chat";
import type { Source } from "../types/conversation";

/** 用途：负责 startKbChat 的界面或数据处理职责。 */
export async function startKbChat(request: KBChatRequest) {
  const response = await authFetch("/kb_chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(request)
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status}`);
  }

  return response;
}

/** 用途：负责 debugKbChat 的界面或数据处理职责。 */
export async function debugKbChat(request: KBChatRequest) {
  const response = await authFetch("/kb_chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(request)
  });

  if (!response.ok) {
    throw new Error(`Debug search failed: ${response.status}`);
  }

  return response.json() as Promise<{
    answer?: string;
    docs?: Source[];
    error?: string;
    results?: Source[];
    sources?: Source[];
    type?: string;
  }>;
}

/** 用途：负责 uploadTempFile 的界面或数据处理职责。 */
export async function uploadTempFile(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("chunk_size", "300");
  formData.append("chunk_overlap", "50");

  const response = await authFetch("/temp_upload", {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(`Temp upload failed: ${response.status}`);
  }

  return response.json() as Promise<{
    error?: string;
    kb_name?: string;
    message?: string;
    temp_id?: string;
    temp_kb_id?: string;
  }>;
}

/** 用途：负责 readSSE 的界面或数据处理职责。 */
export async function readSSE(
  response: Response,
  onEvent: (event: StreamEvent) => void
) {
  if (!response.body) {
    throw new Error("Streaming response body is not available.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  /** 用途：负责 parseEvent 的界面或数据处理职责。 */
  function parseEvent(rawEvent: string) {
    const data = rawEvent
      .split("\n")
      .filter(line => line.startsWith("data:"))
      .map(line => line.replace(/^data:\s?/, ""))
      .join("\n")
      .trim();

    if (!data || data === "[DONE]") return;
    /** 用途：负责 onEvent 的界面或数据处理职责。 */
    onEvent(JSON.parse(data) as StreamEvent);
  }

  try {
    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        buffer += decoder.decode();
        buffer
          .replace(/\r\n/g, "\n")
          .split("\n\n")
          .filter(Boolean)
          .forEach(parseEvent);
        return;
      }

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.replace(/\r\n/g, "\n").split("\n\n");
      buffer = parts.pop() || "";
      parts.filter(Boolean).forEach(parseEvent);
    }
  } finally {
    reader.releaseLock();
  }
}

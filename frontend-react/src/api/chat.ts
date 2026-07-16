import { API_BASE } from "./client";
import type { KBChatRequest, StreamEvent } from "../types/chat";
import type { Source } from "../types/conversation";

export async function startKbChat(request: KBChatRequest) {
  const response = await fetch(`${API_BASE}/kb_chat`, {
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

export async function debugKbChat(request: KBChatRequest) {
  const response = await fetch(`${API_BASE}/kb_chat`, {
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

export async function uploadTempFile(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("chunk_size", "300");
  formData.append("chunk_overlap", "50");

  const response = await fetch(`${API_BASE}/temp_upload`, {
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

  function parseEvent(rawEvent: string) {
    const data = rawEvent
      .split("\n")
      .filter(line => line.startsWith("data:"))
      .map(line => line.replace(/^data:\s?/, ""))
      .join("\n")
      .trim();

    if (!data || data === "[DONE]") return;
    onEvent(JSON.parse(data) as StreamEvent);
  }

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
}

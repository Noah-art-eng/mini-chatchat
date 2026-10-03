import { authFetch } from "./client";
import type { KBChatRequest, StreamEvent } from "../types/chat";
import type { Source } from "../types/conversation";

/** 向后端 /kb_chat 发起 RAG 请求，响应体随后交给 readSSE() 按事件读取。 */
export async function startKbChat(request: KBChatRequest, signal?: AbortSignal) {
  const response = await authFetch("/kb_chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(request),
    signal
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status}`);
  }

  return response;
}

/** 以非流式方式请求同一 RAG 入口，供检索调试界面查看完整结果。 */
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

/** 上传临时问答文件并取得 temp_kb_id，后续 temp_kb 模式用该编号定位隔离索引。 */
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

/**
 * 把 /kb_chat 返回的字节流按 SSE 空行边界拆成事件。
 * 解析后的 sources/token/error/done 交回 useChatStream；AbortSignal 会同时停止网络读取。
 */
export async function readSSE(
  response: Response,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
) {
  if (!response.body) {
    throw new Error("Streaming response body is not available.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const cancelReader = () => {
    void reader.cancel().catch(() => undefined);
  };

  signal?.throwIfAborted();
  signal?.addEventListener("abort", cancelReader, { once: true });

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

  try {
    while (true) {
      signal?.throwIfAborted();
      const { value, done } = await reader.read();
      signal?.throwIfAborted();

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
    signal?.removeEventListener("abort", cancelReader);
    reader.releaseLock();
  }
}

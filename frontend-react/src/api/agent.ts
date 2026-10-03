import { authFetch, requestJson } from "./client";
import type {
  AgentRunRequest,
  AgentRunResponse,
  AgentStreamEvent
} from "../types/agent";

/** 调用单步 Agent，等待完整 JSON 结果。 */
export function runAgent(request: AgentRunRequest) {
  return requestJson<AgentRunResponse>("/agent/run", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

/** 调用多步 Agent，等待完整 JSON 结果。 */
export function runAgentMulti(request: AgentRunRequest) {
  return requestJson<AgentRunResponse>("/agent/run_multi", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

/** 调用带计划的 Agent，等待完整 JSON 结果。 */
export function runAgentPlan(request: AgentRunRequest) {
  return requestJson<AgentRunResponse>("/agent/plan_run", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

/**
 * 调用 planner Agent 的 SSE 接口，把规划、工具执行、回答和完成事件交回 useAgentRun。
 * AbortSignal 用于 Stop 和会话切换，取消后不再继续读取旧任务事件。
 */
export async function runAgentPlanStream(
  request: AgentRunRequest,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal
) {
  const response = await authFetch("/agent/plan_run_stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(request),
    signal
  });

  if (!response.ok || !response.body) {
    throw new Error(`Agent stream failed with HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const cancelReader = () => {
    void reader.cancel().catch(() => undefined);
  };

  signal?.throwIfAborted();
  signal?.addEventListener("abort", cancelReader, { once: true });

  try {
    while (true) {
      signal?.throwIfAborted();
      const { done, value } = await reader.read();
      signal?.throwIfAborted();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";

      for (const chunk of chunks) {
        const dataLine = chunk
          .split("\n")
          .find(line => line.startsWith("data:"));

        if (!dataLine) continue;

        const payload = dataLine.replace(/^data:\s*/, "");
        onEvent(JSON.parse(payload) as AgentStreamEvent);
      }
    }
  } finally {
    signal?.removeEventListener("abort", cancelReader);
    reader.releaseLock();
  }
}

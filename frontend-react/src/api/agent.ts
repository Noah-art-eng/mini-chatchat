import { authFetch, requestJson } from "./client";
import type {
  AgentRunRequest,
  AgentRunResponse,
  AgentStreamEvent
} from "../types/agent";

/** 用途：负责 runAgent 的界面或数据处理职责。 */
export function runAgent(request: AgentRunRequest) {
  return requestJson<AgentRunResponse>("/agent/run", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

/** 用途：负责 runAgentMulti 的界面或数据处理职责。 */
export function runAgentMulti(request: AgentRunRequest) {
  return requestJson<AgentRunResponse>("/agent/run_multi", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

/** 用途：负责 runAgentPlan 的界面或数据处理职责。 */
export function runAgentPlan(request: AgentRunRequest) {
  return requestJson<AgentRunResponse>("/agent/plan_run", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

/** 用途：负责 runAgentPlanStream 的界面或数据处理职责。 */
export async function runAgentPlanStream(
  request: AgentRunRequest,
  onEvent: (event: AgentStreamEvent) => void
) {
  const response = await authFetch("/agent/plan_run_stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(request)
  });

  if (!response.ok || !response.body) {
    throw new Error(`Agent stream failed with HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
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
        /** 用途：负责 onEvent 的界面或数据处理职责。 */
        onEvent(JSON.parse(payload) as AgentStreamEvent);
      }
    }
  } finally {
    reader.releaseLock();
  }
}

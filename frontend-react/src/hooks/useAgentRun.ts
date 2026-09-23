import { useState } from "react";
import { runAgentPlanStream } from "../api/agent";
import { useConversationStore } from "../stores/conversationStore";
import type {
  AgentRunResponse,
  AgentStep,
  AgentStreamEvent
} from "../types/agent";

const AGENT_TOOLS = [
  "calculator",
  "current_time",
  "kb_search",
  "sqlite_readonly_query",
  "filesystem_readonly_read",
  "browser_read",
  "browser_search"
];

/** 用途：负责 useAgentRun 的界面或数据处理职责。 */
export function useAgentRun() {
  const {
    conversationId,
    kbName,
    messages,
    refreshConversations,
    setConversationId,
    setMessages,
    setStreamingMessage
  } = useConversationStore();
  const [agentResult, setAgentResult] = useState<AgentRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);
  const [streamTokenText, setStreamTokenText] = useState("");

  /** 用途：负责 upsertStep 的界面或数据处理职责。 */
  function upsertStep(steps: AgentStep[] | undefined, nextStep: AgentStep) {
    const current = steps || [];
    const index = current.findIndex(step => step.step === nextStep.step);

    if (index === -1) return [...current, nextStep];

    return current.map(step =>
      step.step === nextStep.step ? { ...step, ...nextStep } : step
    );
  }

  /** 用途：负责 applyStreamEvent 的界面或数据处理职责。 */
  function applyStreamEvent(event: AgentStreamEvent) {
    if (event.type === "planning") {
      /** 用途：负责 setStreamStatus 的界面或数据处理职责。 */
      setStreamStatus("Planning");
      /** 用途：负责 setAgentResult 的界面或数据处理职责。 */
      setAgentResult({
        answer: "",
        planner: event.planner,
        steps: [],
        trace: [{ event: "planning" }],
        tool_count: 0,
        error: null
      });
      return;
    }

    if (event.type === "step_start") {
      /** 用途：负责 setStreamStatus 的界面或数据处理职责。 */
      setStreamStatus(`Step ${event.step}`);
      /** 用途：负责 setAgentResult 的界面或数据处理职责。 */
      setAgentResult(current => ({
        answer: current?.answer || "",
        planner: current?.planner || null,
        steps: current?.steps || [],
        trace: [
          ...(current?.trace || []),
          { event: "step_start", step: event.step }
        ],
        tool_count: current?.tool_count || 0,
        error: null
      }));
      return;
    }

    if (event.type === "tool_call") {
      /** 用途：负责 setStreamStatus 的界面或数据处理职责。 */
      setStreamStatus("Tool Call");
      /** 用途：负责 setAgentResult 的界面或数据处理职责。 */
      setAgentResult(current => ({
        answer: current?.answer || "",
        planner: current?.planner || null,
        steps: current?.steps || [],
        trace: [
          ...(current?.trace || []),
          {
            event: "tool_call",
            step: event.step,
            tool: event.tool_call.tool,
            tool_call: event.tool_call
          }
        ],
        tool_call: event.tool_call,
        tool_count: current?.tool_count || 0,
        error: null
      }));
      return;
    }

    if (event.type === "tool_result") {
      /** 用途：负责 setStreamStatus 的界面或数据处理职责。 */
      setStreamStatus("Tool Result");
      /** 用途：负责 setAgentResult 的界面或数据处理职责。 */
      setAgentResult(current => {
        const toolCall =
          current?.tool_call || {
            tool: event.tool || "unknown",
            arguments: {},
            reason: ""
          };
        const nextStep = {
          step: event.step,
          tool_call: toolCall,
          tool_result: event.tool_result,
          observation: event.observation
        };

        return {
          answer: current?.answer || "",
          planner: current?.planner || null,
          steps: upsertStep(current?.steps, nextStep),
          trace: [
            ...(current?.trace || []),
            {
              event: "tool_result",
              step: event.step,
              tool: event.tool,
              ok: event.tool_result.ok
            }
          ],
          tool_call: toolCall,
          tool_result: event.tool_result,
          tool_count: Math.max(current?.tool_count || 0, 1),
          error: null
        };
      });
      return;
    }

    if (event.type === "planner_update") {
      /** 用途：负责 setStreamStatus 的界面或数据处理职责。 */
      setStreamStatus("Planner Update");
      /** 用途：负责 setAgentResult 的界面或数据处理职责。 */
      setAgentResult(current => ({
        answer: current?.answer || "",
        planner: event.planner,
        steps: current?.steps || [],
        trace: [
          ...(current?.trace || []),
          { event: "planner_update" }
        ],
        tool_call: current?.tool_call,
        tool_result: current?.tool_result,
        tool_count: current?.tool_count || 0,
        error: null
      }));
      return;
    }

    if (event.type === "token") {
      /** 用途：负责 setStreamStatus 的界面或数据处理职责。 */
      setStreamStatus("Final Answer Token Streaming");
      /** 用途：负责 setStreamTokenText 的界面或数据处理职责。 */
      setStreamTokenText(current => current + event.content);
      /** 用途：负责 setAgentResult 的界面或数据处理职责。 */
      setAgentResult(current => ({
        answer: `${current?.answer || ""}${event.content}`,
        planner: current?.planner || null,
        steps: current?.steps || [],
        trace: current?.trace || [],
        tool_call: current?.tool_call,
        tool_result: current?.tool_result,
        tool_count: current?.tool_count || 0,
        error: null
      }));
      return;
    }

    if (event.type === "error") {
      /** 用途：负责 setStreamStatus 的界面或数据处理职责。 */
      setStreamStatus("Error");
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(event.error);
    }
  }

  /** 用途：负责 sendAgentMessage 的界面或数据处理职责。 */
  async function sendAgentMessage(query: string) {
    const trimmedQuery = query.trim();
    if (!trimmedQuery || isRunning) return;

    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);
    /** 用途：负责 setAgentResult 的界面或数据处理职责。 */
    setAgentResult(null);
    /** 用途：负责 setStreamStatus 的界面或数据处理职责。 */
    setStreamStatus("Planning");
    /** 用途：负责 setStreamTokenText 的界面或数据处理职责。 */
    setStreamTokenText("");
    /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
    setStreamingMessage("Thinking...");
    /** 用途：负责 setMessages 的界面或数据处理职责。 */
    setMessages([
      ...messages,
      {
        role: "user",
        content: trimmedQuery
      }
    ]);
    /** 用途：负责 setIsRunning 的界面或数据处理职责。 */
    setIsRunning(true);
    const finalResultRef: { current: AgentRunResponse | null } = {
      current: null
    };

    try {
      await runAgentPlanStream(
        {
          query: trimmedQuery,
          kb_name: kbName,
          tools: AGENT_TOOLS,
          conversation_id: conversationId,
          max_steps: 3
        },
        event => {
          /** 用途：负责 applyStreamEvent 的界面或数据处理职责。 */
          applyStreamEvent(event);
          if (event.type === "done") {
            finalResultRef.current = event.result;
            /** 用途：负责 setStreamStatus 的界面或数据处理职责。 */
            setStreamStatus("Done");
          }
        }
      );

      const result = finalResultRef.current;
      if (!result) {
        throw new Error("Agent stream finished without a done event.");
      }
      /** 用途：负责 setAgentResult 的界面或数据处理职责。 */
      setAgentResult(result);
      if (result.conversation_id) {
        /** 用途：负责 setConversationId 的界面或数据处理职责。 */
        setConversationId(result.conversation_id);
      }

      if (result.error) {
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(result.error);
      }

      /** 用途：负责 setMessages 的界面或数据处理职责。 */
      setMessages([
        ...messages,
        {
          role: "user",
          content: trimmedQuery
        },
        {
          id: result.assistant_message_id || undefined,
          role: "assistant",
          content: result.answer || result.error || "No agent answer returned.",
          metadata: {
            agent: true,
            mode: "planner",
            planner: result.planner || null,
            steps: result.steps || [],
            tool_call: result.tool_call,
            tool_result: result.tool_result,
            trace: result.trace,
            tool_count: result.tool_count || 0,
            version: "agent-v3"
          }
        }
      ]);
      await refreshConversations();
    } catch (agentError) {
      const message =
        agentError instanceof Error ? agentError.message : "Agent request failed.";
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(message);
      /** 用途：负责 setMessages 的界面或数据处理职责。 */
      setMessages([
        ...messages,
        {
          role: "user",
          content: trimmedQuery
        },
        {
          role: "assistant",
          content: message
        }
      ]);
    } finally {
      /** 用途：负责 setStreamingMessage 的界面或数据处理职责。 */
      setStreamingMessage("");
      /** 用途：负责 setIsRunning 的界面或数据处理职责。 */
      setIsRunning(false);
      /** 用途：负责 setStreamStatus 的界面或数据处理职责。 */
      setStreamStatus(null);
    }
  }

  return {
    agentResult,
    error,
    isRunning,
    sendAgentMessage,
    streamStatus,
    streamTokenText
  };
}

import { useEffect, useRef, useState } from "react";
import { runAgentPlanStream } from "../api/agent";
import { useConversationStore } from "../stores/conversationStore";
import type {
  AgentRunResponse,
  AgentStep,
  AgentStreamEvent
} from "../types/agent";
import { useI18n } from "../i18n";

const AGENT_TOOLS = [
  "calculator",
  "current_time",
  "kb_search",
  "sqlite_readonly_query",
  "filesystem_readonly_read",
  "browser_read",
  "browser_search"
];

type AgentRun = {
  controller: AbortController;
  id: number;
  initialConversationId: number | null;
  serverConversationId?: number;
};

function isAbortError(error: unknown) {
  return error instanceof Error && error.name === "AbortError";
}

export function useAgentRun() {
  /**
   * 管理 Agent 从规划、工具执行到最终回答的流式界面状态。
   * 后端事件提供步骤进度和工具结果；请求编号、会话归属和 AbortController 共同保证
   * 已停止或已切换会话的 Agent 不再修改当前界面。
   */
  const { t } = useI18n();
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
  const activeRunRef = useRef<AgentRun | null>(null);
  const conversationIdRef = useRef(conversationId);
  const nextRunIdRef = useRef(0);

  function isCurrentRun(run: AgentRun) {
    // Agent 可能在首个请求中由后端创建会话，因此同时接受请求开始时和服务端返回的会话编号。
    const currentConversationId = conversationIdRef.current;
    return (
      activeRunRef.current?.id === run.id &&
      !run.controller.signal.aborted &&
      (currentConversationId === run.initialConversationId ||
        (run.serverConversationId !== undefined &&
          currentConversationId === run.serverConversationId))
    );
  }

  function abortRun(run: AgentRun) {
    if (activeRunRef.current?.id === run.id) {
      activeRunRef.current = null;
    }
    run.controller.abort();
  }

  function stopAgentRun() {
    const run = activeRunRef.current;
    if (!run) return;
    abortRun(run);
    setIsRunning(false);
    setStreamStatus(null);
    setStreamingMessage("");
  }

  useEffect(() => {
    // 用户切换会话后，旧 Agent 即使仍有网络事件到达，也会失去界面写入权并被取消。
    conversationIdRef.current = conversationId;
    const run = activeRunRef.current;
    if (run && !isCurrentRun(run)) {
      abortRun(run);
      setAgentResult(null);
      setError(null);
      setIsRunning(false);
      setStreamStatus(null);
      setStreamTokenText("");
    }
  }, [conversationId]);

  useEffect(() => {
    return () => {
      const run = activeRunRef.current;
      if (run) abortRun(run);
    };
  }, []);

  function upsertStep(steps: AgentStep[] | undefined, nextStep: AgentStep) {
    const current = steps || [];
    const index = current.findIndex(step => step.step === nextStep.step);

    if (index === -1) return [...current, nextStep];

    return current.map(step =>
      step.step === nextStep.step ? { ...step, ...nextStep } : step
    );
  }

  function applyStreamEvent(event: AgentStreamEvent) {
    // 这里把后端 Agent SSE 事件还原成界面可展示的规划、步骤、工具调用和执行结果。
    // token 事件来自后端对已生成最终回答的分段回放，不代表模型正在原生逐 token 输出。
    if (event.type === "planning") {
      setStreamStatus(t("agent.planning"));
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
      setStreamStatus(t("agent.stepNumber", { step: event.step }));
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
      setStreamStatus(t("agent.toolCall"));
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
      setStreamStatus(t("agent.toolResult"));
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
      setStreamStatus(t("agent.plannerUpdate"));
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
      setStreamStatus(t("agent.tokenStreaming"));
      setStreamTokenText(current => current + event.content);
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
      setStreamStatus(t("common.error"));
      setError(event.error);
    }
  }

  async function sendAgentMessage(query: string) {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    const previousRun = activeRunRef.current;
    // 新任务接管当前 Agent 工作区前先取消旧任务，防止两个执行过程交叉写入状态。
    if (previousRun) abortRun(previousRun);

    const run: AgentRun = {
      controller: new AbortController(),
      id: ++nextRunIdRef.current,
      initialConversationId: conversationId
    };
    activeRunRef.current = run;

    setError(null);
    setAgentResult(null);
    setStreamStatus(t("agent.planning"));
    setStreamTokenText("");
    setStreamingMessage(t("agent.thinking"));
    setMessages([
      ...messages,
      {
        role: "user",
        content: trimmedQuery
      }
    ]);
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
          if (!isCurrentRun(run)) return;

          applyStreamEvent(event);
          if (event.type === "done") {
            finalResultRef.current = event.result;
            run.serverConversationId = event.result.conversation_id || undefined;
            setStreamStatus(t("common.done"));
          }
        },
        run.controller.signal
      );

      if (!isCurrentRun(run)) return;

      const result = finalResultRef.current;
      if (!result) {
        throw new Error("Agent stream finished without a done event.");
      }
      setAgentResult(result);
      if (result.conversation_id) {
        setConversationId(result.conversation_id);
      }

      if (result.error) {
        setError(result.error);
      }

      setMessages([
        ...messages,
        {
          role: "user",
          content: trimmedQuery
        },
        {
          id: result.assistant_message_id || undefined,
          role: "assistant",
          content: result.answer || result.error || t("chat.agentNoAnswer"),
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
      if (isAbortError(agentError) || !isCurrentRun(run)) return;

      const message =
        agentError instanceof Error ? agentError.message : t("agent.requestFailed");
      setError(message);
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
      if (isCurrentRun(run)) {
        activeRunRef.current = null;
        setStreamingMessage("");
        setIsRunning(false);
        setStreamStatus(null);
      }
    }
  }

  return {
    agentResult,
    error,
    isRunning,
    sendAgentMessage,
    stopAgentRun,
    streamStatus,
    streamTokenText
  };
}

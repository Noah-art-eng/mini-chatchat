export type AgentToolCall = {
  tool: string;
  arguments: Record<string, unknown>;
  reason?: string;
};

export type AgentToolResult = {
  ok: boolean;
  result?: unknown;
  error?: string | null;
  metadata?: Record<string, unknown>;
};

export type AgentTraceEvent = {
  type?: string;
  event?: string;
  step?: number;
  tool?: string;
  tool_call?: AgentToolCall | null;
  arguments?: Record<string, unknown>;
  answer?: string;
  message?: string;
  summary?: string;
  ok?: boolean;
  error?: string | null;
  reason?: string | null;
};

export type AgentStreamEvent =
  | {
      type: "planning";
      planner: PlannerState;
    }
  | {
      type: "step_start";
      step: number;
    }
  | {
      type: "tool_call";
      step: number;
      tool_call: AgentToolCall;
    }
  | {
      type: "tool_result";
      step: number;
      tool?: string;
      tool_result: AgentToolResult;
      observation?: string;
    }
  | {
      type: "planner_update";
      planner: PlannerState;
    }
  | {
      type: "token";
      content: string;
    }
  | {
      type: "done";
      result: AgentRunResponse;
    }
  | {
      type: "error";
      error: string;
    };

export type AgentStep = {
  step: number;
  tool_call: AgentToolCall;
  tool_result: AgentToolResult;
  observation?: string;
};

export type PlannerStepStatus =
  | "planned"
  | "running"
  | "completed"
  | "failed"
  | "skipped";

export type PlannerStep = {
  id: number;
  title: string;
  status: PlannerStepStatus;
  observation?: string;
};

export type PlannerObservation = {
  step?: number | null;
  tool?: string | null;
  ok?: boolean;
  summary?: string;
};

export type PlannerState = {
  goal: string;
  steps: PlannerStep[];
  status: PlannerStepStatus;
  current_step?: number | null;
  observations?: PlannerObservation[];
};

export type AgentRunRequest = {
  query: string;
  kb_name: string;
  tools: string[];
  conversation_id?: number | null;
  max_steps?: number;
};

export type AgentRunResponse = {
  answer: string;
  tool_call?: AgentToolCall | null;
  tool_result?: AgentToolResult | null;
  planner?: PlannerState | null;
  steps?: AgentStep[];
  trace: AgentTraceEvent[];
  tool_count?: number;
  error: string | null;
  conversation_id?: number | null;
  assistant_message_id?: number | null;
};

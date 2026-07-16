import type {
  AgentToolCall,
  AgentToolResult,
  AgentStep,
  AgentTraceEvent,
  PlannerState
} from "./agent";

export type Conversation = {
  id: number;
  title: string;
  create_time: string;
  updated_time?: string;
};

export type ChatRole = "user" | "assistant" | "system";

export type ChatMessage = {
  id?: number;
  role: ChatRole;
  content: string;
  create_time?: string;
  feedback_score?: number | null;
  feedback_reason?: string | null;
  metadata?: MessageMetadata | null;
  sources?: Source[];
};

export type MessageMetadata = {
  agent?: boolean;
  mode?: string;
  planner?: PlannerState | null;
  steps?: AgentStep[];
  tool_call?: AgentToolCall | null;
  tool_result?: AgentToolResult | null;
  trace?: AgentTraceEvent[];
  tool_count?: number;
  version?: string;
  sources?: Source[];
};

export type Source = {
  chunk?: string;
  content?: string;
  file_name?: string;
  source?: string;
  title?: string;
  url?: string;
  score?: number;
  distance?: number;
  rerank_score?: number;
  chunk_id?: number;
};

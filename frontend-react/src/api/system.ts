import { requestJson } from "./client";

export type ModelsResponse = {
  chat: {
    provider: string;
    default_model: string;
    base_url: string | null;
    temperature: number;
    max_tokens: number | null;
  };
  embedding: {
    default_model: string;
  };
};

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  provider: string;
};

export type HealthDepsResponse = {
  status: string;
  checks: Record<string, string>;
};

export type ToolSpecResponse = {
  name: string;
  description?: string;
  provider?: string;
  read_only?: boolean;
  risk_level?: string;
  server_name?: string | null;
  tool_name?: string | null;
  qualified_name?: string;
  args_schema?: Record<string, unknown>;
  input_schema?: Record<string, unknown>;
};

export type ToolsResponse = {
  tools: ToolSpecResponse[];
};

export type McpServerResponse = {
  server: string;
  enabled?: boolean;
  provider?: string;
  transport?: string;
  running?: boolean;
  initialized?: boolean;
  tool_count?: number;
  error?: string;
};

export type McpServersResponse = {
  servers: McpServerResponse[];
};

export type McpToolsResponse = {
  tools: ToolSpecResponse[];
  enabled?: boolean;
  provider?: string;
};

/** 用途：负责 getModels 的界面或数据处理职责。 */
export function getModels() {
  return requestJson<ModelsResponse>("/models");
}

/** 用途：负责 getHealth 的界面或数据处理职责。 */
export function getHealth() {
  return requestJson<HealthResponse>("/health");
}

/** 用途：负责 getHealthDeps 的界面或数据处理职责。 */
export function getHealthDeps() {
  return requestJson<HealthDepsResponse>("/health/deps");
}

/** 用途：负责 getAgentTools 的界面或数据处理职责。 */
export function getAgentTools() {
  return requestJson<ToolsResponse>("/agent/tools");
}

/** 用途：负责 getMcpServers 的界面或数据处理职责。 */
export function getMcpServers() {
  return requestJson<McpServersResponse>("/agent/mcp/servers");
}

/** 用途：负责 getMcpTools 的界面或数据处理职责。 */
export function getMcpTools() {
  return requestJson<McpToolsResponse>("/agent/mcp/tools");
}

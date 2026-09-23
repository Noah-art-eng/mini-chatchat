import { AgentWorkspace } from "./agent";
import type { AgentRunResponse } from "../types/agent";

type AgentTracePanelProps = {
  error: string | null;
  isRunning: boolean;
  result: AgentRunResponse | null;
  showDeveloperDetails?: boolean;
  streamStatus?: string | null;
  streamTokenText?: string;
};

/** 用途：负责 AgentTracePanel 的界面或数据处理职责。 */
export function AgentTracePanel(props: AgentTracePanelProps) {
  return <AgentWorkspace {...props} />;
}

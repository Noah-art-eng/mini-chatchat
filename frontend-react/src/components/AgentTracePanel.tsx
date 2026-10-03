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

export function AgentTracePanel(props: AgentTracePanelProps) {
  return <AgentWorkspace {...props} />;
}

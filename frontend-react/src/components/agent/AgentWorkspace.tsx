import type { AgentRunResponse } from "../../types/agent";
import { AgentHeader } from "./AgentHeader";
import { AgentRunToolbar } from "./AgentRunToolbar";
import { AgentStatus } from "./AgentStatus";
import { AgentThought } from "./AgentThought";
import { AgentTimeline } from "./AgentTimeline";
import { AgentTraceList } from "./AgentTraceList";
import { EmptyAgentState } from "./EmptyAgentState";
import { FinalAnswer } from "./FinalAnswer";
import { ToolCallSummary } from "./ToolCallSummary";
import { ToolObservation } from "./ToolObservation";
import { MarkdownContent } from "../chat";
import { useI18n } from "../../i18n";

type AgentWorkspaceProps = {
  error: string | null;
  isRunning: boolean;
  result: AgentRunResponse | null;
  showDeveloperDetails?: boolean;
  streamStatus?: string | null;
  streamTokenText?: string;
};

/** 用途：负责 AgentWorkspace 的界面或数据处理职责。 */
export function AgentWorkspace({
  error,
  isRunning,
  result,
  showDeveloperDetails = false,
  streamStatus,
  streamTokenText = ""
}: AgentWorkspaceProps) {
  const { t } = useI18n();
  const hasSteps = Boolean(result?.steps?.length);

  if (!isRunning && !result && !error) {
    return <EmptyAgentState />;
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section
      aria-label="Agent trace"
      className="agent-trace-panel"
      data-testid="agent-trace-panel"
    >
      <AgentHeader isRunning={isRunning} />
      <AgentRunToolbar result={result} />
      <AgentStatus isRunning={isRunning} streamStatus={streamStatus} />
      {error && <p className="inline-error">{error}</p>}
      {result?.planner && <AgentThought planner={result.planner} />}
      {result?.steps && <AgentTimeline steps={result.steps} />}
      {!hasSteps && result?.tool_call && (
        <ToolCallSummary toolCall={result.tool_call} />
      )}
      {!hasSteps && result?.tool_result && (
        <ToolObservation
          toolCall={result.tool_call}
          toolResult={result.tool_result}
        />
      )}
      <FinalAnswer answer={result?.answer || ""} />
      {streamTokenText && (
        <article className="agent-trace-card" data-testid="agent-stream-token">
          <strong>{t("agent.tokenStreaming")}</strong>
          <MarkdownContent content={streamTokenText} />
        </article>
      )}
      {showDeveloperDetails && result?.trace && <AgentTraceList trace={result.trace} />}
    </section>
  );
}

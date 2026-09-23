import type { AgentToolCall } from "../../types/agent";
import { formatJson } from "./agentFormatters";
import { useI18n } from "../../i18n";

type ToolCallSummaryProps = {
  toolCall: AgentToolCall;
};

/** 用途：负责 ToolCallSummary 的界面或数据处理职责。 */
export function ToolCallSummary({ toolCall }: ToolCallSummaryProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="agent-trace-card" data-testid="agent-tool-call">
      <span className="agent-card-label">{t("agent.selectedTool")}</span>
      <strong>{toolCall.tool}</strong>
      {toolCall.reason && <small>{toolCall.reason}</small>}
      <details>
        <summary>{t("agent.arguments")}</summary>
        <pre>{formatJson(toolCall.arguments)}</pre>
      </details>
    </article>
  );
}

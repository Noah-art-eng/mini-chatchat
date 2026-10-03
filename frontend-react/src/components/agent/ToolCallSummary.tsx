import type { AgentToolCall } from "../../types/agent";
import { formatJson } from "./agentFormatters";
import { useI18n } from "../../i18n";
import { agentStyles } from "./agentStyles";

type ToolCallSummaryProps = {
  toolCall: AgentToolCall;
};

export function ToolCallSummary({ toolCall }: ToolCallSummaryProps) {
  const { t } = useI18n();

  return (
    <article className={agentStyles.card} data-testid="agent-tool-call">
      <span className={agentStyles.label}>{t("agent.selectedTool")}</span>
      <strong>{toolCall.tool}</strong>
      {toolCall.reason && <small>{toolCall.reason}</small>}
      <details>
        <summary>{t("agent.arguments")}</summary>
        <pre>{formatJson(toolCall.arguments)}</pre>
      </details>
    </article>
  );
}

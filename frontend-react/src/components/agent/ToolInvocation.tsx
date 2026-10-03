import type { AgentToolCall } from "../../types/agent";
import { formatJson } from "./agentFormatters";
import { useI18n } from "../../i18n";

type ToolInvocationProps = {
  toolCall: AgentToolCall;
};

export function ToolInvocation({ toolCall }: ToolInvocationProps) {
  const { t } = useI18n();

  return (
    <div data-testid="agent-step-tool">
      {toolCall.reason && <p>{toolCall.reason}</p>}
      <details>
        <summary>{t("agent.arguments")}</summary>
        <pre>{formatJson(toolCall.arguments)}</pre>
      </details>
    </div>
  );
}

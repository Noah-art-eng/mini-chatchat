import type { AgentToolCall } from "../../types/agent";
import { formatJson } from "./agentFormatters";
import { useI18n } from "../../i18n";

type ToolInvocationProps = {
  toolCall: AgentToolCall;
};

/** 用途：负责 ToolInvocation 的界面或数据处理职责。 */
export function ToolInvocation({ toolCall }: ToolInvocationProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
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

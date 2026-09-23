import type { AgentToolCall, AgentToolResult } from "../../types/agent";
import { ToolResult } from "./ToolResult";
import { getToolVisualByName } from "./agentToolVisuals";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";

type ToolObservationProps = {
  toolCall?: AgentToolCall | null;
  toolResult: AgentToolResult;
};

/** 用途：负责 ToolObservation 的界面或数据处理职责。 */
export function ToolObservation({
  toolCall,
  toolResult
}: ToolObservationProps) {
  const { t } = useI18n();
  const toolVisual = getToolVisualByName(toolCall?.tool || "");

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="agent-trace-card" data-testid="agent-tool-result">
      <strong className="agent-card-title">
        <Icon icon={toolVisual.icon} size="sm" tone={toolVisual.tone} />
        {t("agent.toolResult")} / {t("agent.observation")}
      </strong>
      <ToolResult result={toolResult} toolName={toolCall?.tool || ""} />
    </article>
  );
}

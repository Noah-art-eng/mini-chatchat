import { Wrench } from "lucide-react";
import type { AgentStep as AgentStepType } from "../../types/agent";
import { ToolInvocation } from "./ToolInvocation";
import { ToolResult } from "./ToolResult";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import { getToolVisualByName } from "./agentToolVisuals";

type AgentStepProps = {
  step: AgentStepType;
};

/** 用途：负责 AgentStep 的界面或数据处理职责。 */
export function AgentStep({ step }: AgentStepProps) {
  const { t } = useI18n();
  const toolVisual = getToolVisualByName(step.tool_call.tool);

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article
      className="agent-trace-card agent-timeline-step"
      data-testid="agent-step"
    >
      <div className="timeline-marker" aria-hidden="true">
        <Icon icon={Wrench} size="sm" tone={toolVisual.tone} />
      </div>
      <div className="timeline-content">
        <div className="agent-step-heading">
          <span>{t("agent.step")} {step.step}</span>
          <strong>
            <Icon icon={toolVisual.icon} size="sm" tone={toolVisual.tone} />
            {step.tool_call.tool}
          </strong>
        </div>
        <ToolInvocation toolCall={step.tool_call} />
        <ToolResult result={step.tool_result} toolName={step.tool_call.tool} />
      </div>
    </article>
  );
}

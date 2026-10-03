import { Wrench } from "lucide-react";
import type { AgentStep as AgentStepType } from "../../types/agent";
import { ToolInvocation } from "./ToolInvocation";
import { ToolResult } from "./ToolResult";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import { getToolVisualByName } from "./agentToolVisuals";
import { cx } from "../ui/utils";
import { agentStyles } from "./agentStyles";

type AgentStepProps = {
  step: AgentStepType;
};

export function AgentStep({ step }: AgentStepProps) {
  const { t } = useI18n();
  const toolVisual = getToolVisualByName(step.tool_call.tool);

  return (
    <article
      className={cx(agentStyles.card, agentStyles.timelineStep)}
      data-testid="agent-step"
    >
      <div className={agentStyles.marker} aria-hidden="true">
        <Icon icon={Wrench} size="sm" tone={toolVisual.tone} />
      </div>
      <div className={agentStyles.timelineContent}>
        <div className={agentStyles.stepHeading}>
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

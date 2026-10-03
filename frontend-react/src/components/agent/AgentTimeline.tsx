import type { AgentStep as AgentStepType } from "../../types/agent";
import { AgentStep } from "./AgentStep";
import { agentStyles } from "./agentStyles";

type AgentTimelineProps = {
  steps: AgentStepType[];
};

export function AgentTimeline({ steps }: AgentTimelineProps) {
  if (steps.length === 0) {
    return null;
  }

  return (
    <div className={agentStyles.timeline}>
      {steps.map(step => (
        <AgentStep key={step.step} step={step} />
      ))}
    </div>
  );
}

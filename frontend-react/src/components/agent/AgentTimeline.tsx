import type { AgentStep as AgentStepType } from "../../types/agent";
import { AgentStep } from "./AgentStep";

type AgentTimelineProps = {
  steps: AgentStepType[];
};

/** 用途：负责 AgentTimeline 的界面或数据处理职责。 */
export function AgentTimeline({ steps }: AgentTimelineProps) {
  if (steps.length === 0) {
    return null;
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="agent-timeline">
      {steps.map(step => (
        <AgentStep key={step.step} step={step} />
      ))}
    </div>
  );
}

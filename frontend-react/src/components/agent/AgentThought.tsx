import {
  Circle,
  CircleCheck,
  CircleX,
  LoaderCircle,
  Play,
  Square
} from "lucide-react";
import type { PlannerState } from "../../types/agent";
import { getPreview } from "./agentFormatters";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";

type AgentThoughtProps = {
  planner: PlannerState;
};

/** 用途：负责 getPlannerStatusIcon 的界面或数据处理职责。 */
function getPlannerStatusIcon(status: string) {
  if (status === "running") return LoaderCircle;
  if (status === "completed") return CircleCheck;
  if (status === "failed") return CircleX;
  if (status === "skipped") return Circle;
  if (status === "ready") return Play;
  return Square;
}

/** 用途：负责 getPlannerStatusTone 的界面或数据处理职责。 */
function getPlannerStatusTone(status: string) {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "running") return "info";
  return "muted";
}

/** 用途：负责 AgentThought 的界面或数据处理职责。 */
export function AgentThought({ planner }: AgentThoughtProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article
      className="agent-trace-card planner-card"
      data-testid="planner-panel"
    >
      <strong>{t("agent.planning")}</strong>
      <div className="planner-summary">
        <span>{t("agent.goal")}</span>
        <p data-testid="planner-goal">{planner.goal}</p>
      </div>
      <div className="agent-tool-fields">
        <div>
          <span>{t("agent.status")}</span>
          <strong data-testid="planner-status">{planner.status}</strong>
        </div>
        <div>
          <span>{t("agent.currentStep")}</span>
          <strong>{String(planner.current_step ?? "-")}</strong>
        </div>
        <div>
          <span>{t("agent.steps")}</span>
          <strong>{String(planner.steps.length)}</strong>
        </div>
      </div>
      <ol className="planner-step-list">
        {planner.steps.map(step => (
          <li
            className={`planner-step ${step.status}`}
            data-testid="planner-step"
            key={step.id}
          >
            <span aria-hidden="true">
              <Icon
                icon={getPlannerStatusIcon(step.status)}
                size="sm"
                tone={getPlannerStatusTone(step.status)}
              />
            </span>
            <div>
              <strong>{`${t("agent.step")} ${step.id}: ${step.title}`}</strong>
              <small>{step.status}</small>
              {step.observation && <p>{getPreview(step.observation, 300)}</p>}
            </div>
          </li>
        ))}
      </ol>
    </article>
  );
}

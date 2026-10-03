import { useI18n } from "../../i18n";
import { agentStyles } from "./agentStyles";

type AgentHeaderProps = {
  isRunning: boolean;
};

export function AgentHeader({ isRunning }: AgentHeaderProps) {
  const { t } = useI18n();

  return (
    <div className={agentStyles.heading}>
      <p className="eyebrow">{t("agent.traceTitle")}</p>
      <h3>{isRunning ? t("agent.thinking") : t("agent.runDetails")}</h3>
    </div>
  );
}

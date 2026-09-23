import { useI18n } from "../../i18n";

type AgentHeaderProps = {
  isRunning: boolean;
};

/** 用途：负责 AgentHeader 的界面或数据处理职责。 */
export function AgentHeader({ isRunning }: AgentHeaderProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="panel-heading">
      <p className="eyebrow">{t("agent.traceTitle")}</p>
      <h3>{isRunning ? t("agent.thinking") : t("agent.runDetails")}</h3>
    </div>
  );
}

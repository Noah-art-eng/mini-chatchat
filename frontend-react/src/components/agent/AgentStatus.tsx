import { useI18n } from "../../i18n";
import { cx } from "../ui/utils";
import { agentStyles } from "./agentStyles";

type AgentStatusProps = {
  isRunning: boolean;
  streamStatus?: string | null;
};

/** 用途：负责 AgentStatus 的界面或数据处理职责。 */
export function AgentStatus({ isRunning, streamStatus }: AgentStatusProps) {
  const { t } = useI18n();

  if (!streamStatus && !isRunning) {
    return null;
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article
      aria-live="polite"
      className={cx(agentStyles.card, agentStyles.running)}
      data-testid="agent-stream-status"
    >
      <span className={agentStyles.liveDot} aria-hidden="true" />
      <strong>{streamStatus || t("agent.thinking")}</strong>
    </article>
  );
}

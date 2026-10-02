import { useI18n } from "../../i18n";
import type { AgentRunResponse } from "../../types/agent";
import { agentStyles } from "./agentStyles";

type AgentRunToolbarProps = {
  result: AgentRunResponse | null;
};

/** 用途：负责 AgentRunToolbar 的界面或数据处理职责。 */
export function AgentRunToolbar({ result }: AgentRunToolbarProps) {
  const { t } = useI18n();

  if (!result) {
    return null;
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className={agentStyles.toolbar}>
      <span className={agentStyles.toolbarItem}>{t("agent.steps")}: {result.steps?.length || 0}</span>
      <span className={agentStyles.toolbarItem}>{t("agent.toolCall")}: {result.tool_count || 0}</span>
      {result.error && <span className={agentStyles.error}>{result.error}</span>}
    </div>
  );
}

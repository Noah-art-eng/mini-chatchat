import { useI18n } from "../../i18n";
import type { AgentRunResponse } from "../../types/agent";

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
    <div className="agent-run-toolbar">
      <span>{t("agent.steps")}: {result.steps?.length || 0}</span>
      <span>{t("agent.toolCall")}: {result.tool_count || 0}</span>
      {result.error && <span className="agent-error">{result.error}</span>}
    </div>
  );
}

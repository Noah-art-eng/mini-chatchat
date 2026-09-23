import { useI18n } from "../../i18n";

type MCPStatusProps = {
  enabled?: boolean;
  mcpError: string | null;
  serversCount: number;
  toolsCount: number;
};

/** 用途：负责 MCPStatus 的界面或数据处理职责。 */
export function MCPStatus({
  enabled,
  mcpError,
  serversCount,
  toolsCount
}: MCPStatusProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="system-summary-strip">
      <span>{t("settings.mcpStatus")}: {enabled === false ? "disabled" : "enabled"}</span>
      <span>{t("settings.servers")}: {serversCount}</span>
      <span>{t("settings.tools")}: {toolsCount}</span>
      {mcpError && <span className="agent-error">{mcpError}</span>}
    </div>
  );
}

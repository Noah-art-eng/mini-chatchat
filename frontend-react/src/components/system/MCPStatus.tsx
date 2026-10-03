import { useI18n } from "../../i18n";

type MCPStatusProps = {
  enabled?: boolean;
  mcpError: string | null;
  serversCount: number;
  toolsCount: number;
};

export function MCPStatus({
  enabled,
  mcpError,
  serversCount,
  toolsCount
}: MCPStatusProps) {
  const { t } = useI18n();

  return (
    <div className="system-summary-strip flex flex-wrap gap-mc-2 [&>span]:rounded-mc-pill [&>span]:border [&>span]:border-solid [&>span]:border-mc-border-subtle [&>span]:bg-mc-subtle [&>span]:px-mc-2 [&>span]:py-mc-1 [&>span]:text-mc-caption [&>span]:font-mc-semibold [&>span]:text-mc-secondary">
      <span>{t("settings.mcpStatus")}: {enabled === false ? "disabled" : "enabled"}</span>
      <span>{t("settings.servers")}: {serversCount}</span>
      <span>{t("settings.tools")}: {toolsCount}</span>
      {mcpError && <span className="agent-error">{mcpError}</span>}
    </div>
  );
}

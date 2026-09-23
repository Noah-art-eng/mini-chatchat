import { Plug } from "lucide-react";
import { MCPServerCard } from "./MCPServerCard";
import { MCPStatus } from "./MCPStatus";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type {
  McpServersResponse,
  McpToolsResponse
} from "../../api/system";

type MCPSectionProps = {
  mcpError: string | null;
  mcpServers: McpServersResponse | null;
  mcpTools: McpToolsResponse | null;
};

/** 用途：负责 MCPSection 的界面或数据处理职责。 */
export function MCPSection({
  mcpError,
  mcpServers,
  mcpTools
}: MCPSectionProps) {
  const { t } = useI18n();
  const servers = mcpServers?.servers || [];
  const tools = mcpTools?.tools || [];

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="settings-card system-wide-card">
      <span className={`settings-badge status-${mcpError ? "degraded" : "ok"}`}>
        MCP
      </span>
      <h2><Icon icon={Plug} size="sm" tone="mcp" />{t("settings.mcp")}</h2>
      <MCPStatus
        enabled={mcpTools?.enabled}
        mcpError={mcpError}
        serversCount={servers.length}
        toolsCount={tools.length}
      />
      {servers.length === 0 && !mcpError && (
        <p className="muted">{t("settings.noMcpServers")}</p>
      )}
      <div className="system-tool-list">
        {servers.map(server => (
          <MCPServerCard key={server.server} server={server} />
        ))}
      </div>
    </article>
  );
}

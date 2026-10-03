import { Plug } from "lucide-react";
import { MCPServerCard } from "./MCPServerCard";
import { MCPStatus } from "./MCPStatus";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type {
  McpServersResponse,
  McpToolsResponse
} from "../../api/system";
import { systemBadgeClassName, systemCardClassName } from "./systemStyles";

type MCPSectionProps = {
  mcpError: string | null;
  mcpServers: McpServersResponse | null;
  mcpTools: McpToolsResponse | null;
};

export function MCPSection({
  mcpError,
  mcpServers,
  mcpTools
}: MCPSectionProps) {
  const { t } = useI18n();
  const servers = mcpServers?.servers || [];
  const tools = mcpTools?.tools || [];

  return (
    <article className={`${systemCardClassName} system-wide-card col-span-full`}>
      <span className={`${systemBadgeClassName} status-${mcpError ? "degraded" : "ok"}`}>
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
      <div className="system-tool-list grid grid-cols-[repeat(auto-fill,minmax(210px,1fr))] gap-mc-4 max-[1100px]:grid-cols-[repeat(auto-fill,minmax(220px,1fr))] max-[720px]:grid-cols-1">
        {servers.map(server => (
          <MCPServerCard key={server.server} server={server} />
        ))}
      </div>
    </article>
  );
}

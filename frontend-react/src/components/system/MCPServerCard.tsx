import type { McpServerResponse } from "../../api/system";

type MCPServerCardProps = {
  server: McpServerResponse;
};

/** 用途：负责 MCPServerCard 的界面或数据处理职责。 */
export function MCPServerCard({ server }: MCPServerCardProps) {
  const status = server.error
    ? "failed"
    : server.running || server.initialized || server.enabled
      ? "ok"
      : "degraded";

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="system-tool-card">
      <strong>{server.server}</strong>
      <div>
        <span className={`status status-${status}`}>{status}</span>
        {server.transport && <span className="status">{server.transport}</span>}
        <span className="status">{server.tool_count ?? 0} tools</span>
      </div>
      {server.error && <p className="inline-error">{server.error}</p>}
    </article>
  );
}

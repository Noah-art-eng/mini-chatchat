import type { McpServerResponse } from "../../api/system";

type MCPServerCardProps = {
  server: McpServerResponse;
};

export function MCPServerCard({ server }: MCPServerCardProps) {
  const status = server.error
    ? "failed"
    : server.running || server.initialized || server.enabled
      ? "ok"
      : "degraded";

  return (
    <article className="system-tool-card rounded-mc-lg border border-solid border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-bg-surface)_86%,transparent)] [box-shadow:none] [backdrop-filter:blur(18px)]">
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

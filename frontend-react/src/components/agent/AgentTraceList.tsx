import type { AgentTraceEvent } from "../../types/agent";
import { useI18n } from "../../i18n";

type AgentTraceListProps = {
  trace: AgentTraceEvent[];
};

/** 用途：负责 AgentTraceList 的界面或数据处理职责。 */
export function AgentTraceList({ trace }: AgentTraceListProps) {
  const { t } = useI18n();

  if (trace.length === 0) {
    return null;
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <details className="agent-trace-card" open={false}>
      <summary>{t("agent.trace")}</summary>
      <ol className="agent-trace-list">
        {trace.map((event, index) => (
          <li key={`${event.type || event.event || "event"}-${index}`}>
            <span>{event.type || event.event || "event"}</span>
            {event.step && <small>step {event.step}</small>}
            {event.tool && <small>{event.tool}</small>}
            {event.error && <small className="agent-error">{event.error}</small>}
          </li>
        ))}
      </ol>
    </details>
  );
}

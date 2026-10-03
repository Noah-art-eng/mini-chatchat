import type { AgentTraceEvent } from "../../types/agent";
import { useI18n } from "../../i18n";
import { agentStyles } from "./agentStyles";

type AgentTraceListProps = {
  trace: AgentTraceEvent[];
};

export function AgentTraceList({ trace }: AgentTraceListProps) {
  const { t } = useI18n();

  if (trace.length === 0) {
    return null;
  }

  return (
    <details className={agentStyles.card} open={false}>
      <summary>{t("agent.trace")}</summary>
      <ol className={agentStyles.traceList}>
        {trace.map((event, index) => (
          <li className={agentStyles.traceItem} key={`${event.type || event.event || "event"}-${index}`}>
            <span>{event.type || event.event || "event"}</span>
            {event.step && <small>step {event.step}</small>}
            {event.tool && <small>{event.tool}</small>}
            {event.error && <small className={agentStyles.error}>{event.error}</small>}
          </li>
        ))}
      </ol>
    </details>
  );
}

import { Route } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";

/** 用途：负责 EmptyAgentState 的界面或数据处理职责。 */
export function EmptyAgentState() {
  const { t } = useI18n();
  const examples = [
    /** 用途：负责 t 的界面或数据处理职责。 */
    t("onboarding.agentExampleTime"),
    /** 用途：负责 t 的界面或数据处理职责。 */
    t("onboarding.agentExampleNews"),
    /** 用途：负责 t 的界面或数据处理职责。 */
    t("onboarding.agentExampleReadme"),
    /** 用途：负责 t 的界面或数据处理职责。 */
    t("onboarding.agentExampleKnowledge")
  ];

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section className="empty-agent-state">
      <div className="empty-state-icon" aria-hidden="true">
        <Icon icon={Route} size="lg" tone="mcp" />
      </div>
      <p className="eyebrow">{t("agent.traceTitle")}</p>
      <h2>{t("onboarding.agentEmptyTitle")}</h2>
      <p className="muted">{t("onboarding.agentEmptyDescription")}</p>
      <ul className="agent-empty-examples">
        {examples.map(example => (
          <li key={example}>{example}</li>
        ))}
      </ul>
    </section>
  );
}

import { Route } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import { agentStyles } from "./agentStyles";

export function EmptyAgentState() {
  const { t } = useI18n();
  const examples = [
    t("onboarding.agentExampleTime"),
    t("onboarding.agentExampleNews"),
    t("onboarding.agentExampleReadme"),
    t("onboarding.agentExampleKnowledge")
  ];

  return (
    <section className={agentStyles.empty}>
      <div className="empty-state-icon" aria-hidden="true">
        <Icon icon={Route} size="lg" tone="mcp" />
      </div>
      <p className="eyebrow">{t("agent.traceTitle")}</p>
      <h2>{t("onboarding.agentEmptyTitle")}</h2>
      <p className="muted">{t("onboarding.agentEmptyDescription")}</p>
      <ul className={agentStyles.emptyExamples}>
        {examples.map(example => (
          <li key={example}>{example}</li>
        ))}
      </ul>
    </section>
  );
}

import { MarkdownContent } from "../chat";
import { useI18n } from "../../i18n";
import { cx } from "../ui/utils";
import { agentStyles } from "./agentStyles";

type FinalAnswerProps = {
  answer: string;
};

export function FinalAnswer({ answer }: FinalAnswerProps) {
  const { t } = useI18n();

  if (!answer) {
    return null;
  }

  return (
    <article
      className={cx(agentStyles.card, agentStyles.final)}
      data-testid="agent-final-answer"
    >
      <span className={agentStyles.label}>{t("agent.finalAnswer")}</span>
      <MarkdownContent content={answer} />
    </article>
  );
}

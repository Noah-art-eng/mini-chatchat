import { MarkdownContent } from "../chat";
import { useI18n } from "../../i18n";

type FinalAnswerProps = {
  answer: string;
};

/** 用途：负责 FinalAnswer 的界面或数据处理职责。 */
export function FinalAnswer({ answer }: FinalAnswerProps) {
  const { t } = useI18n();

  if (!answer) {
    return null;
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article
      className="agent-trace-card agent-final-card"
      data-testid="agent-final-answer"
    >
      <span className="agent-card-label">{t("agent.finalAnswer")}</span>
      <MarkdownContent content={answer} />
    </article>
  );
}

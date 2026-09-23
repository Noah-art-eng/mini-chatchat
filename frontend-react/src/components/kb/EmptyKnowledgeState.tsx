import { FilePlus } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";

type EmptyKnowledgeStateProps = {
  hasKnowledgeBase?: boolean;
};

/** 用途：负责 EmptyKnowledgeState 的界面或数据处理职责。 */
export function EmptyKnowledgeState({
  hasKnowledgeBase = true
}: EmptyKnowledgeStateProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section className="empty-knowledge-state">
      <div className="empty-state-icon" aria-hidden="true">
        <Icon icon={FilePlus} size="lg" tone="file" />
      </div>
      <p className="eyebrow">{t("kb.documents")}</p>
      <h2>{hasKnowledgeBase ? t("kb.emptyFilesTitle") : t("kb.emptyKbsTitle")}</h2>
      <p>
        {hasKnowledgeBase
          ? t("kb.emptyFilesDescription")
          : t("kb.emptyKbsDescription")}
      </p>
      {hasKnowledgeBase && (
        <ol className="empty-knowledge-steps">
          <li>{t("kb.emptyUploadStep")}</li>
          <li>{t("kb.emptyIndexStep")}</li>
          <li>{t("kb.emptyAskStep")}</li>
        </ol>
      )}
    </section>
  );
}

import { useI18n } from "../../i18n";

type KnowledgeStatsProps = {
  documentsCount: number;
  failedCount: number;
  indexedCount: number;
  totalChunks: number;
};

/** 用途：负责 KnowledgeStats 的界面或数据处理职责。 */
export function KnowledgeStats({
  documentsCount,
  failedCount,
  indexedCount,
  totalChunks
}: KnowledgeStatsProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="kb-stats">
      <article>
        <span>{t("kb.documents")}</span>
        <strong>{documentsCount}</strong>
      </article>
      <article>
        <span>{t("kb.indexed")}</span>
        <strong>{indexedCount}</strong>
      </article>
      <article>
        <span>{t("kb.chunks")}</span>
        <strong>{totalChunks}</strong>
      </article>
      <article>
        <span>{t("kb.failed")}</span>
        <strong>{failedCount}</strong>
      </article>
    </div>
  );
}

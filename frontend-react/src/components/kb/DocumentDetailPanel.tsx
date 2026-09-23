import { useI18n } from "../../i18n";
import type { KnowledgeFile } from "../../types/kb";

type DocumentDetailPanelProps = {
  document: KnowledgeFile | null;
  documentsCount: number;
  failedCount: number;
  indexedCount: number;
  totalChunks: number;
};

/** 用途：负责 DocumentDetailPanel 的界面或数据处理职责。 */
export function DocumentDetailPanel({
  document,
  documentsCount,
  failedCount,
  indexedCount,
  totalChunks
}: DocumentDetailPanelProps) {
  const { t } = useI18n();

  if (!document) {
    /** 用途：负责 return 的界面或数据处理职责。 */
    return (
      <section className="document-detail-panel">
        <p className="muted">{t("kb.emptyFiles")}</p>
        <dl>
          <div>
            <dt>{t("kb.documents")}</dt>
            <dd>{documentsCount}</dd>
          </div>
          <div>
            <dt>{t("kb.indexed")}</dt>
            <dd>{indexedCount}</dd>
          </div>
          <div>
            <dt>{t("kb.failed")}</dt>
            <dd>{failedCount}</dd>
          </div>
          <div>
            <dt>{t("kb.chunks")}</dt>
            <dd>{totalChunks}</dd>
          </div>
        </dl>
      </section>
    );
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section className="document-detail-panel">
      <p className="eyebrow">{t("kb.managedFile")}</p>
      <h2>{document.filename}</h2>
      <dl>
        <div>
          <dt>{t("kb.statusUnknown")}</dt>
          <dd>{document.status || t("kb.statusUnknown")}</dd>
        </div>
        <div>
          <dt>{t("kb.chunks")}</dt>
          <dd>{document.docs_count ?? 0}</dd>
        </div>
        <div>
          <dt>{t("kb.size")}</dt>
          <dd>{document.chunk_size ?? "-"}</dd>
        </div>
        <div>
          <dt>{t("kb.overlap")}</dt>
          <dd>{document.chunk_overlap ?? "-"}</dd>
        </div>
        <div>
          <dt>upload_path</dt>
          <dd>{document.upload_path || "-"}</dd>
        </div>
        <div>
          <dt>content_path</dt>
          <dd>{document.content_path || "-"}</dd>
        </div>
      </dl>
      {document.error && <p className="inline-error">{document.error}</p>}
    </section>
  );
}

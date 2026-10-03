import { useI18n } from "../../i18n";
import type { KnowledgeFile } from "../../types/kb";

type DocumentDetailPanelProps = {
  document: KnowledgeFile | null;
  documentsCount: number;
  failedCount: number;
  indexedCount: number;
  totalChunks: number;
};

export function DocumentDetailPanel({
  document,
  documentsCount,
  failedCount,
  indexedCount,
  totalChunks
}: DocumentDetailPanelProps) {
  const { t } = useI18n();

  if (!document) {
    return (
      <section className="document-detail-panel grid min-w-0 gap-mc-4 [&_dl]:m-0 [&_dl]:grid [&_dl]:gap-mc-3 [&_dt]:text-mc-caption [&_dt]:font-mc-semibold [&_dt]:text-mc-muted [&_dd]:mt-mc-1 [&_dd]:mb-0 [&_dd]:text-mc-body-small [&_dd]:text-mc-text [&_dd]:[overflow-wrap:anywhere]">
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

  return (
    <section className="document-detail-panel grid min-w-0 gap-mc-4 [&_h2]:m-0 [&_h2]:text-mc-title [&_h2]:[overflow-wrap:anywhere] [&_dl]:m-0 [&_dl]:grid [&_dl]:gap-mc-3 [&_dt]:text-mc-caption [&_dt]:font-mc-semibold [&_dt]:text-mc-muted [&_dd]:mt-mc-1 [&_dd]:mb-0 [&_dd]:text-mc-body-small [&_dd]:text-mc-text [&_dd]:[overflow-wrap:anywhere]">
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

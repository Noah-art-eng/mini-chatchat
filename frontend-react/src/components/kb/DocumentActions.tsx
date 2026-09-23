import { Download, RefreshCw, Trash2 } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { KnowledgeFile } from "../../types/kb";
import { safeFileName } from "./utils";

type DocumentActionsProps = {
  activeDocumentAction: string | null;
  file: KnowledgeFile;
  onDelete: (filename: string) => void;
  onDownload: (filename: string) => void;
  onReindex: (file: KnowledgeFile) => void;
};

/** 用途：负责 DocumentActions 的界面或数据处理职责。 */
export function DocumentActions({
  activeDocumentAction,
  file,
  onDelete,
  onDownload,
  onReindex
}: DocumentActionsProps) {
  const { t } = useI18n();
  const safeName = safeFileName(file.filename);
  const isDownloading = activeDocumentAction === `download:${file.filename}`;
  const isReindexing = activeDocumentAction === `reindex:${file.filename}`;
  const isDeleting = activeDocumentAction === `delete:${file.filename}`;

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="document-actions">
      <button
        data-testid={`download-document-${safeName}`}
        disabled={Boolean(activeDocumentAction)}
        onClick={event => {
          event.stopPropagation();
          /** 用途：负责 onDownload 的界面或数据处理职责。 */
          onDownload(file.filename);
        }}
        type="button"
      >
        <Icon icon={Download} size="sm" />
        {isDownloading ? t("kb.downloading") : t("kb.download")}
      </button>
      <button
        data-testid={`reindex-document-${safeName}`}
        disabled={Boolean(activeDocumentAction)}
        onClick={event => {
          event.stopPropagation();
          /** 用途：负责 onReindex 的界面或数据处理职责。 */
          onReindex(file);
        }}
        type="button"
      >
        <Icon icon={RefreshCw} size="sm" />
        {isReindexing ? t("kb.reindexing") : t("kb.reindex")}
      </button>
      <button
        data-testid={`delete-document-${safeName}`}
        disabled={Boolean(activeDocumentAction)}
        onClick={event => {
          event.stopPropagation();
          /** 用途：负责 onDelete 的界面或数据处理职责。 */
          onDelete(file.filename);
        }}
        type="button"
      >
        <Icon icon={Trash2} size="sm" tone="danger" />
        {isDeleting ? t("kb.deleting") : t("kb.delete")}
      </button>
    </div>
  );
}

import { Download, RefreshCw, Trash2 } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { KnowledgeFile } from "../../types/kb";
import { safeFileName } from "./utils";
import { cx } from "../ui/utils";
import { kbDocumentActionButtonClassName } from "./kbStyles";

type DocumentActionsProps = {
  activeDocumentAction: string | null;
  file: KnowledgeFile;
  onDelete: (filename: string) => void;
  onDownload: (filename: string) => void;
  onReindex: (file: KnowledgeFile) => void;
};

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

  return (
    <div className="document-actions mt-mc-3 flex flex-wrap gap-mc-2 max-[720px]:grid max-[720px]:grid-cols-1">
      <button
        className={kbDocumentActionButtonClassName}
        data-testid={`download-document-${safeName}`}
        disabled={Boolean(activeDocumentAction)}
        onClick={event => {
          event.stopPropagation();
          onDownload(file.filename);
        }}
        type="button"
      >
        <Icon icon={Download} size="sm" />
        {isDownloading ? t("kb.downloading") : t("kb.download")}
      </button>
      <button
        className={kbDocumentActionButtonClassName}
        data-testid={`reindex-document-${safeName}`}
        disabled={Boolean(activeDocumentAction)}
        onClick={event => {
          event.stopPropagation();
          onReindex(file);
        }}
        type="button"
      >
        <Icon icon={RefreshCw} size="sm" />
        {isReindexing ? t("kb.reindexing") : t("kb.reindex")}
      </button>
      <button
        className={cx(kbDocumentActionButtonClassName, "border-mc-danger-soft bg-mc-danger-soft text-mc-danger hover:bg-mc-danger hover:text-mc-inverse")}
        data-testid={`delete-document-${safeName}`}
        disabled={Boolean(activeDocumentAction)}
        onClick={event => {
          event.stopPropagation();
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

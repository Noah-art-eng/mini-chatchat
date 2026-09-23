import {
  CircleAlert,
  CircleCheck,
  FileImage,
  FileSpreadsheet,
  FileText,
  FileType,
  FileUp,
  type LucideIcon
} from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { KnowledgeFile } from "../../types/kb";
import { DocumentActions } from "./DocumentActions";
import { safeFileName } from "./utils";

type DocumentRowProps = {
  activeDocumentAction: string | null;
  file: KnowledgeFile;
  isSelected: boolean;
  onDelete: (filename: string) => void;
  onDownload: (filename: string) => void;
  onReindex: (file: KnowledgeFile) => void;
  onSelect: (file: KnowledgeFile) => void;
};

/** 用途：负责 getFileIcon 的界面或数据处理职责。 */
function getFileIcon(filename: string): LucideIcon {
  const extension = filename.split(".").pop()?.toLowerCase() || "";

  if (extension === "pdf") return FileType;
  if (["doc", "docx"].includes(extension)) return FileText;
  if (["csv", "xls", "xlsx"].includes(extension)) return FileSpreadsheet;
  if (["png", "jpg", "jpeg", "gif", "webp"].includes(extension)) return FileImage;
  if (["md", "markdown"].includes(extension)) return FileUp;
  return FileText;
}

/** 用途：负责 DocumentRow 的界面或数据处理职责。 */
export function DocumentRow({
  activeDocumentAction,
  file,
  isSelected,
  onDelete,
  onDownload,
  onReindex,
  onSelect
}: DocumentRowProps) {
  const { t } = useI18n();
  const safeName = safeFileName(file.filename);
  const isIndexed = file.status === "indexed";
  const StatusIcon = isIndexed ? CircleCheck : CircleAlert;
  const FileIcon = getFileIcon(file.filename);

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article
      className={isSelected ? "document-row selected" : "document-row"}
      data-testid={`document-row-${safeName}`}
      onClick={() => onSelect(file)}
      role="button"
      tabIndex={0}
      onKeyDown={event => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          /** 用途：负责 onSelect 的界面或数据处理职责。 */
          onSelect(file);
        }
      }}
    >
      <div className="document-row-header">
        <div className="document-title-cell">
          <span className="document-file-icon" aria-hidden="true">
            <Icon icon={FileIcon} size="md" tone="file" />
          </span>
          <div>
            <strong data-testid={`document-filename-${safeName}`}>
              {file.filename}
            </strong>
            <small>{file.upload_path || file.content_path || t("kb.managedFile")}</small>
          </div>
        </div>
        <span
          className={`status status-${file.status || "unknown"}`}
          data-testid={`document-status-${safeName}`}
        >
          <Icon
            icon={StatusIcon}
            size="sm"
            tone={isIndexed ? "success" : "warning"}
          />
          {file.status || t("kb.statusUnknown")}
        </span>
      </div>
      <dl>
        <div>
          <dt>{t("kb.chunks")}</dt>
          <dd data-testid={`document-chunks-${safeName}`}>
            {file.docs_count ?? 0}
          </dd>
        </div>
        <div>
          <dt>{t("kb.size")}</dt>
          <dd>{file.chunk_size ?? "-"}</dd>
        </div>
        <div>
          <dt>{t("kb.overlap")}</dt>
          <dd>{file.chunk_overlap ?? "-"}</dd>
        </div>
      </dl>
      {file.error && <p className="inline-error">{file.error}</p>}
      <DocumentActions
        activeDocumentAction={activeDocumentAction}
        file={file}
        onDelete={onDelete}
        onDownload={onDownload}
        onReindex={onReindex}
      />
    </article>
  );
}

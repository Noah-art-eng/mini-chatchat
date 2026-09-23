import type { RefObject } from "react";
import { Archive, ArchiveRestore } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";

type KnowledgeBackupActionsProps = {
  importInputRef: RefObject<HTMLInputElement | null>;
  isKbActionLoading: boolean;
  kbActionStatus: string | null;
  onChangeImportFile: (file: File | null) => void;
  onExport: () => void;
  onImport: () => void;
  selectedImportFile: File | null;
};

/** 用途：负责 KnowledgeBackupActions 的界面或数据处理职责。 */
export function KnowledgeBackupActions({
  importInputRef,
  isKbActionLoading,
  kbActionStatus,
  onChangeImportFile,
  onExport,
  onImport,
  selectedImportFile
}: KnowledgeBackupActionsProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="kb-action-panel">
      <p className="section-kicker">{t("kb.backupAndMove")}</p>
      <button
        data-testid="export-kb-button"
        disabled={isKbActionLoading}
        onClick={onExport}
        type="button"
      >
        <Icon icon={Archive} size="sm" />
        {isKbActionLoading ? t("kb.working") : t("kb.export")}
      </button>

      <p className="upload-label">{t("kb.importKb")}</p>
      <input
        accept=".zip"
        className="native-file-input"
        data-testid="import-kb-input"
        id="kb-import-file"
        name="kb-import-file"
        onChange={event => onChangeImportFile(event.target.files?.[0] || null)}
        ref={importInputRef}
        type="file"
      />
      <p className="selected-file">
        {selectedImportFile ? selectedImportFile.name : t("kb.noImportFile")}
      </p>
      <button
        data-testid="import-kb-button"
        disabled={isKbActionLoading || !selectedImportFile}
        onClick={onImport}
        type="button"
      >
        <Icon icon={ArchiveRestore} size="sm" />
        {isKbActionLoading ? t("kb.importing") : t("kb.import")}
      </button>

      {kbActionStatus && (
        <p className="upload-status" data-testid="kb-action-status">
          {kbActionStatus}
        </p>
      )}
    </div>
  );
}

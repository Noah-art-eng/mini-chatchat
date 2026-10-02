import type { RefObject } from "react";
import { Archive, ArchiveRestore } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import { kbActionButtonClassName, kbFileInputClassName } from "./kbStyles";

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
    <div className="kb-action-panel grid min-w-0 gap-mc-2 rounded-[18px] border border-solid border-[rgba(23,23,23,.08)] bg-[rgba(255,255,255,.54)] p-mc-3 [box-shadow:var(--shadow-hairline)] [grid-area:actions]">
      <p className="section-kicker">{t("kb.backupAndMove")}</p>
      <button
        className={kbActionButtonClassName}
        data-testid="export-kb-button"
        disabled={isKbActionLoading}
        onClick={onExport}
        type="button"
      >
        <Icon icon={Archive} size="sm" />
        {isKbActionLoading ? t("kb.working") : t("kb.export")}
      </button>

      <p className="upload-label m-0 font-mc-bold text-mc-text">{t("kb.importKb")}</p>
      <input
        accept=".zip"
        className={kbFileInputClassName}
        data-testid="import-kb-input"
        id="kb-import-file"
        name="kb-import-file"
        onChange={event => onChangeImportFile(event.target.files?.[0] || null)}
        ref={importInputRef}
        type="file"
      />
      <p className="selected-file m-0 text-mc-caption text-mc-muted [overflow-wrap:anywhere]">
        {selectedImportFile ? selectedImportFile.name : t("kb.noImportFile")}
      </p>
      <button
        className={kbActionButtonClassName}
        data-testid="import-kb-button"
        disabled={isKbActionLoading || !selectedImportFile}
        onClick={onImport}
        type="button"
      >
        <Icon icon={ArchiveRestore} size="sm" />
        {isKbActionLoading ? t("kb.importing") : t("kb.import")}
      </button>

      {kbActionStatus && (
        <p className="upload-status m-0 text-mc-caption text-mc-muted [overflow-wrap:anywhere]" data-testid="kb-action-status">
          {kbActionStatus}
        </p>
      )}
    </div>
  );
}

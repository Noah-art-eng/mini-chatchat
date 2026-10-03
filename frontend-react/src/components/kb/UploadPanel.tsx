import type { RefObject } from "react";
import { useI18n } from "../../i18n";
import { cx } from "../ui/utils";
import { kbActionButtonClassName, kbFileInputClassName } from "./kbStyles";

type UploadPanelProps = {
  fileInputRef: RefObject<HTMLInputElement | null>;
  isUploading: boolean;
  isSwitchingKnowledgeBase: boolean;
  onChangeFile: (file: File | null) => void;
  onUpload: () => void;
  selectedFile: File | null;
  uploadStatus: string | null;
};

export function UploadPanel({
  fileInputRef,
  isUploading,
  isSwitchingKnowledgeBase,
  onChangeFile,
  onUpload,
  selectedFile,
  uploadStatus
}: UploadPanelProps) {
  const { t } = useI18n();

  return (
    <div
      className={cx(
        "upload-panel grid min-w-0 self-start gap-mc-2 rounded-mc-lg border border-dashed border-mc-border bg-mc-subtle p-mc-3 [box-shadow:var(--shadow-hairline)] [grid-column:2] [grid-area:upload] max-[900px]:[grid-column:1]",
        isUploading && "uploading border-solid border-[color-mix(in_srgb,var(--color-brand-primary)_22%,var(--color-border-default))]"
      )}
      onDragOver={event => {
        event.preventDefault();
      }}
      onDrop={event => {
        event.preventDefault();
        onChangeFile(event.dataTransfer.files?.[0] || null);
      }}
    >
      <p className="section-kicker">{t("kb.addKnowledge")}</p>
      <p className="upload-label m-0 font-mc-bold text-mc-text">{t("kb.uploadDocument")}</p>
      <input
        accept=".txt,.pdf,.docx,.md,.csv"
        className={kbFileInputClassName}
        data-testid="upload-file-input"
        id="kb-upload-file"
        name="file"
        onChange={event => onChangeFile(event.target.files?.[0] || null)}
        ref={fileInputRef}
        type="file"
      />
      <label className="file-picker-button hidden w-fit min-h-[36px] cursor-pointer items-center justify-center rounded-mc-pill border border-solid border-mc-border bg-mc-surface px-[10px] py-mc-2 text-mc-body-small font-mc-bold text-mc-text" htmlFor="kb-upload-file">
        {t("kb.uploadDocument")}
      </label>
      <p className="upload-drop-hint m-0 text-mc-caption text-mc-muted">{t("kb.dropUploadHint")}</p>
      <p className="selected-file m-0 text-mc-caption text-mc-muted [overflow-wrap:anywhere]">
        {selectedFile ? selectedFile.name : t("kb.noFile")}
      </p>
      {isUploading && (
        <div className="upload-progress h-[6px] overflow-hidden rounded-mc-pill bg-mc-surface" aria-label={t("kb.uploading")} role="progressbar">
          <span className="block h-full w-[44%] animate-[upload-progress-slide_1.1s_ease-in-out_infinite] rounded-[inherit] bg-[var(--color-accent-primary)] motion-reduce:animate-none" />
        </div>
      )}
      <button
        className={kbActionButtonClassName}
        data-testid="upload-file-button"
        disabled={isUploading || isSwitchingKnowledgeBase || !selectedFile}
        onClick={onUpload}
        type="button"
      >
        {isUploading ? t("chat.uploading") : t("kb.upload")}
      </button>
      <p className="upload-status m-0 text-mc-caption text-mc-muted [overflow-wrap:anywhere]" data-testid="upload-status">
        {uploadStatus || t("kb.uploadHint")}
      </p>
    </div>
  );
}

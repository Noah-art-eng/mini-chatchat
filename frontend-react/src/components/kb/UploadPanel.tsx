import type { RefObject } from "react";
import { useI18n } from "../../i18n";

type UploadPanelProps = {
  fileInputRef: RefObject<HTMLInputElement | null>;
  isUploading: boolean;
  onChangeFile: (file: File | null) => void;
  onUpload: () => void;
  selectedFile: File | null;
  uploadStatus: string | null;
};

/** 用途：负责 UploadPanel 的界面或数据处理职责。 */
export function UploadPanel({
  fileInputRef,
  isUploading,
  onChangeFile,
  onUpload,
  selectedFile,
  uploadStatus
}: UploadPanelProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div
      className={isUploading ? "upload-panel uploading" : "upload-panel"}
      onDragOver={event => {
        event.preventDefault();
      }}
      onDrop={event => {
        event.preventDefault();
        /** 用途：负责 onChangeFile 的界面或数据处理职责。 */
        onChangeFile(event.dataTransfer.files?.[0] || null);
      }}
    >
      <p className="section-kicker">{t("kb.addKnowledge")}</p>
      <p className="upload-label">{t("kb.uploadDocument")}</p>
      <input
        accept=".txt,.pdf,.docx,.md,.csv"
        className="native-file-input"
        data-testid="upload-file-input"
        id="kb-upload-file"
        name="file"
        onChange={event => onChangeFile(event.target.files?.[0] || null)}
        ref={fileInputRef}
        type="file"
      />
      <label className="file-picker-button" htmlFor="kb-upload-file">
        {t("kb.uploadDocument")}
      </label>
      <p className="upload-drop-hint">{t("kb.dropUploadHint")}</p>
      <p className="selected-file">
        {selectedFile ? selectedFile.name : t("kb.noFile")}
      </p>
      {isUploading && (
        <div className="upload-progress" aria-label={t("kb.uploading")} role="progressbar">
          <span />
        </div>
      )}
      <button
        data-testid="upload-file-button"
        disabled={isUploading || !selectedFile}
        onClick={onUpload}
        type="button"
      >
        {isUploading ? t("chat.uploading") : t("kb.upload")}
      </button>
      <p className="upload-status" data-testid="upload-status">
        {uploadStatus || t("kb.uploadHint")}
      </p>
    </div>
  );
}

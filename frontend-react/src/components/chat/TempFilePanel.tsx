import type { RefObject } from "react";
import { useI18n } from "../../i18n";

type TempFilePanelProps = {
  inputRef: RefObject<HTMLInputElement | null>;
  isUploading: boolean;
  onChangeFile: (file: File | null) => void;
  onUpload: () => void;
  selectedFile: File | null;
  status: string | null;
  tempFileName: string | null;
  tempKbId: string | null;
};

/** 用途：负责 TempFilePanel 的界面或数据处理职责。 */
export function TempFilePanel({
  inputRef,
  isUploading,
  onChangeFile,
  onUpload,
  selectedFile,
  status,
  tempFileName,
  tempKbId
}: TempFilePanelProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section className="temp-file-panel" data-testid="temp-file-mode-status">
      <div>
        <p className="eyebrow">{t("chat.tempModeStatus")}</p>
        <strong>
          {tempKbId && tempFileName
            ? `${tempFileName} · temp_kb_id: ${tempKbId}`
            : t("chat.disabledTempFile")}
        </strong>
      </div>
      <div className="temp-file-upload">
        <input
          accept=".txt,.pdf,.docx,.md,.csv"
          data-testid="temp-file-input"
          name="temp-file"
          onChange={event => {
            /** 用途：负责 onChangeFile 的界面或数据处理职责。 */
            onChangeFile(event.target.files?.[0] || null);
          }}
          ref={inputRef}
          type="file"
        />
        <button
          className="button-secondary"
          data-testid="temp-file-upload-button"
          disabled={isUploading || !selectedFile}
          onClick={onUpload}
          type="button"
        >
          {isUploading ? t("chat.uploading") : t("chat.uploadTempFile")}
        </button>
      </div>
      <p className="temp-file-status" data-testid="temp-file-status">
        {status ||
          (selectedFile
            ? `${t("chat.selectedTempFile")}: ${selectedFile.name}`
            : t("chat.noTempFile"))}
      </p>
    </section>
  );
}

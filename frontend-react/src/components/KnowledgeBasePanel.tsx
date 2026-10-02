import { useRef, useState } from "react";
import { useKbPanel } from "../hooks/useKbPanel";
import { useI18n } from "../i18n";
import { KnowledgeWorkspace } from "./kb";
import { useToast } from "./ui";
import { ConfirmDialog } from "./ConfirmDialog";

/** 用途：负责 KnowledgeBasePanel 的界面或数据处理职责。 */
export function KnowledgeBasePanel() {
  const { t } = useI18n();
  const { showToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const importInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedImportFile, setSelectedImportFile] = useState<File | null>(
    null
  );
  const [documentToDelete, setDocumentToDelete] = useState<string | null>(null);
  const {
    activeDocumentAction,
    createKnowledgeBaseByName,
    deleteKnowledgeFile,
    deleteKnowledgeBaseByName,
    documentActionStatus,
    documents,
    downloadKnowledgeFile,
    error,
    exportCurrentKnowledgeBase,
    importKnowledgeBaseFile,
    isLoading,
    isKbActionLoading,
    isUploading,
    kbActionStatus,
    kbName,
    knowledgeBases,
    refreshDocuments,
    reindexKnowledgeFile,
    selectKnowledgeBase,
    uploadKnowledgeFile,
    uploadStatus
  } = useKbPanel();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <>
    <KnowledgeWorkspace
      activeDocumentAction={activeDocumentAction}
      documentActionStatus={documentActionStatus}
      documents={documents}
      error={error}
      fileInputRef={fileInputRef}
      importInputRef={importInputRef}
      isKbActionLoading={isKbActionLoading}
      isLoading={isLoading}
      isUploading={isUploading}
      kbActionStatus={kbActionStatus}
      kbName={kbName}
      knowledgeBases={knowledgeBases}
      onChangeImportFile={setSelectedImportFile}
      onChangeUploadFile={setSelectedFile}
      onCreateKnowledgeBase={createKnowledgeBaseByName}
      onDeleteKnowledgeBase={deleteKnowledgeBaseByName}
      onDeleteDocument={filename => {
        setDocumentToDelete(filename);
      }}
      onDownloadDocument={filename => {
        void downloadKnowledgeFile(filename).then(downloaded => {
          showToast({
            message: downloaded
              ? t("kb.downloadSuccess", { name: filename })
              : t("kb.downloadFailed"),
            variant: downloaded ? "success" : "error"
          });
        });
      }}
      onExportKb={() => {
        void exportCurrentKnowledgeBase().then(exported => {
          showToast({
            message: exported
              ? t("kb.exportSuccess", { name: kbName })
              : t("kb.exportFailed"),
            variant: exported ? "success" : "error"
          });
        });
      }}
      onImportKb={() => {
        /** 用途：负责 void 的界面或数据处理职责。 */
        void (async () => {
          const didImport = await importKnowledgeBaseFile(selectedImportFile);

          if (didImport) {
            /** 用途：负责 showToast 的界面或数据处理职责。 */
            showToast({ message: t("kb.importSuccess"), variant: "success" });
            /** 用途：负责 setSelectedImportFile 的界面或数据处理职责。 */
            setSelectedImportFile(null);
            if (importInputRef.current) {
              importInputRef.current.value = "";
            }
          } else {
            /** 用途：负责 showToast 的界面或数据处理职责。 */
            showToast({ message: t("kb.importFailed"), variant: "error" });
          }
        })();
      }}
      onRefreshDocuments={() => {
        void refreshDocuments()
          .then(() => showToast({ message: t("kb.refreshSuccess"), variant: "success" }))
          .catch(error => {
            console.error(error);
            /** 用途：负责 showToast 的界面或数据处理职责。 */
            showToast({ message: t("kb.refreshFailed"), variant: "error" });
          });
      }}
      onReindexDocument={file => {
        void reindexKnowledgeFile(file).then(reindexed => {
          showToast({
            message: reindexed
              ? t("kb.reindexSuccess", { name: file.filename })
              : t("kb.reindexFailed"),
            variant: reindexed ? "success" : "error"
          });
        });
      }}
      onSelectKnowledgeBase={nextKbName => {
        void selectKnowledgeBase(nextKbName);
      }}
      onUploadDocument={() => {
        /** 用途：负责 void 的界面或数据处理职责。 */
        void (async () => {
          const didUpload = await uploadKnowledgeFile(selectedFile);

          if (didUpload) {
            /** 用途：负责 showToast 的界面或数据处理职责。 */
            showToast({ message: t("kb.uploadSuccess"), variant: "success" });
            /** 用途：负责 setSelectedFile 的界面或数据处理职责。 */
            setSelectedFile(null);
            if (fileInputRef.current) {
              fileInputRef.current.value = "";
            }
          } else {
            /** 用途：负责 showToast 的界面或数据处理职责。 */
            showToast({ message: t("kb.uploadFailed"), variant: "error" });
          }
        })();
      }}
      selectedFile={selectedFile}
      selectedImportFile={selectedImportFile}
      uploadStatus={uploadStatus}
    />
    <ConfirmDialog
      confirmLabel={t("kb.delete")}
      description={t("kb.confirmDeleteDocument", { name: documentToDelete || "" })}
      isOpen={documentToDelete !== null}
      onCancel={() => setDocumentToDelete(null)}
      onConfirm={() => {
        const filename = documentToDelete;
        if (!filename) return;
        setDocumentToDelete(null);
        void deleteKnowledgeFile(filename).then(deleted => {
          showToast({
            message: deleted ? t("kb.deleteSuccess", { name: filename }) : t("kb.deleteFailed"),
            variant: deleted ? "success" : "error"
          });
        });
      }}
      title={t("kb.confirmDeleteDocumentTitle")}
    />
    </>
  );
}

import type { RefObject } from "react";
import { useMemo, useState } from "react";
import { ContextPanel } from "../ContextPanel";
import { RetrievalDebugPanel } from "../RetrievalDebugPanel";
import { DeveloperModeIntroDialog } from "../onboarding";
import { useI18n } from "../../i18n";
import {
  isDeveloperModeIntroSeen,
  setDeveloperModeIntroSeen
} from "../../onboarding/preferences";
import type { KnowledgeBase, KnowledgeFile } from "../../types/kb";
import { DocumentDetailPanel } from "./DocumentDetailPanel";
import { DocumentTable } from "./DocumentTable";
import { KnowledgeBackupActions } from "./KnowledgeBackupActions";
import { KnowledgeBaseList } from "./KnowledgeBaseList";
import { KnowledgeHeader } from "./KnowledgeHeader";
import { KnowledgeStats } from "./KnowledgeStats";
import { KnowledgeToolbar } from "./KnowledgeToolbar";
import { UploadPanel } from "./UploadPanel";
import { ConfirmDialog } from "../ConfirmDialog";

type KnowledgeWorkspaceProps = {
  activeDocumentAction: string | null;
  documentActionStatus: string | null;
  documents: KnowledgeFile[];
  error: string | null;
  fileInputRef: RefObject<HTMLInputElement | null>;
  importInputRef: RefObject<HTMLInputElement | null>;
  isKbActionLoading: boolean;
  isLoading: boolean;
  isUploading: boolean;
  kbActionStatus: string | null;
  kbName: string;
  knowledgeBases: KnowledgeBase[];
  onChangeImportFile: (file: File | null) => void;
  onChangeUploadFile: (file: File | null) => void;
  onCreateKnowledgeBase: (name: string) => Promise<boolean>;
  onDeleteKnowledgeBase: (name: string) => Promise<boolean>;
  onDeleteDocument: (filename: string) => void;
  onDownloadDocument: (filename: string) => void;
  onExportKb: () => void;
  onImportKb: () => void;
  onRefreshDocuments: () => void;
  onReindexDocument: (file: KnowledgeFile) => void;
  onSelectKnowledgeBase: (kbName: string) => void;
  onUploadDocument: () => void;
  selectedFile: File | null;
  selectedImportFile: File | null;
  uploadStatus: string | null;
};

/** 用途：负责 KnowledgeWorkspace 的界面或数据处理职责。 */
export function KnowledgeWorkspace({
  activeDocumentAction,
  documentActionStatus,
  documents,
  error,
  fileInputRef,
  importInputRef,
  isKbActionLoading,
  isLoading,
  isUploading,
  kbActionStatus,
  kbName,
  knowledgeBases,
  onChangeImportFile,
  onChangeUploadFile,
  onCreateKnowledgeBase,
  onDeleteKnowledgeBase,
  onDeleteDocument,
  onDownloadDocument,
  onExportKb,
  onImportKb,
  onRefreshDocuments,
  onReindexDocument,
  onSelectKnowledgeBase,
  onUploadDocument,
  selectedFile,
  selectedImportFile,
  uploadStatus
}: KnowledgeWorkspaceProps) {
  const { t } = useI18n();
  const [activeContextTab, setActiveContextTab] = useState("document");
  const [isContextOpen, setIsContextOpen] = useState(false);
  const [isDeveloperMode, setIsDeveloperMode] = useState(false);
  const [isDeveloperIntroOpen, setIsDeveloperIntroOpen] = useState(false);
  const [newKbName, setNewKbName] = useState("");
  const [isDeleteKbOpen, setIsDeleteKbOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeFile | null>(
    documents[0] || null
  );
  const selectedDocumentFromList = useMemo(
    () =>
      documents.find(document => document.filename === selectedDocument?.filename) ||
      documents[0] ||
      null,
    [documents, selectedDocument]
  );
  const indexedCount = documents.filter(file => file.status === "indexed").length;
  const failedCount = documents.filter(file => file.status === "failed").length;
  const totalChunks = documents.reduce(
    (count, file) => count + (file.docs_count ?? 0),
    0
  );

  /** 用途：负责 toggleDeveloperMode 的界面或数据处理职责。 */
  function toggleDeveloperMode() {
    if (isDeveloperMode) {
      /** 用途：负责 setIsDeveloperMode 的界面或数据处理职责。 */
      setIsDeveloperMode(false);
      if (activeContextTab === "debug") {
        /** 用途：负责 setActiveContextTab 的界面或数据处理职责。 */
        setActiveContextTab("document");
        /** 用途：负责 setIsContextOpen 的界面或数据处理职责。 */
        setIsContextOpen(false);
      }
      return;
    }

    if (isDeveloperModeIntroSeen()) {
      /** 用途：负责 setIsDeveloperMode 的界面或数据处理职责。 */
      setIsDeveloperMode(true);
      return;
    }

    /** 用途：负责 setIsDeveloperIntroOpen 的界面或数据处理职责。 */
    setIsDeveloperIntroOpen(true);
  }

  /** 用途：负责 confirmDeveloperMode 的界面或数据处理职责。 */
  function confirmDeveloperMode() {
    /** 用途：负责 setDeveloperModeIntroSeen 的界面或数据处理职责。 */
    setDeveloperModeIntroSeen(true);
    /** 用途：负责 setIsDeveloperMode 的界面或数据处理职责。 */
    setIsDeveloperMode(true);
    /** 用途：负责 setIsDeveloperIntroOpen 的界面或数据处理职责。 */
    setIsDeveloperIntroOpen(false);
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section className="page-surface knowledge-workspace" aria-label={t("kb.title")}>
      <KnowledgeHeader />
      <div
        className={
          isContextOpen
            ? "kb-page-grid context-open"
            : "kb-page-grid context-collapsed"
        }
      >
        <section
          aria-label={t("kb.title")}
          className="kb-panel-page"
          data-testid="kb-panel"
          id="kb-panel"
        >
          <div className="kb-panel">
            <div className="panel-heading">
              <p className="eyebrow">{t("kb.current")}</p>
              <h2>{t("kb.files")}</h2>
              <p>{t("kb.workspaceSummary")}</p>
            </div>

            <div className="current-kb" data-testid="current-kb">
              <span>{t("kb.current")}</span>
              <strong>{kbName}</strong>
            </div>

            <KnowledgeStats
              documentsCount={documents.length}
              failedCount={failedCount}
              indexedCount={indexedCount}
              totalChunks={totalChunks}
            />

            <KnowledgeBaseList
              currentKb={kbName}
              isLoading={isLoading}
              knowledgeBases={knowledgeBases}
              onSelectKnowledgeBase={onSelectKnowledgeBase}
            />

            <div className="kb-lifecycle-actions">
              <label>
                <span>{t("kb.newKbName")}</span>
                <input
                  disabled={isKbActionLoading}
                  onChange={event => setNewKbName(event.target.value)}
                  placeholder={t("kb.newKbPlaceholder")}
                  value={newKbName}
                />
              </label>
              <button
                disabled={isKbActionLoading || !newKbName.trim()}
                onClick={() => {
                  void onCreateKnowledgeBase(newKbName).then(created => {
                    if (created) setNewKbName("");
                  });
                }}
                type="button"
              >
                {t("kb.createKb")}
              </button>
              <button
                className="danger"
                disabled={isKbActionLoading || kbName === "default"}
                onClick={() => setIsDeleteKbOpen(true)}
                type="button"
              >
                {t("kb.deleteKb")}
              </button>
            </div>

            {isLoading && <p className="muted">{t("kb.loading")}</p>}
            {isLoading && (
              <div className="skeleton-grid" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
            )}
            {error && <p className="inline-error">{error}</p>}
            {documentActionStatus && (
              <p
                className="document-action-status"
                data-testid="document-action-status"
              >
                {documentActionStatus}
              </p>
            )}

            <KnowledgeBackupActions
              importInputRef={importInputRef}
              isKbActionLoading={isKbActionLoading}
              kbActionStatus={kbActionStatus}
              onChangeImportFile={onChangeImportFile}
              onExport={onExportKb}
              onImport={onImportKb}
              selectedImportFile={selectedImportFile}
            />

            <KnowledgeToolbar
              isDeveloperMode={isDeveloperMode}
              isLoading={isLoading}
              onOpenDebug={() => {
                /** 用途：负责 setActiveContextTab 的界面或数据处理职责。 */
                setActiveContextTab("debug");
                /** 用途：负责 setIsContextOpen 的界面或数据处理职责。 */
                setIsContextOpen(true);
              }}
              onOpenDetails={() => {
                /** 用途：负责 setActiveContextTab 的界面或数据处理职责。 */
                setActiveContextTab("document");
                /** 用途：负责 setIsContextOpen 的界面或数据处理职责。 */
                setIsContextOpen(true);
              }}
              onRefreshDocuments={onRefreshDocuments}
              onToggleDeveloperMode={toggleDeveloperMode}
            />

            <UploadPanel
              fileInputRef={fileInputRef}
              isUploading={isUploading}
              onChangeFile={onChangeUploadFile}
              onUpload={onUploadDocument}
              selectedFile={selectedFile}
              uploadStatus={uploadStatus}
            />

            <DocumentTable
              activeDocumentAction={activeDocumentAction}
              documents={documents}
              hasKnowledgeBase={knowledgeBases.length > 0}
              isLoading={isLoading}
              onDelete={onDeleteDocument}
              onDownload={onDownloadDocument}
              onReindex={onReindexDocument}
              onSelectDocument={file => {
                /** 用途：负责 setSelectedDocument 的界面或数据处理职责。 */
                setSelectedDocument(file);
                /** 用途：负责 setActiveContextTab 的界面或数据处理职责。 */
                setActiveContextTab("document");
                /** 用途：负责 setIsContextOpen 的界面或数据处理职责。 */
                setIsContextOpen(true);
              }}
              selectedDocument={selectedDocumentFromList}
            />
          </div>
        </section>

        <ContextPanel
          activeTab={activeContextTab}
          ariaLabel={t("kb.title")}
          isOpen={isContextOpen}
          onChangeTab={setActiveContextTab}
          onClose={() => setIsContextOpen(false)}
          onOpen={() => setIsContextOpen(true)}
          tabs={[
            { id: "document", label: t("kb.managedFile") },
            ...(isDeveloperMode ? [{ id: "debug", label: t("kb.debugTab") }] : [])
          ]}
          title={
            activeContextTab === "debug" ? t("kb.debugTab") : t("kb.managedFile")
          }
          workspace="knowledge"
        >
          {activeContextTab === "debug" ? (
            <RetrievalDebugPanel />
          ) : (
            <DocumentDetailPanel
              document={selectedDocumentFromList}
              documentsCount={documents.length}
              failedCount={failedCount}
              indexedCount={indexedCount}
              totalChunks={totalChunks}
            />
          )}
        </ContextPanel>
      </div>
      <DeveloperModeIntroDialog
        isOpen={isDeveloperIntroOpen}
        onCancel={() => setIsDeveloperIntroOpen(false)}
        onConfirm={confirmDeveloperMode}
      />
      <ConfirmDialog
        confirmLabel={t("kb.deleteKb")}
        description={t("kb.confirmDeleteKbDescription", { name: kbName })}
        isLoading={isKbActionLoading}
        isOpen={isDeleteKbOpen}
        onCancel={() => setIsDeleteKbOpen(false)}
        onConfirm={() => {
          void onDeleteKnowledgeBase(kbName).then(deleted => {
            if (deleted) setIsDeleteKbOpen(false);
          });
        }}
        title={t("kb.confirmDeleteKbTitle")}
      />
    </section>
  );
}

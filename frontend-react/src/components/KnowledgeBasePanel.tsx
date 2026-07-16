import { useRef, useState } from "react";
import { RetrievalDebugPanel } from "./RetrievalDebugPanel";
import { SourcesPanel } from "./SourcesPanel";
import { useKbPanel } from "../hooks/useKbPanel";

function safeFileName(filename: string) {
  return filename.replace(/[^a-zA-Z0-9._-]/g, "-");
}

export function KnowledgeBasePanel() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const importInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedImportFile, setSelectedImportFile] = useState<File | null>(
    null
  );
  const {
    activeDocumentAction,
    deleteKnowledgeFile,
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

  return (
    <section
      aria-label="Sources and KB panel"
      className="right-panel"
      data-testid="kb-panel"
      id="kb-panel"
    >
      <SourcesPanel />
      <RetrievalDebugPanel />

      <div className="kb-panel">
        <div className="panel-heading">
          <p className="eyebrow">Knowledge Base</p>
          <h2>Documents</h2>
        </div>

        <div className="current-kb" data-testid="current-kb">
          Current KB: <strong>{kbName}</strong>
        </div>

        <div className="kb-list" data-testid="kb-list">
          {knowledgeBases.map(kb => (
            <button
              className={kb.kb_name === kbName ? "kb-option active" : "kb-option"}
              data-testid={`kb-option-${kb.kb_name}`}
              key={kb.kb_name}
              onClick={() => {
                void selectKnowledgeBase(kb.kb_name);
              }}
              type="button"
            >
              <span>{kb.kb_name}</span>
              {kb.embed_model && <small>{kb.embed_model}</small>}
            </button>
          ))}
        </div>

        {knowledgeBases.length === 0 && !isLoading && (
          <p className="muted">No knowledge bases found.</p>
        )}

        <label className="kb-selector">
          Quick select
          <select
            onChange={event => {
              void selectKnowledgeBase(event.target.value);
            }}
            value={kbName}
          >
            {knowledgeBases.map(kb => (
              <option key={kb.kb_name} value={kb.kb_name}>
                {kb.kb_name}
              </option>
            ))}
          </select>
        </label>

        {isLoading && <p className="muted">Loading KB data...</p>}
        {error && <p className="inline-error">{error}</p>}
        {documentActionStatus && (
          <p className="document-action-status" data-testid="document-action-status">
            {documentActionStatus}
          </p>
        )}

        <div className="kb-action-panel">
          <button
            data-testid="export-kb-button"
            disabled={isKbActionLoading}
            onClick={() => {
              void exportCurrentKnowledgeBase();
            }}
            type="button"
          >
            {isKbActionLoading ? "Working" : "Export KB"}
          </button>

          <p className="upload-label">Import knowledge base</p>
          <input
            accept=".zip,.json"
            className="native-file-input"
            data-testid="import-kb-input"
            onChange={event => {
              setSelectedImportFile(event.target.files?.[0] || null);
            }}
            ref={importInputRef}
            type="file"
          />
          <p className="selected-file">
            {selectedImportFile ? selectedImportFile.name : "No import file selected"}
          </p>
          <button
            data-testid="import-kb-button"
            disabled={isKbActionLoading || !selectedImportFile}
            onClick={async () => {
              const didImport = await importKnowledgeBaseFile(selectedImportFile);

              if (didImport) {
                setSelectedImportFile(null);
                if (importInputRef.current) {
                  importInputRef.current.value = "";
                }
              }
            }}
            type="button"
          >
            {isKbActionLoading ? "Importing" : "Import KB"}
          </button>

          {kbActionStatus && (
            <p className="upload-status" data-testid="kb-action-status">
              {kbActionStatus}
            </p>
          )}
        </div>

        <button
          className="refresh-documents-button"
          data-testid="refresh-documents-button"
          disabled={isLoading}
          onClick={() => {
            void refreshDocuments();
          }}
          type="button"
        >
          Refresh Documents
        </button>

        <div className="upload-panel">
          <p className="upload-label">Upload document</p>
          <input
            accept=".txt,.pdf,.docx,.md,.csv"
            className="native-file-input"
            data-testid="upload-file-input"
            id="kb-upload-file"
            name="file"
            onChange={event => {
              setSelectedFile(event.target.files?.[0] || null);
            }}
            ref={fileInputRef}
            type="file"
          />
          <p className="selected-file">
            {selectedFile ? selectedFile.name : "No file selected"}
          </p>
          <button
            data-testid="upload-file-button"
            disabled={isUploading || !selectedFile}
            onClick={async () => {
              const didUpload = await uploadKnowledgeFile(selectedFile);

              if (didUpload) {
                setSelectedFile(null);
                if (fileInputRef.current) {
                  fileInputRef.current.value = "";
                }
              }
            }}
            type="button"
          >
            {isUploading ? "Uploading" : "Upload"}
          </button>
          <p className="upload-status" data-testid="upload-status">
            {uploadStatus || "Supports .txt, .pdf, .docx, .md, .csv"}
          </p>
        </div>

        {!isLoading && documents.length === 0 && (
          <p className="muted">No documents in this knowledge base yet.</p>
        )}

        <div className="document-list" data-testid="documents" id="documents">
          {documents.map(file => {
            const safeName = safeFileName(file.filename);
            const isDownloading =
              activeDocumentAction === `download:${file.filename}`;
            const isReindexing =
              activeDocumentAction === `reindex:${file.filename}`;

            return (
              <article
                className="document-row"
                data-testid={`document-row-${safeName}`}
                key={file.filename}
              >
                <div>
                  <strong data-testid={`document-filename-${safeName}`}>
                    {file.filename}
                  </strong>
                  <span
                    className={`status status-${file.status || "unknown"}`}
                    data-testid={`document-status-${safeName}`}
                  >
                    {file.status || "unknown"}
                  </span>
                </div>
                <dl>
                  <div>
                    <dt>Chunks</dt>
                    <dd data-testid={`document-chunks-${safeName}`}>
                      {file.docs_count ?? 0}
                    </dd>
                  </div>
                  <div>
                    <dt>Size</dt>
                    <dd>{file.chunk_size ?? "-"}</dd>
                  </div>
                  <div>
                    <dt>Overlap</dt>
                    <dd>{file.chunk_overlap ?? "-"}</dd>
                  </div>
                </dl>
                <div className="document-actions">
                  <button
                    data-testid={`download-document-${safeName}`}
                    disabled={Boolean(activeDocumentAction)}
                    onClick={() => {
                      void downloadKnowledgeFile(file.filename);
                    }}
                    type="button"
                  >
                    {isDownloading ? "Downloading" : "Download"}
                  </button>
                  <button
                    data-testid={`reindex-document-${safeName}`}
                    disabled={Boolean(activeDocumentAction)}
                    onClick={() => {
                      void reindexKnowledgeFile(file);
                    }}
                    type="button"
                  >
                    {isReindexing ? "Reindexing" : "Reindex"}
                  </button>
                  <button
                    data-testid={`delete-document-${safeName}`}
                    disabled={Boolean(activeDocumentAction)}
                    onClick={() => {
                      void deleteKnowledgeFile(file.filename);
                    }}
                    type="button"
                  >
                    {activeDocumentAction === `delete:${file.filename}`
                      ? "Deleting"
                      : "Delete"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

import { useCallback, useEffect, useState } from "react";
import {
  deleteDocument,
  downloadDocument,
  exportKnowledgeBase,
  importKnowledgeBase,
  listDocuments,
  listKnowledgeBases,
  reindexDocument,
  switchKnowledgeBase,
  uploadDocument
} from "../api/kb";
import { useConversationStore } from "../stores/conversationStore";
import type { KnowledgeBase, KnowledgeFile } from "../types/kb";

export function useKbPanel() {
  const { kbName, setKbName } = useConversationStore();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [documents, setDocuments] = useState<KnowledgeFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [activeDocumentAction, setActiveDocumentAction] = useState<
    string | null
  >(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [documentActionStatus, setDocumentActionStatus] = useState<
    string | null
  >(null);
  const [isKbActionLoading, setIsKbActionLoading] = useState(false);
  const [kbActionStatus, setKbActionStatus] = useState<string | null>(null);

  const refreshDocuments = useCallback(async () => {
    const data = await listDocuments();
    setDocuments(data.files);
  }, []);

  const refreshKnowledgeBases = useCallback(async () => {
    const data = await listKnowledgeBases();
    setKnowledgeBases(data.knowledge_bases);

    if (!data.knowledge_bases.some(kb => kb.kb_name === kbName)) {
      const nextKbName = data.knowledge_bases[0]?.kb_name || "default";
      setKbName(nextKbName);
    }
  }, [kbName, setKbName]);

  const selectKnowledgeBase = useCallback(
    async (nextKbName: string) => {
      setIsLoading(true);
      setError(null);
      try {
        await switchKnowledgeBase(nextKbName);
        setKbName(nextKbName);
        await refreshDocuments();
      } catch (selectError) {
        const message =
          selectError instanceof Error
            ? selectError.message
            : "Failed to switch knowledge base.";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [refreshDocuments, setKbName]
  );

  const uploadKnowledgeFile = useCallback(
    async (file: File | null) => {
      if (!file) {
        setUploadStatus("Choose a file first.");
        return false;
      }

      setIsUploading(true);
      setError(null);
      setUploadStatus(`Uploading ${file.name}...`);

      try {
        const result = await uploadDocument(file);

        if (result.error) {
          setUploadStatus(result.error);
          setError(result.error);
          return false;
        }

        setUploadStatus(result.message || `${file.name} uploaded.`);
        await refreshDocuments();
        return true;
      } catch (uploadError) {
        const message =
          uploadError instanceof Error ? uploadError.message : "Upload failed.";
        setUploadStatus(message);
        setError(message);
        return false;
      } finally {
        setIsUploading(false);
      }
    },
    [refreshDocuments]
  );

  const downloadKnowledgeFile = useCallback(async (filename: string) => {
    setActiveDocumentAction(`download:${filename}`);
    setError(null);
    setDocumentActionStatus(`Downloading ${filename}...`);

    try {
      await downloadDocument(filename);
      setDocumentActionStatus(`${filename} download started.`);
    } catch (downloadError) {
      const message =
        downloadError instanceof Error
          ? downloadError.message
          : "Download failed.";
      setDocumentActionStatus(message);
      setError(message);
    } finally {
      setActiveDocumentAction(null);
    }
  }, []);

  const reindexKnowledgeFile = useCallback(
    async (file: KnowledgeFile) => {
      setActiveDocumentAction(`reindex:${file.filename}`);
      setError(null);
      setDocumentActionStatus(`Reindexing ${file.filename}...`);

      try {
        const result = await reindexDocument(
          file.filename,
          file.chunk_size || 300,
          file.chunk_overlap || 50
        );

        if (result.error) {
          setDocumentActionStatus(result.error);
          setError(result.error);
          return;
        }

        setDocumentActionStatus(
          result.message || `${file.filename} reindexed.`
        );
        await refreshDocuments();
      } catch (reindexError) {
        const message =
          reindexError instanceof Error
            ? reindexError.message
            : "Reindex failed.";
        setDocumentActionStatus(message);
        setError(message);
      } finally {
        setActiveDocumentAction(null);
      }
    },
    [refreshDocuments]
  );

  const deleteKnowledgeFile = useCallback(
    async (filename: string) => {
      setActiveDocumentAction(`delete:${filename}`);
      setError(null);
      setDocumentActionStatus(`Deleting ${filename}...`);

      try {
        const result = await deleteDocument(filename);

        if (result.error) {
          setDocumentActionStatus(result.error);
          setError(result.error);
          return;
        }

        setDocumentActionStatus(result.message || `${filename} deleted.`);
        await refreshDocuments();
      } catch (deleteError) {
        const message =
          deleteError instanceof Error ? deleteError.message : "Delete failed.";
        setDocumentActionStatus(message);
        setError(message);
      } finally {
        setActiveDocumentAction(null);
      }
    },
    [refreshDocuments]
  );

  const exportCurrentKnowledgeBase = useCallback(async () => {
    setIsKbActionLoading(true);
    setError(null);
    setKbActionStatus(`Exporting ${kbName}...`);

    try {
      await exportKnowledgeBase(kbName);
      setKbActionStatus(`${kbName} export started.`);
    } catch (exportError) {
      const message =
        exportError instanceof Error ? exportError.message : "Export failed.";
      setKbActionStatus(message);
      setError(message);
    } finally {
      setIsKbActionLoading(false);
    }
  }, [kbName]);

  const importKnowledgeBaseFile = useCallback(
    async (file: File | null) => {
      if (!file) {
        setKbActionStatus("Choose a KB export file first.");
        return false;
      }

      setIsKbActionLoading(true);
      setError(null);
      setKbActionStatus(`Importing ${file.name}...`);

      try {
        const result = await importKnowledgeBase(file);

        if (result.error) {
          setKbActionStatus(result.error);
          setError(result.error);
          return false;
        }

        setKbActionStatus(
          result.kb_name
            ? `${result.kb_name} imported.`
            : `${file.name} imported.`
        );
        await refreshKnowledgeBases();
        if (result.kb_name) {
          await selectKnowledgeBase(result.kb_name);
        } else {
          await refreshDocuments();
        }
        return true;
      } catch (importError) {
        const message =
          importError instanceof Error ? importError.message : "Import failed.";
        setKbActionStatus(message);
        setError(message);
        return false;
      } finally {
        setIsKbActionLoading(false);
      }
    },
    [refreshDocuments, refreshKnowledgeBases, selectKnowledgeBase]
  );

  useEffect(() => {
    let ignore = false;

    async function loadKbPanel() {
      setIsLoading(true);
      setError(null);
      try {
        const [kbData, documentData] = await Promise.all([
          listKnowledgeBases(),
          listDocuments()
        ]);

        if (ignore) return;

        setKnowledgeBases(kbData.knowledge_bases);
        setDocuments(documentData.files);
      } catch (loadError) {
        if (ignore) return;
        const message =
          loadError instanceof Error
            ? loadError.message
            : "Failed to load knowledge base data.";
        setError(message);
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadKbPanel().catch(console.error);

    return () => {
      ignore = true;
    };
  }, []);

  return {
    documents,
    activeDocumentAction,
    deleteKnowledgeFile,
    documentActionStatus,
    downloadKnowledgeFile,
    error,
    exportCurrentKnowledgeBase,
    isLoading,
    isKbActionLoading,
    isUploading,
    importKnowledgeBaseFile,
    kbActionStatus,
    kbName,
    knowledgeBases,
    refreshDocuments,
    refreshKnowledgeBases,
    selectKnowledgeBase,
    reindexKnowledgeFile,
    uploadKnowledgeFile,
    uploadStatus
  };
}

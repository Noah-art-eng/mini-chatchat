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

/** 用途：负责 useKbPanel 的界面或数据处理职责。 */
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
    /** 用途：负责 setDocuments 的界面或数据处理职责。 */
    setDocuments(data.files);
  }, []);

  const refreshKnowledgeBases = useCallback(async () => {
    const data = await listKnowledgeBases();
    /** 用途：负责 setKnowledgeBases 的界面或数据处理职责。 */
    setKnowledgeBases(data.knowledge_bases);

    if (!data.knowledge_bases.some(kb => kb.kb_name === kbName)) {
      const nextKbName = data.knowledge_bases[0]?.kb_name || "default";
      /** 用途：负责 setKbName 的界面或数据处理职责。 */
      setKbName(nextKbName);
    }
  }, [kbName, setKbName]);

  const selectKnowledgeBase = useCallback(
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (nextKbName: string) => {
      /** 用途：负责 setIsLoading 的界面或数据处理职责。 */
      setIsLoading(true);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(null);
      try {
        await switchKnowledgeBase(nextKbName);
        /** 用途：负责 setKbName 的界面或数据处理职责。 */
        setKbName(nextKbName);
        await refreshDocuments();
      } catch (selectError) {
        const message =
          selectError instanceof Error
            ? selectError.message
            : "Failed to switch knowledge base.";
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(message);
      } finally {
        /** 用途：负责 setIsLoading 的界面或数据处理职责。 */
        setIsLoading(false);
      }
    },
    [refreshDocuments, setKbName]
  );

  const uploadKnowledgeFile = useCallback(
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (file: File | null) => {
      if (!file) {
        /** 用途：负责 setUploadStatus 的界面或数据处理职责。 */
        setUploadStatus("Choose a file first.");
        return false;
      }

      /** 用途：负责 setIsUploading 的界面或数据处理职责。 */
      setIsUploading(true);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(null);
      /** 用途：负责 setUploadStatus 的界面或数据处理职责。 */
      setUploadStatus(`Uploading ${file.name}...`);

      try {
        const result = await uploadDocument(file);

        if (result.error) {
          /** 用途：负责 setUploadStatus 的界面或数据处理职责。 */
          setUploadStatus(result.error);
          /** 用途：负责 setError 的界面或数据处理职责。 */
          setError(result.error);
          return false;
        }

        /** 用途：负责 setUploadStatus 的界面或数据处理职责。 */
        setUploadStatus(result.message || `${file.name} uploaded.`);
        await refreshDocuments();
        return true;
      } catch (uploadError) {
        const message =
          uploadError instanceof Error ? uploadError.message : "Upload failed.";
        /** 用途：负责 setUploadStatus 的界面或数据处理职责。 */
        setUploadStatus(message);
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(message);
        return false;
      } finally {
        /** 用途：负责 setIsUploading 的界面或数据处理职责。 */
        setIsUploading(false);
      }
    },
    [refreshDocuments]
  );

  const downloadKnowledgeFile = useCallback(async (filename: string) => {
    /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
    setActiveDocumentAction(`download:${filename}`);
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);
    /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
    setDocumentActionStatus(`Downloading ${filename}...`);

    try {
      await downloadDocument(filename);
      /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
      setDocumentActionStatus(`${filename} download started.`);
    } catch (downloadError) {
      const message =
        downloadError instanceof Error
          ? downloadError.message
          : "Download failed.";
      /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
      setDocumentActionStatus(message);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(message);
    } finally {
      /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
      setActiveDocumentAction(null);
    }
  }, []);

  const reindexKnowledgeFile = useCallback(
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (file: KnowledgeFile) => {
      /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
      setActiveDocumentAction(`reindex:${file.filename}`);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(null);
      /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
      setDocumentActionStatus(`Reindexing ${file.filename}...`);

      try {
        const result = await reindexDocument(
          file.filename,
          file.chunk_size || 300,
          file.chunk_overlap || 50
        );

        if (result.error) {
          /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
          setDocumentActionStatus(result.error);
          /** 用途：负责 setError 的界面或数据处理职责。 */
          setError(result.error);
          return;
        }

        /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
        setDocumentActionStatus(
          result.message || `${file.filename} reindexed.`
        );
        await refreshDocuments();
      } catch (reindexError) {
        const message =
          reindexError instanceof Error
            ? reindexError.message
            : "Reindex failed.";
        /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
        setDocumentActionStatus(message);
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(message);
      } finally {
        /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
        setActiveDocumentAction(null);
      }
    },
    [refreshDocuments]
  );

  const deleteKnowledgeFile = useCallback(
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (filename: string) => {
      /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
      setActiveDocumentAction(`delete:${filename}`);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(null);
      /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
      setDocumentActionStatus(`Deleting ${filename}...`);

      try {
        const result = await deleteDocument(filename);

        if (result.error) {
          /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
          setDocumentActionStatus(result.error);
          /** 用途：负责 setError 的界面或数据处理职责。 */
          setError(result.error);
          return;
        }

        /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
        setDocumentActionStatus(result.message || `${filename} deleted.`);
        await refreshDocuments();
      } catch (deleteError) {
        const message =
          deleteError instanceof Error ? deleteError.message : "Delete failed.";
        /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
        setDocumentActionStatus(message);
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(message);
      } finally {
        /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
        setActiveDocumentAction(null);
      }
    },
    [refreshDocuments]
  );

  const exportCurrentKnowledgeBase = useCallback(async () => {
    /** 用途：负责 setIsKbActionLoading 的界面或数据处理职责。 */
    setIsKbActionLoading(true);
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);
    /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
    setKbActionStatus(`Exporting ${kbName}...`);

    try {
      await exportKnowledgeBase(kbName);
      /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
      setKbActionStatus(`${kbName} export started.`);
    } catch (exportError) {
      const message =
        exportError instanceof Error ? exportError.message : "Export failed.";
      /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
      setKbActionStatus(message);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(message);
    } finally {
      /** 用途：负责 setIsKbActionLoading 的界面或数据处理职责。 */
      setIsKbActionLoading(false);
    }
  }, [kbName]);

  const importKnowledgeBaseFile = useCallback(
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (file: File | null) => {
      if (!file) {
        /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
        setKbActionStatus("Choose a KB export file first.");
        return false;
      }

      /** 用途：负责 setIsKbActionLoading 的界面或数据处理职责。 */
      setIsKbActionLoading(true);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(null);
      /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
      setKbActionStatus(`Importing ${file.name}...`);

      try {
        const result = await importKnowledgeBase(file);

        if (result.error) {
          /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
          setKbActionStatus(result.error);
          /** 用途：负责 setError 的界面或数据处理职责。 */
          setError(result.error);
          return false;
        }

        /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
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
        /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
        setKbActionStatus(message);
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(message);
        return false;
      } finally {
        /** 用途：负责 setIsKbActionLoading 的界面或数据处理职责。 */
        setIsKbActionLoading(false);
      }
    },
    [refreshDocuments, refreshKnowledgeBases, selectKnowledgeBase]
  );

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    let ignore = false;

    /** 用途：负责 loadKbPanel 的界面或数据处理职责。 */
    async function loadKbPanel() {
      /** 用途：负责 setIsLoading 的界面或数据处理职责。 */
      setIsLoading(true);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(null);
      try {
        const [kbData, documentData] = await Promise.all([
          /** 用途：负责 listKnowledgeBases 的界面或数据处理职责。 */
          listKnowledgeBases(),
          /** 用途：负责 listDocuments 的界面或数据处理职责。 */
          listDocuments()
        ]);

        if (ignore) return;

        /** 用途：负责 setKnowledgeBases 的界面或数据处理职责。 */
        setKnowledgeBases(kbData.knowledge_bases);
        /** 用途：负责 setDocuments 的界面或数据处理职责。 */
        setDocuments(documentData.files);
      } catch (loadError) {
        if (ignore) return;
        const message =
          loadError instanceof Error
            ? loadError.message
            : "Failed to load knowledge base data.";
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(message);
      } finally {
        if (!ignore) {
          /** 用途：负责 setIsLoading 的界面或数据处理职责。 */
          setIsLoading(false);
        }
      }
    }

    /** 用途：负责 loadKbPanel 的界面或数据处理职责。 */
    loadKbPanel().catch(() => undefined);

    /** 用途：负责 return 的界面或数据处理职责。 */
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

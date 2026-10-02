import { useCallback, useEffect, useState } from "react";
import {
  deleteDocument,
  deleteKnowledgeBase,
  downloadDocument,
  exportKnowledgeBase,
  importKnowledgeBase,
  createKnowledgeBase,
  listDocuments,
  listKnowledgeBases,
  reindexDocument,
  switchKnowledgeBase,
  uploadDocument
} from "../api/kb";
import { useConversationStore } from "../stores/conversationStore";
import type { KnowledgeBase, KnowledgeFile } from "../types/kb";
import { useI18n } from "../i18n";

/** 用途：负责 useKbPanel 的界面或数据处理职责。 */
export function useKbPanel() {
  const { t } = useI18n();
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
            : t("kb.switchFailed");
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(message);
      } finally {
        /** 用途：负责 setIsLoading 的界面或数据处理职责。 */
        setIsLoading(false);
      }
    },
    [refreshDocuments, setKbName, t]
  );

  const createKnowledgeBaseByName = useCallback(async (name: string) => {
    const nextName = name.trim();
    if (!nextName) return false;
    setIsKbActionLoading(true);
    setKbActionStatus(t("kb.creatingKb", { name: nextName }));
    setError(null);
    try {
      const result = await createKnowledgeBase(nextName);
      if (result.error) throw new Error(result.error);
      await refreshKnowledgeBases();
      await selectKnowledgeBase(nextName);
      setKbActionStatus(t("kb.createKbSuccess", { name: nextName }));
      return true;
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : t("kb.createKbFailed");
      setError(message);
      setKbActionStatus(t("kb.createKbFailed"));
      return false;
    } finally {
      setIsKbActionLoading(false);
    }
  }, [refreshKnowledgeBases, selectKnowledgeBase, t]);

  const deleteKnowledgeBaseByName = useCallback(async (name: string) => {
    setIsKbActionLoading(true);
    setKbActionStatus(t("kb.deletingKb", { name }));
    setError(null);
    try {
      const result = await deleteKnowledgeBase(name);
      if (result.error) throw new Error(result.error);
      setKbName("default");
      await switchKnowledgeBase("default");
      await refreshKnowledgeBases();
      await refreshDocuments();
      setKbActionStatus(t("kb.deleteKbSuccess", { name }));
      return true;
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : t("kb.deleteKbFailed");
      setError(message);
      setKbActionStatus(t("kb.deleteKbFailed"));
      return false;
    } finally {
      setIsKbActionLoading(false);
    }
  }, [refreshDocuments, refreshKnowledgeBases, setKbName, t]);

  const uploadKnowledgeFile = useCallback(
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (file: File | null) => {
      if (!file) {
        /** 用途：负责 setUploadStatus 的界面或数据处理职责。 */
        setUploadStatus(t("kb.chooseFileFirst"));
        return false;
      }

      /** 用途：负责 setIsUploading 的界面或数据处理职责。 */
      setIsUploading(true);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(null);
      /** 用途：负责 setUploadStatus 的界面或数据处理职责。 */
      setUploadStatus(t("kb.uploadingFile", { name: file.name }));

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
        setUploadStatus(result.message || t("kb.uploadSuccessNamed", { name: file.name }));
        await refreshDocuments();
        return true;
      } catch (uploadError) {
        const message = uploadError instanceof Error ? uploadError.message : t("kb.uploadFailed");
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
    [refreshDocuments, t]
  );

  const downloadKnowledgeFile = useCallback(async (filename: string) => {
    /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
    setActiveDocumentAction(`download:${filename}`);
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);
    /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
    setDocumentActionStatus(t("kb.downloadingFile", { name: filename }));

    try {
      await downloadDocument(filename);
      /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
      setDocumentActionStatus(t("kb.downloadSuccess", { name: filename }));
      return true;
    } catch (downloadError) {
      const message =
        downloadError instanceof Error
          ? downloadError.message
          : t("kb.downloadFailed");
      /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
      setDocumentActionStatus(message);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(message);
      return false;
    } finally {
      /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
      setActiveDocumentAction(null);
    }
  }, [t]);

  const reindexKnowledgeFile = useCallback(
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (file: KnowledgeFile) => {
      /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
      setActiveDocumentAction(`reindex:${file.filename}`);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(null);
      /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
      setDocumentActionStatus(t("kb.reindexingFile", { name: file.filename }));

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
          return false;
        }

        /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
        setDocumentActionStatus(
          result.message || t("kb.reindexSuccess", { name: file.filename })
        );
        await refreshDocuments();
        return true;
      } catch (reindexError) {
        const message =
          reindexError instanceof Error
            ? reindexError.message
            : t("kb.reindexFailed");
        /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
        setDocumentActionStatus(message);
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(message);
        return false;
      } finally {
        /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
        setActiveDocumentAction(null);
      }
    },
    [refreshDocuments, t]
  );

  const deleteKnowledgeFile = useCallback(
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (filename: string) => {
      /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
      setActiveDocumentAction(`delete:${filename}`);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(null);
      /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
      setDocumentActionStatus(t("kb.deletingFile", { name: filename }));

      try {
        const result = await deleteDocument(filename);

        if (result.error) {
          /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
          setDocumentActionStatus(result.error);
          /** 用途：负责 setError 的界面或数据处理职责。 */
          setError(result.error);
          return false;
        }

        /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
        setDocumentActionStatus(result.message || t("kb.deleteSuccess", { name: filename }));
        await refreshDocuments();
        return true;
      } catch (deleteError) {
        const message =
          deleteError instanceof Error ? deleteError.message : t("kb.deleteFailed");
        /** 用途：负责 setDocumentActionStatus 的界面或数据处理职责。 */
        setDocumentActionStatus(message);
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(message);
        return false;
      } finally {
        /** 用途：负责 setActiveDocumentAction 的界面或数据处理职责。 */
        setActiveDocumentAction(null);
      }
    },
    [refreshDocuments, t]
  );

  const exportCurrentKnowledgeBase = useCallback(async () => {
    /** 用途：负责 setIsKbActionLoading 的界面或数据处理职责。 */
    setIsKbActionLoading(true);
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);
    /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
    setKbActionStatus(t("kb.exportingKb", { name: kbName }));

    try {
      await exportKnowledgeBase(kbName);
      /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
      setKbActionStatus(t("kb.exportSuccess", { name: kbName }));
      return true;
    } catch (exportError) {
      const message =
        exportError instanceof Error ? exportError.message : t("kb.exportFailed");
      /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
      setKbActionStatus(message);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(message);
      return false;
    } finally {
      /** 用途：负责 setIsKbActionLoading 的界面或数据处理职责。 */
      setIsKbActionLoading(false);
    }
  }, [kbName, t]);

  const importKnowledgeBaseFile = useCallback(
    /** 用途：负责 async 的界面或数据处理职责。 */
    async (file: File | null) => {
      if (!file) {
        /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
        setKbActionStatus(t("kb.chooseImportFile"));
        return false;
      }

      /** 用途：负责 setIsKbActionLoading 的界面或数据处理职责。 */
      setIsKbActionLoading(true);
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(null);
      /** 用途：负责 setKbActionStatus 的界面或数据处理职责。 */
      setKbActionStatus(t("kb.importingFile", { name: file.name }));

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
            ? t("kb.importSuccessNamed", { name: result.kb_name })
            : t("kb.importSuccessNamed", { name: file.name })
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
          importError instanceof Error ? importError.message : t("kb.importFailed");
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
    [refreshDocuments, refreshKnowledgeBases, selectKnowledgeBase, t]
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
            : t("kb.loadFailed");
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
  }, [t]);

  return {
    createKnowledgeBaseByName,
    documents,
    activeDocumentAction,
    deleteKnowledgeFile,
    deleteKnowledgeBaseByName,
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

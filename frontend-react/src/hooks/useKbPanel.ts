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

/**
 * 编排知识库页面的选择、文件操作和状态反馈。
 * 这里把 API 结果写回列表状态；真正的文件解析、索引和用户隔离由后端完成。
 */
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
      // 先让后端切换当前知识库，再更新共享 kbName 并刷新文件列表。
      // isLoading 会让上传入口暂时不可用，避免用户误以为切换尚未完成时已经在新库操作。
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
            : t("kb.switchFailed");
        setError(message);
      } finally {
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
      // 创建成功后立即选中新知识库，让后续文件列表和上传操作落在同一个目标上。
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
      // 删除当前知识库后显式切回 default，再刷新知识库列表和对应文件列表。
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
    async (file: File | null) => {
      if (!file) {
        setUploadStatus(t("kb.chooseFileFirst"));
        return false;
      }

      setIsUploading(true);
      setError(null);
      setUploadStatus(t("kb.uploadingFile", { name: file.name }));

      try {
        // 显式传入当前 kbName。即使 /switch_kb 尚未完成，文件也会进入用户刚选择的目标知识库。
        const result = await uploadDocument(file, kbName);

        if (result.error) {
          setUploadStatus(result.error);
          setError(result.error);
          return false;
        }

        setUploadStatus(result.message || t("kb.uploadSuccessNamed", { name: file.name }));
        await refreshDocuments();
        return true;
      } catch (uploadError) {
        const message = uploadError instanceof Error ? uploadError.message : t("kb.uploadFailed");
        setUploadStatus(message);
        setError(message);
        return false;
      } finally {
        setIsUploading(false);
      }
    },
    [kbName, refreshDocuments, t]
  );

  const downloadKnowledgeFile = useCallback(async (filename: string) => {
    setActiveDocumentAction(`download:${filename}`);
    setError(null);
    setDocumentActionStatus(t("kb.downloadingFile", { name: filename }));

    try {
      await downloadDocument(filename);
      setDocumentActionStatus(t("kb.downloadSuccess", { name: filename }));
      return true;
    } catch (downloadError) {
      const message =
        downloadError instanceof Error
          ? downloadError.message
          : t("kb.downloadFailed");
      setDocumentActionStatus(message);
      setError(message);
      return false;
    } finally {
      setActiveDocumentAction(null);
    }
  }, [t]);

  const reindexKnowledgeFile = useCallback(
    async (file: KnowledgeFile) => {
      setActiveDocumentAction(`reindex:${file.filename}`);
      setError(null);
      setDocumentActionStatus(t("kb.reindexingFile", { name: file.filename }));

      try {
        const result = await reindexDocument(
          file.filename,
          file.chunk_size || 300,
          file.chunk_overlap || 50
        );

        if (result.error) {
          setDocumentActionStatus(result.error);
          setError(result.error);
          return false;
        }

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
        setDocumentActionStatus(message);
        setError(message);
        return false;
      } finally {
        setActiveDocumentAction(null);
      }
    },
    [refreshDocuments, t]
  );

  const deleteKnowledgeFile = useCallback(
    async (filename: string) => {
      setActiveDocumentAction(`delete:${filename}`);
      setError(null);
      setDocumentActionStatus(t("kb.deletingFile", { name: filename }));

      try {
        const result = await deleteDocument(filename);

        if (result.error) {
          setDocumentActionStatus(result.error);
          setError(result.error);
          return false;
        }

        setDocumentActionStatus(result.message || t("kb.deleteSuccess", { name: filename }));
        await refreshDocuments();
        return true;
      } catch (deleteError) {
        const message =
          deleteError instanceof Error ? deleteError.message : t("kb.deleteFailed");
        setDocumentActionStatus(message);
        setError(message);
        return false;
      } finally {
        setActiveDocumentAction(null);
      }
    },
    [refreshDocuments, t]
  );

  const exportCurrentKnowledgeBase = useCallback(async () => {
    setIsKbActionLoading(true);
    setError(null);
    setKbActionStatus(t("kb.exportingKb", { name: kbName }));

    try {
      await exportKnowledgeBase(kbName);
      setKbActionStatus(t("kb.exportSuccess", { name: kbName }));
      return true;
    } catch (exportError) {
      const message =
        exportError instanceof Error ? exportError.message : t("kb.exportFailed");
      setKbActionStatus(message);
      setError(message);
      return false;
    } finally {
      setIsKbActionLoading(false);
    }
  }, [kbName, t]);

  const importKnowledgeBaseFile = useCallback(
    async (file: File | null) => {
      if (!file) {
        setKbActionStatus(t("kb.chooseImportFile"));
        return false;
      }

      setIsKbActionLoading(true);
      setError(null);
      setKbActionStatus(t("kb.importingFile", { name: file.name }));

      try {
        const result = await importKnowledgeBase(file);

        if (result.error) {
          setKbActionStatus(result.error);
          setError(result.error);
          return false;
        }

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
        setKbActionStatus(message);
        setError(message);
        return false;
      } finally {
        setIsKbActionLoading(false);
      }
    },
    [refreshDocuments, refreshKnowledgeBases, selectKnowledgeBase, t]
  );

  useEffect(() => {
    let ignore = false;

    async function loadKbPanel() {
      // 页面首次进入时并行读取知识库和当前库文件。组件卸载后的迟到响应不能再写状态。
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
            : t("kb.loadFailed");
        setError(message);
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadKbPanel().catch(() => undefined);

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

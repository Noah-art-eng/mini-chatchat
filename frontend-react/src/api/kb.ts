import { authFetch, requestJson } from "./client";
import type { KnowledgeBase, KnowledgeFile } from "../types/kb";

/** 读取当前用户拥有的知识库列表。 */
export async function listKnowledgeBases() {
  return requestJson<{ knowledge_bases: KnowledgeBase[] }>("/knowledge_bases");
}

export async function createKnowledgeBase(kbName: string) {
  return requestJson<{ message?: string; error?: string }>("/knowledge_bases", {
    method: "POST",
    body: JSON.stringify({ kb_name: kbName })
  });
}

export async function deleteKnowledgeBase(kbName: string) {
  return requestJson<{ message?: string; error?: string }>(
    `/knowledge_bases/${encodeURIComponent(kbName)}`,
    { method: "DELETE" }
  );
}

/** 更新后端当前知识库选择，供仍按会话选择工作的旧接口使用。 */
export async function switchKnowledgeBase(kbName: string) {
  return requestJson<{ current_kb: string }>("/switch_kb", {
    method: "POST",
    body: JSON.stringify({
      kb_name: kbName
    })
  });
}

/** 读取后端当前选中知识库的文件列表。 */
export async function listDocuments() {
  return requestJson<{ files: KnowledgeFile[] }>("/documents");
}

/**
 * 把文件和明确的 kb_name 一起上传到 /upload。
 * 后端按请求中的知识库完成校验、解析和索引，不依赖可能仍在切换中的全局选择状态。
 */
export async function uploadDocument(file: File, kbName: string) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("kb_name", kbName);
  formData.append("override", "true");
  formData.append("chunk_size", "300");
  formData.append("chunk_overlap", "50");

  const response = await authFetch("/upload", {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`);
  }

  return response.json() as Promise<{
    message?: string;
    error?: string;
  }>;
}

export async function downloadDocument(filename: string) {
  const response = await authFetch(
    `/documents/${encodeURIComponent(filename)}/download`
  );

  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`);
  }

  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    const data = (await response.json()) as { error?: string };
    throw new Error(data.error || "Download failed.");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/** 让后端重新解析指定文件并重建当前知识库索引。 */
export async function reindexDocument(
  filename: string,
  chunkSize = 300,
  chunkOverlap = 50
) {
  return requestJson<{
    message?: string;
    error?: string;
    filename?: string;
  }>(`/documents/${encodeURIComponent(filename)}/reindex`, {
    method: "POST",
    body: JSON.stringify({
      chunk_size: chunkSize,
      chunk_overlap: chunkOverlap
    })
  });
}

export async function deleteDocument(filename: string) {
  return requestJson<{
    message?: string;
    error?: string;
  }>(`/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE"
  });
}

/** 下载当前用户指定知识库的 ZIP 快照。 */
export async function exportKnowledgeBase(kbName: string) {
  const response = await authFetch(
    `/knowledge_bases/${encodeURIComponent(kbName)}/export`
  );

  if (!response.ok) {
    throw new Error(`Export failed: ${response.status}`);
  }

  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    const data = (await response.json()) as { error?: string };
    throw new Error(data.error || "Export failed.");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${kbName}_export.zip`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/** 上传知识库 ZIP；后端完成资源、路径和归属校验后再导入。 */
export async function importKnowledgeBase(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("override", "false");

  const response = await authFetch("/knowledge_bases/import", {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(`Import failed: ${response.status}`);
  }

  return response.json() as Promise<{
    kb_name?: string;
    files_count?: number;
    chunks_count?: number;
    error?: string;
  }>;
}

import { API_BASE, requestJson } from "./client";
import type { KnowledgeBase, KnowledgeFile } from "../types/kb";

export async function listKnowledgeBases() {
  return requestJson<{ knowledge_bases: KnowledgeBase[] }>("/knowledge_bases");
}

export async function switchKnowledgeBase(kbName: string) {
  return requestJson<{ current_kb: string }>("/switch_kb", {
    method: "POST",
    body: JSON.stringify({
      kb_name: kbName
    })
  });
}

export async function listDocuments() {
  return requestJson<{ files: KnowledgeFile[] }>("/documents");
}

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("override", "true");
  formData.append("chunk_size", "300");
  formData.append("chunk_overlap", "50");

  const response = await fetch(`${API_BASE}/upload`, {
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
  const response = await fetch(
    `${API_BASE}/documents/${encodeURIComponent(filename)}/download`
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

export async function exportKnowledgeBase(kbName: string) {
  const response = await fetch(
    `${API_BASE}/knowledge_bases/${encodeURIComponent(kbName)}/export`
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

export async function importKnowledgeBase(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("override", "false");

  const response = await fetch(`${API_BASE}/knowledge_bases/import`, {
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

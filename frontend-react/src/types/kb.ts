export type KnowledgeBase = {
  id: number;
  kb_name: string;
  embed_model?: string;
  create_time?: string;
};

export type KnowledgeFile = {
  filename: string;
  status?: string | null;
  docs_count?: number | null;
  chunk_size?: number | null;
  chunk_overlap?: number | null;
  content_path?: string | null;
  error?: string | null;
  upload_path?: string | null;
};

import type { Source } from "./conversation";

export type KBChatRequest = {
  mode: ChatMode;
  query: string;
  kb_name?: string;
  temp_kb_id?: string;
  stream: boolean;
  conversation_id?: number | null;
  top_k?: number;
  score_threshold?: number;
  prompt_name?: string;
  return_direct?: boolean;
  rerank?: boolean;
  rerank_top_n?: number;
};

export type ChatMode = "local_kb" | "search_engine" | "temp_kb" | "agent";

export type StreamEvent =
  | {
      type: "sources";
      sources: Source[];
      conversation_id?: number;
    }
  | {
      type: "token";
      content: string;
    }
  | {
      type: "done";
      assistant_message_id?: number;
      conversation_id?: number;
    }
  | {
      type: "error";
      message: string;
      conversation_id?: number;
    };

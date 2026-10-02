import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import { ConversationProvider } from "../stores/conversationStore";
import { useKbPanel } from "./useKbPanel";
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  listDocuments,
  listKnowledgeBases,
  switchKnowledgeBase
} from "../api/kb";

vi.mock("../api/kb", () => ({
  createKnowledgeBase: vi.fn(),
  deleteDocument: vi.fn(),
  deleteKnowledgeBase: vi.fn(),
  downloadDocument: vi.fn(),
  exportKnowledgeBase: vi.fn(),
  importKnowledgeBase: vi.fn(),
  listDocuments: vi.fn(),
  listKnowledgeBases: vi.fn(),
  reindexDocument: vi.fn(),
  switchKnowledgeBase: vi.fn(),
  uploadDocument: vi.fn()
}));

function wrapper({ children }: { children: ReactNode }) {
  return (
    <I18nProvider>
      <ConversationProvider>{children}</ConversationProvider>
    </I18nProvider>
  );
}

describe("knowledge base lifecycle feedback", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(listKnowledgeBases).mockResolvedValue({
      knowledge_bases: [{ id: 1, kb_name: "default" }]
    });
    vi.mocked(listDocuments).mockResolvedValue({ files: [] });
    vi.mocked(switchKnowledgeBase).mockResolvedValue({ current_kb: "default" });
    vi.mocked(createKnowledgeBase).mockReset();
    vi.mocked(deleteKnowledgeBase).mockReset();
  });

  it("moves create feedback from processing to success only after the API completes", async () => {
    let finishCreate: ((value: { message: string }) => void) | undefined;
    vi.mocked(createKnowledgeBase).mockImplementation(
      () => new Promise(resolve => {
        finishCreate = resolve;
      })
    );
    vi.mocked(listKnowledgeBases)
      .mockResolvedValueOnce({ knowledge_bases: [{ id: 1, kb_name: "default" }] })
      .mockResolvedValueOnce({
        knowledge_bases: [
          { id: 1, kb_name: "default" },
          { id: 2, kb_name: "产品资料" }
        ]
      });

    const { result } = renderHook(useKbPanel, { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    let creation: Promise<boolean> | undefined;
    act(() => {
      creation = result.current.createKnowledgeBaseByName("产品资料");
    });

    expect(result.current.isKbActionLoading).toBe(true);
    expect(result.current.kbActionStatus).toBe("Creating 产品资料...");

    await act(async () => {
      finishCreate?.({ message: "created" });
      await creation;
    });

    expect(result.current.isKbActionLoading).toBe(false);
    expect(result.current.kbActionStatus).toBe("产品资料 created.");
    expect(switchKnowledgeBase).toHaveBeenCalledWith("产品资料");
  });

  it("reports delete failures without claiming success", async () => {
    vi.mocked(deleteKnowledgeBase).mockRejectedValue(new Error("delete unavailable"));
    const { result } = renderHook(useKbPanel, { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    let deleted = true;
    await act(async () => {
      deleted = await result.current.deleteKnowledgeBaseByName("archive");
    });

    expect(deleted).toBe(false);
    expect(result.current.kbActionStatus).toBe("Knowledge base deletion failed.");
    expect(result.current.error).toBe("delete unavailable");
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatArea } from "./ChatArea";
import { switchKnowledgeBase } from "../../api/kb";

const setKbName = vi.fn();

vi.mock("../../api/kb", () => ({
  listKnowledgeBases: vi.fn(async () => ({
    knowledge_bases: [
      { id: 1, kb_name: "default" },
      { id: 2, kb_name: "个人简历" }
    ]
  })),
  switchKnowledgeBase: vi.fn()
}));
vi.mock("../../hooks/useChatStream", () => ({
  useChatStream: () => ({ error: null, isStreaming: false, sendMessage: vi.fn(), stopGeneration: vi.fn() })
}));
vi.mock("../../hooks/useAgentRun", () => ({
  useAgentRun: () => ({ agentResult: null, error: null, isRunning: false, sendAgentMessage: vi.fn(), stopAgentRun: vi.fn(), streamStatus: null, streamTokenText: "" })
}));
vi.mock("../../stores/conversationStore", () => ({
  useConversationStore: () => ({
    chatMode: "local_kb",
    conversationId: null,
    isLoadingMessages: false,
    kbName: "default",
    messages: [],
    selectedAssistantMessageId: null,
    setChatMode: vi.fn(),
    setKbName,
    setSelectedAssistantMessageId: vi.fn(),
    setTempFileName: vi.fn(),
    setTempKbId: vi.fn(),
    streamingMessage: "",
    tempFileName: null,
    tempKbId: null
  })
}));
vi.mock("../../router", () => ({ useNavigate: () => vi.fn() }));
vi.mock("../../i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("./ChatWorkspace", () => ({
  ChatWorkspace: ({ onChangeKbName }: { onChangeKbName: (name: string) => void }) => (
    <button onClick={() => onChangeKbName("个人简历")} type="button">select personal KB</button>
  )
}));

describe("ChatArea knowledge base selection", () => {
  beforeEach(() => {
    setKbName.mockReset();
    vi.mocked(switchKnowledgeBase).mockReset();
  });

  it("synchronizes the backend selection before committing the local state", async () => {
    vi.mocked(switchKnowledgeBase).mockResolvedValue({ current_kb: "个人简历" });
    render(<ChatArea />);

    fireEvent.click(screen.getByRole("button", { name: "select personal KB" }));

    await waitFor(() => {
      expect(switchKnowledgeBase).toHaveBeenCalledWith("个人简历");
      expect(setKbName).toHaveBeenCalledWith("个人简历");
    });
    expect(
      vi.mocked(switchKnowledgeBase).mock.invocationCallOrder[0]
    ).toBeLessThan(setKbName.mock.invocationCallOrder[0]);
  });
});

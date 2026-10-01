import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConversationProvider, useConversationStore } from "../stores/conversationStore";
import type { AgentRunResponse, AgentStreamEvent } from "../types/agent";
import type { StreamEvent } from "../types/chat";
import { useAgentRun } from "./useAgentRun";
import { useChatStream } from "./useChatStream";

type PendingChat = {
  onEvent?: (event: StreamEvent) => void;
  reject: (reason?: unknown) => void;
  resolve: () => void;
  signal?: AbortSignal;
};

type PendingAgent = {
  onEvent: (event: AgentStreamEvent) => void;
  reject: (reason?: unknown) => void;
  resolve: () => void;
  signal?: AbortSignal;
};

const pendingChats: PendingChat[] = [];
const pendingAgents: PendingAgent[] = [];

vi.mock("../api/conversations", () => ({
  deleteConversation: vi.fn(),
  deleteConversations: vi.fn(),
  getConversationMessages: vi.fn(),
  listConversations: vi.fn(async () => ({ conversations: [] })),
  renameConversation: vi.fn()
}));

vi.mock("../api/chat", () => ({
  startKbChat: vi.fn(async (_request: unknown, signal?: AbortSignal) => {
    const pending = pendingChats[pendingChats.length - 1];
    if (pending) pending.signal = signal;
    return new Response("stream");
  }),
  readSSE: vi.fn(
    async (
      _response: Response,
      onEvent: (event: StreamEvent) => void,
      signal?: AbortSignal
    ) => {
      await new Promise<void>((resolve, reject) => {
        pendingChats.push({ onEvent, reject, resolve, signal });
      });
    }
  )
}));

vi.mock("../api/agent", () => ({
  runAgentPlanStream: vi.fn(
    async (
      _request: unknown,
      onEvent: (event: AgentStreamEvent) => void,
      signal?: AbortSignal
    ) => {
      await new Promise<void>((resolve, reject) => {
        pendingAgents.push({ onEvent, reject, resolve, signal });
      });
    }
  )
}));

function wrapper({ children }: { children: ReactNode }) {
  return <ConversationProvider>{children}</ConversationProvider>;
}

function useChatHarness() {
  return { chat: useChatStream(), store: useConversationStore() };
}

function useAgentHarness() {
  return { agent: useAgentRun(), store: useConversationStore() };
}

function abortError() {
  return new DOMException("The operation was aborted.", "AbortError");
}

describe("stream request isolation", () => {
  beforeEach(() => {
    pendingChats.length = 0;
    pendingAgents.length = 0;
    localStorage.clear();
  });

  it("aborts chat and ignores stale events after changing conversation", async () => {
    const { result } = renderHook(useChatHarness, { wrapper });

    act(() => result.current.store.setConversationId(11));
    await act(async () => {
      void result.current.chat.sendMessage("old question");
    });
    await waitFor(() => expect(pendingChats).toHaveLength(1));

    const oldRun = pendingChats[0];
    act(() => result.current.store.startNewConversation());

    await waitFor(() => expect(oldRun.signal?.aborted).toBe(true));
    act(() => {
      oldRun.onEvent?.({ type: "token", content: "stale token" });
      oldRun.onEvent?.({
        type: "sources",
        sources: [{ source: "stale.txt", content: "stale" }]
      });
      oldRun.onEvent?.({ type: "error", message: "stale error" });
      oldRun.reject(abortError());
    });

    await waitFor(() => expect(result.current.chat.isStreaming).toBe(false));
    expect(result.current.chat.error).toBeNull();
    expect(result.current.store.messages).toEqual([]);
    expect(result.current.store.sources).toEqual([]);
    expect(result.current.store.streamingMessage).toBe("");
  });

  it("aborts the previous chat run when a newer request starts", async () => {
    const { result } = renderHook(useChatHarness, { wrapper });

    await act(async () => {
      void result.current.chat.sendMessage("first");
      void result.current.chat.sendMessage("second");
    });
    await waitFor(() => expect(pendingChats).toHaveLength(2));

    expect(pendingChats[0].signal?.aborted).toBe(true);
    expect(pendingChats[1].signal?.aborted).toBe(false);
  });

  it("keeps a partial chat answer when the stream reports a later failure", async () => {
    const { result } = renderHook(useChatHarness, { wrapper });

    await act(async () => {
      void result.current.chat.sendMessage("partial request");
    });
    await waitFor(() => expect(pendingChats).toHaveLength(1));

    const run = pendingChats[0];
    act(() => {
      run.onEvent?.({ type: "token", content: "partial answer" });
      run.onEvent?.({
        type: "error",
        message: "Streaming response failed. Please try again.",
        partial_response: true
      } as StreamEvent);
      run.onEvent?.({ type: "done", assistant_message_id: 8 });
      run.resolve();
    });

    await waitFor(() => expect(result.current.chat.isStreaming).toBe(false));
    expect(result.current.chat.error).toBe(
      "Streaming response failed. Please try again."
    );
    expect(
      result.current.store.messages[result.current.store.messages.length - 1]?.content
    ).toBe("partial answer");
  });

  it("uses the generic error as the assistant message when no token arrived", async () => {
    const { result } = renderHook(useChatHarness, { wrapper });

    await act(async () => {
      void result.current.chat.sendMessage("failed request");
    });
    await waitFor(() => expect(pendingChats).toHaveLength(1));

    const run = pendingChats[0];
    act(() => {
      run.onEvent?.({
        type: "error",
        message: "Streaming response failed. Please try again.",
        partial_response: false
      } as StreamEvent);
      run.onEvent?.({ type: "done", assistant_message_id: 9 });
      run.resolve();
    });

    await waitFor(() => expect(result.current.chat.isStreaming).toBe(false));
    expect(result.current.chat.error).toBe(
      "Streaming response failed. Please try again."
    );
    expect(
      result.current.store.messages[result.current.store.messages.length - 1]?.content
    ).toBe("Streaming response failed. Please try again.");
  });

  it("keeps normal completion separate from a real network failure", async () => {
    const { result } = renderHook(useChatHarness, { wrapper });

    await act(async () => {
      void result.current.chat.sendMessage("successful request");
    });
    await waitFor(() => expect(pendingChats).toHaveLength(1));

    const successfulRun = pendingChats[0];
    act(() => {
      successfulRun.onEvent?.({ type: "token", content: "answer" });
      successfulRun.onEvent?.({
        type: "sources",
        sources: [{ source: "guide.txt", content: "evidence" }]
      });
      successfulRun.onEvent?.({ type: "done", assistant_message_id: 7 });
      successfulRun.resolve();
    });

    await waitFor(() => expect(result.current.chat.isStreaming).toBe(false));
    expect(result.current.chat.error).toBeNull();
    expect(
      result.current.store.messages[result.current.store.messages.length - 1]?.content
    ).toBe("answer");
    expect(result.current.store.sources[0]?.source).toBe("guide.txt");

    await act(async () => {
      void result.current.chat.sendMessage("network failure");
    });
    await waitFor(() => expect(pendingChats).toHaveLength(2));

    act(() => pendingChats[1].reject(new Error("network unavailable")));
    await waitFor(() => expect(result.current.chat.isStreaming).toBe(false));
    expect(result.current.chat.error).toBe("network unavailable");
    expect(
      result.current.store.messages[result.current.store.messages.length - 1]?.content
    ).toBe("network unavailable");
  });

  it("aborts an active chat stream when its component unmounts", async () => {
    const { result, unmount } = renderHook(useChatHarness, { wrapper });

    await act(async () => {
      void result.current.chat.sendMessage("unmount request");
    });
    await waitFor(() => expect(pendingChats).toHaveLength(1));

    unmount();
    expect(pendingChats[0].signal?.aborted).toBe(true);
  });

  it("aborts Agent and ignores stale trace, token, error and done events", async () => {
    const { result } = renderHook(useAgentHarness, { wrapper });

    act(() => result.current.store.setConversationId(21));
    await act(async () => {
      void result.current.agent.sendAgentMessage("old agent request");
    });
    await waitFor(() => expect(pendingAgents).toHaveLength(1));

    const oldRun = pendingAgents[0];
    act(() => result.current.store.startNewConversation());
    await waitFor(() => expect(oldRun.signal?.aborted).toBe(true));

    const staleResult: AgentRunResponse = {
      answer: "stale answer",
      error: null,
      trace: [],
      tool_count: 0
    };
    act(() => {
      oldRun.onEvent({ type: "token", content: "stale token" });
      oldRun.onEvent({ type: "error", error: "stale error" });
      oldRun.onEvent({ type: "done", result: staleResult });
      oldRun.reject(abortError());
    });

    await waitFor(() => expect(result.current.agent.isRunning).toBe(false));
    expect(result.current.agent.error).toBeNull();
    expect(result.current.agent.agentResult).toBeNull();
    expect(result.current.agent.streamTokenText).toBe("");
    expect(result.current.store.messages).toEqual([]);
  });

  it("aborts an active Agent stream when its component unmounts", async () => {
    const { result, unmount } = renderHook(useAgentHarness, { wrapper });

    await act(async () => {
      void result.current.agent.sendAgentMessage("unmount agent request");
    });
    await waitFor(() => expect(pendingAgents).toHaveLength(1));

    unmount();
    expect(pendingAgents[0].signal?.aborted).toBe(true);
  });
});

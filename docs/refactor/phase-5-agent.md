# React Refactor Phase 5: Agent Workspace

## Scope

This phase refactors the Agent workspace presentation layer only. It keeps backend APIs, `useAgentRun`, MCP integration, Tool Registry, store state, streaming, conversation, chat, knowledge, and system behavior unchanged.

## Split Components

New Agent presentation components:

- `frontend-react/src/components/agent/AgentWorkspace.tsx`
  - Owns Agent trace composition.
  - Receives the same props previously accepted by `AgentTracePanel`.

- `frontend-react/src/components/agent/AgentHeader.tsx`
  - Renders the trace panel heading and running/completed title.

- `frontend-react/src/components/agent/AgentRunToolbar.tsx`
  - Shows existing run summary values: step count, tool count, and result error when present.

- `frontend-react/src/components/agent/AgentStatus.tsx`
  - Shows existing running/stream status with polite live updates.

- `frontend-react/src/components/agent/AgentThought.tsx`
  - Renders existing planner goal, status, current step, and planner steps.
  - Does not infer or generate new reasoning.

- `frontend-react/src/components/agent/AgentTimeline.tsx`
  - Owns the timeline list.

- `frontend-react/src/components/agent/AgentStep.tsx`
  - Renders one agent step with tool call and observation.

- `frontend-react/src/components/agent/ToolInvocation.tsx`
  - Shows existing tool name, reason, and arguments.

- `frontend-react/src/components/agent/ToolResult.tsx`
  - Formats existing tool results by supported tool type.

- `frontend-react/src/components/agent/ToolCallSummary.tsx`
  - Shows single-step tool call fallback when no timeline steps exist.

- `frontend-react/src/components/agent/ToolObservation.tsx`
  - Shows single-step tool result fallback when no timeline steps exist.

- `frontend-react/src/components/agent/FinalAnswer.tsx`
  - Shows the final answer using the existing lightweight Markdown renderer.

- `frontend-react/src/components/agent/AgentTraceList.tsx`
  - Shows raw trace as secondary collapsed detail.

- `frontend-react/src/components/agent/EmptyAgentState.tsx`
  - Provides one empty Agent trace state.

- `frontend-react/src/components/agent/agentFormatters.ts`
  - Shared formatting helpers for JSON, records, text, numbers, and previews.

## Modified Components

- `frontend-react/src/components/AgentTracePanel.tsx`
  - Now acts as a compatibility wrapper around `AgentWorkspace`.
  - Public props and import path remain unchanged.

- `frontend-react/src/styles/shell.css`
  - Adds Agent run toolbar and empty state styling using design tokens.

## Deleted Components

No components were deleted in this phase.

## Preserved Components

These remain unchanged by design:

- `useAgentRun`
- `frontend-react/src/api/agent.ts`
- `conversationStore`
- `ChatWorkspace`
- `ContextPanel`
- backend Agent services
- Tool Registry
- MCP integration

## Compatibility Strategy

- `AgentTracePanel` keeps the same export and prop contract.
- Existing `data-testid` values remain available:
  - `agent-trace-panel`
  - `planner-panel`
  - `planner-step`
  - `agent-step`
  - `agent-step-tool`
  - `agent-step-result`
  - `agent-tool-call`
  - `agent-tool-result`
  - `agent-final-answer`
  - `agent-stream-token`
- Tool result rendering supports the same existing tools:
  - `calculator`
  - `kb_search`
  - `sqlite_readonly_query`
  - `filesystem_readonly_read`
  - `browser_read`
  - `browser_search`
- No new Agent states are introduced.
- No tool execution behavior changes.

## Validation

Typecheck:

- Passed through `npm run build`.

Build:

- `npm run build` passed.

ESLint:

- Not run. The current project does not define a lint script.

Unit tests:

- Not run. The current project does not define a unit test script.

## Known Limitations

- Agent detail still lives inside the Chat workspace `ContextPanel` in Agent mode. A dedicated Agent page workspace can be refined later without changing hooks.
- Raw trace remains a compact collapsed list rather than a full detail inspector.
- Tool result formatting is intentionally human-readable and does not expose full raw payloads as the primary UI.

## Next Phase Recommendation

Begin Phase 6: System Workspace Refactor.

Recommended order:

1. Keep System APIs unchanged.
2. Replace `SettingsPage` presentation with `SystemOverview`.
3. Split model, health, dependencies, tools, and MCP sections.
4. Keep runtime data factual and avoid adding settings controls that the backend cannot save.

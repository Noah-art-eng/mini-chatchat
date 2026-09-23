# React Refactor Phase 3: Chat Workspace

## Scope

This phase refactors the Chat workspace presentation layer only. It keeps backend APIs, stores, hooks, streaming protocol, conversation persistence, RAG retrieval, feedback, sources, and agent integration unchanged.

## Split Components

New Chat presentation components:

- `frontend-react/src/features/chat/ChatWorkspace.tsx`
  - Owns Chat workspace composition.
  - Receives state and callbacks from `ChatArea`.
  - Does not call APIs or stores directly.

- `frontend-react/src/components/chat/ChatHeader.tsx`
  - Renders conversation and active mode summary.

- `frontend-react/src/components/chat/ChatModeControls.tsx`
  - Renders mode cards and current KB field.
  - Uses existing mode and KB callbacks.

- `frontend-react/src/components/chat/ChatMessageViewport.tsx`
  - Owns message viewport shell, loading state, and empty/message placement.

- `frontend-react/src/components/chat/UserMessage.tsx`
  - Renders user messages only.

- `frontend-react/src/components/chat/AssistantMessage.tsx`
  - Renders assistant messages, markdown content, source references, and message actions.

- `frontend-react/src/components/chat/StreamingMessage.tsx`
  - Renders the active streaming assistant message separately from persisted assistant messages.

- `frontend-react/src/components/chat/MessageActions.tsx`
  - Groups Copy and existing feedback controls.
  - Does not add retry because no retry API exists yet.

- `frontend-react/src/components/chat/SourceReferenceList.tsx`
  - Shows compact per-answer source references.
  - Opens the existing Sources context panel for the selected assistant message.

- `frontend-react/src/components/chat/MarkdownContent.tsx`
  - Provides lightweight rendering for paragraphs, inline code, code fences, lists, quotes, headings, and simple markdown tables without adding a dependency.

- `frontend-react/src/components/chat/TempFilePanel.tsx`
  - Renders temp file upload UI using existing callbacks.

## Modified Components

- `frontend-react/src/features/chat/ChatArea.tsx`
  - Now acts as the container for existing hooks, derived state, temp upload state, and submit callbacks.
  - Delegates UI rendering to `ChatWorkspace`.

- `frontend-react/src/components/ChatMessageList.tsx`
  - Now coordinates `UserMessage`, `AssistantMessage`, and `StreamingMessage`.
  - Keeps existing selection behavior and stable `data-testid="message-list"`.

- `frontend-react/src/styles/shell.css`
  - Adds message markdown, source reference, and message action styles using design tokens.

## Deleted Components

No components were deleted in this phase.

## Preserved Components

These remain in place and are intentionally not refactored yet:

- `ChatComposer`
- `SourcesPanel`
- `RetrievalDebugPanel`
- `FeedbackControls`
- `ContextPanel`
- `AgentTracePanel`

## Compatibility Strategy

- `useChatStream` is unchanged.
- `useAgentRun` is unchanged.
- `conversationStore` is unchanged.
- API clients are unchanged.
- SSE event handling and streaming message state are unchanged.
- Assistant source selection still uses `selectedAssistantMessageId`.
- Feedback still uses the existing `/chat/feedback` flow.
- Agent mode still uses existing agent stream state and `AgentTracePanel`.

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

- Markdown rendering is intentionally lightweight and does not cover full GitHub-flavored Markdown.
- Copy action uses the browser clipboard API and falls back to an inline failure state if the browser denies access.
- Retry is not shown because there is no existing retry/abort contract.
- `SourcesPanel` and `RetrievalDebugPanel` are still legacy detail components inside the unified `ContextPanel`.

## Next Phase Recommendation

Begin Phase 4: Knowledge Workspace Refactor.

Recommended order:

1. Split `KnowledgeBasePage` into workspace composition and document-management presentation components.
2. Keep `useKbPanel` and API clients unchanged.
3. Move document detail/chunk detail into the existing `ContextPanel` pattern.
4. Preserve upload, download, reindex, delete, import, and export behavior.

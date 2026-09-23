# UI Redesign Plan

The next UI phase is a React redesign. The goal is not a visual makeover for its own sake. The goal is to make growing product state explicit, testable, and maintainable while preserving the current backend APIs.

## Current UI Problems

The plain JS frontend has grown beyond its original purpose:

- `frontend/app.js` owns too many responsibilities.
- Chat streaming, KB state, temp file state, feedback, debug settings, import/export, and document management are mixed.
- Chat history is saved as HTML in localStorage.
- Conversation IDs are not first-class UI state.
- Debug panel settings are reused by chat implicitly.
- DOM mutation makes E2E failures harder to diagnose.

## Redesign Goals

- Keep current backend endpoints.
- Preserve current feature coverage.
- Make state explicit.
- Make streaming reusable.
- Add Conversation History UI.
- Keep interface dense and operational, not marketing-like.
- Keep the first screen as the actual app, not a landing page.

## Proposed React Structure

```text
frontend-react/
  src/
    api/
      client.ts
      chat.ts
      kb.ts
      documents.ts
      conversations.ts
    hooks/
      useSSE.ts
      useKbList.ts
      useConversation.ts
      useRetrievalSettings.ts
    components/
      AppShell.tsx
      KBToolbar.tsx
      DocumentList.tsx
      DocumentActions.tsx
      ChatModeSelector.tsx
      RetrievalDebugPanel.tsx
      ChatThread.tsx
      MessageBubble.tsx
      SourcesList.tsx
      FeedbackControls.tsx
      TempFilePanel.tsx
      ConversationSidebar.tsx
    styles/
      app.css
```

The exact toolchain can be Vite + React. TypeScript is recommended but not required if the user wants to keep the project simpler.

## State Model

Application state:

- selected KB
- KB list
- document list
- selected chat mode
- retrieval settings
- current temp KB id
- current conversation id
- active messages
- streaming message state

Server state:

- KBs
- documents
- conversations
- messages
- feedback

Avoid storing rendered HTML. Store structured message objects.

## Conversation History UI

Conversation History should be part of the React redesign or the first backend/frontend task immediately before it.

Backend endpoints to add:

- `GET /conversations`
- `GET /conversations/{conversation_id}/messages`
- optional `DELETE /conversations/{conversation_id}`
- optional rename conversation endpoint

Frontend behavior:

- sidebar lists conversations
- New Conversation button clears current thread and sets `conversation_id=null`
- first successful chat receives/uses backend `conversation_id`
- switching a conversation loads messages from DB
- `ask()` always sends current `conversation_id` when present
- streaming `sources` or `done` updates current conversation id

Acceptance:

- reload page and still see conversation list
- switch conversation and see correct messages
- feedback remains tied to assistant message id

## Component Notes

### `KBToolbar`

Owns:

- KB selector
- New KB
- Delete KB
- Export KB
- Import KB

Should not own document rendering.

### `DocumentList`

Displays:

- filename
- status
- docs_count
- chunk_size / chunk_overlap
- error
- Reindex
- Delete
- Download

### `RetrievalDebugPanel`

Owns:

- top_k
- score_threshold
- prompt_name
- rerank
- rerank_top_n
- return_direct
- Debug Search
- Debug Results

It should expose settings to chat through a typed state object, not hidden DOM reads.

### `ChatThread`

Owns:

- message list rendering
- streaming assistant placeholder
- sources per answer
- feedback controls

It should not know how KB import/export works.

### `useSSE`

Reusable parser for:

- `/kb_chat`
- `/file_chat`
- future OpenAI-compatible stream if needed

Must handle:

- `type=sources`
- `type=token`
- `type=done`
- `type=error`
- `[DONE]` compatibility

## Visual Direction

This is an operational RAG tool, so the UI should be:

- compact
- scannable
- quiet
- reliable
- suited for repeated use

Avoid:

- hero sections
- marketing cards
- decorative gradients
- oversized headings
- hidden controls

Use:

- left sidebar for conversations
- top toolbar for KB controls
- main center chat thread
- right or collapsible panel for retrieval debug
- clear status badges for files

## Migration Plan

Step 1:

- Scaffold React app beside existing frontend.
- Add API client and route constants.
- Keep old frontend working.

Step 2:

- Port KB selector and document list.
- Verify upload, delete, reindex, import/export.

Step 3:

- Port `/kb_chat` streaming.
- Verify local KB, temp KB, search engine.

Step 4:

- Add Conversation History endpoints and UI.
- Replace localStorage HTML history.

Step 5:

- Port retrieval debug panel and feedback.
- Add Playwright coverage.

Step 6:

- Remove or archive old plain JS frontend only after parity is verified.

## Non-goals For This Phase

- No Agent mode.
- No MCP UI.
- No multi-provider model management UI.
- No redesign of backend RAG flow.
- No LangChain integration.

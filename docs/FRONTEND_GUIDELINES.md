# Frontend Guidelines

This guide defines how Mini ChatChat frontend work should be done during the move from the current plain HTML/CSS/JS app to a React UI. It is based on the project state, ChatChat-style product goals, and selected frontend/backend engineering references. It intentionally avoids copying reference text.

## Product UI Principles

- Build the actual working app first, not a landing page.
- Optimize for repeated daily use: compact, scannable, predictable, and fast.
- Keep the UI close to the RAG workflow: question, retrieval evidence, answer, feedback, and conversation continuity.
- Make state visible when it matters: current KB, chat mode, conversation, temp KB, retrieval settings, streaming state, and source documents.
- Prefer operational clarity over decorative design. The target visual family is closer to ChatGPT, Perplexity, and Dify than a marketing site.
- Every error state should help the user recover or understand what failed.

## Layout Rules

- Use a three-zone desktop layout for the React redesign:
  - Left: Conversation sidebar.
  - Center: Chat thread and input.
  - Right: Sources, retrieval debug, and KB/document panels.
- Keep the first viewport useful. The user should immediately see conversations, chat, and relevant controls.
- Use restrained density: show enough metadata for RAG debugging without turning the chat into a log dump.
- Keep repeated controls in stable positions:
  - Chat mode near the input or chat header.
  - KB selector and document actions in KB panel.
  - Retrieval settings in a dedicated debug panel.
- On smaller screens, collapse the left and right panels into drawers or tabs. Do not hide critical state without a clear affordance.

## React Component Rules

- Scaffold new work under `frontend-react/`. Do not directly replace or break the current `frontend/` app during migration.
- Start with core Chat + Conversation. Then migrate KB, Debug, Import/Export, Temp File Chat, and secondary tools.
- Prefer small components with clear ownership:
  - `AppShell`
  - `ConversationSidebar`
  - `ChatThread`
  - `MessageBubble`
  - `ChatInput`
  - `SourcesPanel`
  - `RetrievalDebugPanel`
  - `KBToolbar`
  - `DocumentList`
  - `FeedbackControls`
- Avoid monolithic components with many boolean props. Create explicit variants or compose smaller pieces.
- Keep component files focused. If a component accumulates API calls, parsing, storage, and rendering, split it.
- Put API requests under `src/api/`, for example:
  - `api/client.ts`
  - `api/chat.ts`
  - `api/conversations.ts`
  - `api/kb.ts`
  - `api/documents.ts`
- Put stateful workflows in hooks, for example:
  - `useConversation`
  - `useChatStream`
  - `useKbList`
  - `useRetrievalSettings`
  - `useTempKb`
- Do not define components inside components.
- Do not introduce a component library blindly. If using shadcn-style primitives later, keep them customizable and local to the app.

## State Management Rules

- Treat these as first-class state:
  - `currentConversationId`
  - `messages`
  - `streamingMessage`
  - `sources`
  - `selectedKb`
  - `chatMode`
  - `tempKbId`
  - `retrievalSettings`
  - `documentList`
- Store structured data, not rendered HTML.
- Use localStorage only for small, versioned preferences such as last selected conversation id or panel state. Do not store full chat DOM.
- Derive display values during render when possible instead of duplicating state.
- Use refs for transient stream buffers that update frequently.
- Keep API/server state separate from UI-only state.
- Fetch independent data in parallel when possible, for example conversations, KB list, and model info.

## Streaming / SSE UI Rules

- Centralize SSE parsing in one hook or utility. Do not duplicate stream parsing in each component.
- Support current Mini ChatChat event shapes:
  - `type="sources"`
  - `type="token"`
  - `type="done"`
  - `type="error"`
  - OpenAI-style `[DONE]` compatibility where needed.
- Persist `conversation_id` as soon as it appears in any event or chunk. Do not wait for `done`.
- Token rendering should append incrementally without rerendering the whole page.
- Each assistant message should own its own:
  - streaming text
  - sources
  - loading/error state
  - `assistant_message_id`
- Error events must not discard the current conversation id or sources already received.
- Done events should finalize the message, enable feedback, refresh conversations, and stop loading indicators.

## Conversation UI Rules

- Conversation History is the next product priority.
- The left sidebar should include:
  - New Conversation
  - conversation list
  - selected state
  - title
  - last updated or created time
- New Conversation should set `currentConversationId=null` and clear the active thread without deleting server data.
- First ask in a new conversation should bind to the backend `conversation_id`.
- Refreshing the page should restore the latest selected conversation id and load messages from the server.
- Switching conversations should load messages from `/conversations/{id}/messages`.
- Historical assistant messages should preserve feedback affordances where `assistant_message_id` exists.
- A later backend enhancement should save sources per assistant message so historical messages can show citations.
- Future conversation management should add rename, delete, and updated-time sorting before advanced Agent/MCP features.

## Knowledge Base UI Rules

- KB management should live in the right panel or a dedicated KB tab, not inside the chat thread.
- Show file metadata clearly:
  - filename
  - status
  - docs count
  - chunk size
  - chunk overlap
  - error
  - download/reindex/delete actions
- Status badges should be visually distinct:
  - uploaded
  - indexed
  - failed
- Keep upload/import/export separate from retrieval debug.
- Reindex should expose chunk params without crowding the document list.
- Runtime files, exports, FAISS files, and SQLite data must never be treated as source assets.

## Error / Loading / Empty State Rules

- Every async panel needs explicit states:
  - loading
  - empty
  - error
  - ready
- Empty conversation list: explain that no conversations exist yet and offer New Conversation.
- Empty sources: say no relevant sources were found.
- Empty KB: show upload and import options.
- Streaming error: show the error inside the assistant message and preserve the conversation.
- File errors should show the backend `error` field when available.
- Use deterministic user-facing messages. Do not expose stack traces in the UI.

## Accessibility Rules

- All buttons must be real `<button>` elements with `type="button"` unless they intentionally submit a form.
- Inputs must have visible labels or accessible labels.
- Keyboard users must be able to:
  - send a message
  - create a conversation
  - switch conversations
  - open source links
  - trigger feedback
- Keep focus stable after streaming starts and after conversation switching.
- Source URLs should open with `target="_blank"` and `rel="noopener noreferrer"`.
- Use sufficient contrast for status badges, selected conversation, disabled controls, and error text.
- Do not rely on color alone for file status or feedback state.

## Testing Rules

- For the existing plain frontend, run:

```bash
node --check frontend/app.js
```

- For React work, add and use:

```bash
npm run build
```

- UI changes should be verified with Playwright MCP when available.
- Minimum React UI E2E coverage should include:
  - create conversation
  - ask with local KB
  - recover conversation after refresh
  - switch conversations
  - streaming token display
  - sources display
  - feedback submission
  - retrieval debug return-direct
  - KB upload and document list
- Keep `test_files/sample_rag.txt` as the stable upload/temp-file fixture.

## What Not To Do

- Do not rewrite the entire frontend in one pass.
- Do not break the current `frontend/` while building `frontend-react/`.
- Do not add Agent, MCP UI, or multi-provider model UI during the React + Conversation phase.
- Do not introduce LangChain on the frontend or backend for UI reasons.
- Do not store rendered chat HTML as the long-term source of truth.
- Do not scatter fetch calls across components; use `api/` modules.
- Do not duplicate SSE parsing logic across chat modes.
- Do not hide retrieval settings in unrelated controls.
- Do not commit runtime data, screenshots, reports, exported zips, uploaded files, SQLite DB, or FAISS indexes.

## Migration Order

1. Create `frontend-react/` beside the current frontend.
2. Add API client modules and shared types for chat, conversations, KBs, documents, and sources.
3. Build the shell: left Conversation sidebar, center Chat, right Sources/Debug/KB panel.
4. Migrate core Chat + Conversation first.
5. Add reusable SSE hook and verify local KB streaming.
6. Add temp KB and search engine modes.
7. Migrate feedback.
8. Migrate KB document management, reindex, import/export.
9. Migrate retrieval debug panel.
10. Add Playwright coverage before retiring the old plain JS frontend.

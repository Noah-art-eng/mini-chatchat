# React Refactor Phase 4: Knowledge Workspace

## Scope

This phase refactors the Knowledge workspace presentation layer only. It keeps backend APIs, `useKbPanel`, store state, upload, delete, download, reindex, import/export, retrieval, FAISS, SQLite, chat, agent, and system behavior unchanged.

## Split Components

New Knowledge presentation components:

- `frontend-react/src/components/kb/KnowledgeWorkspace.tsx`
  - Owns Knowledge workspace composition.
  - Receives all data and callbacks from `KnowledgeBasePanel`.
  - Hosts the unified `ContextPanel` for document detail and retrieval debug.

- `frontend-react/src/components/kb/KnowledgeHeader.tsx`
  - Renders the Knowledge page header.

- `frontend-react/src/components/kb/KnowledgeStats.tsx`
  - Displays document count, indexed count, chunk count, and failed count from existing document data.

- `frontend-react/src/components/kb/KnowledgeBaseList.tsx`
  - Renders KB buttons and quick select using existing selection callbacks.

- `frontend-react/src/components/kb/KnowledgeToolbar.tsx`
  - Renders the existing Refresh Documents action.

- `frontend-react/src/components/kb/KnowledgeBackupActions.tsx`
  - Renders existing Export and Import controls.

- `frontend-react/src/components/kb/UploadPanel.tsx`
  - Renders existing document upload controls.

- `frontend-react/src/components/kb/DocumentTable.tsx`
  - Owns document list/empty state composition.

- `frontend-react/src/components/kb/DocumentRow.tsx`
  - Renders one document row and selection state.

- `frontend-react/src/components/kb/DocumentActions.tsx`
  - Renders existing Download, Reindex, and Delete row actions.

- `frontend-react/src/components/kb/DocumentDetailPanel.tsx`
  - Shows selected document metadata or aggregate stats in the `ContextPanel`.

- `frontend-react/src/components/kb/EmptyKnowledgeState.tsx`
  - Provides one empty document state.

## Modified Components

- `frontend-react/src/components/KnowledgeBasePanel.tsx`
  - Now acts as the container for `useKbPanel`, local file input state, and existing action callbacks.
  - Delegates rendering to `KnowledgeWorkspace`.

- `frontend-react/src/features/kb/KnowledgeBasePage.tsx`
  - Now mounts `KnowledgeBasePanel`.
  - No longer embeds Retrieval Debug as a second page card; debug lives in the unified `ContextPanel`.

- `frontend-react/src/styles/shell.css`
  - Adds Knowledge workspace layout, document selected state, empty state, and document detail styles using design tokens.

- `frontend-react/src/types/kb.ts`
  - Adds optional `error` metadata field already supported by backend document metadata responses.

## Deleted Components

No components were deleted in this phase.

## Preserved Components

These remain in place and are intentionally not refactored:

- `RetrievalDebugPanel`
- `ContextPanel`
- `useKbPanel`
- `api/kb.ts`

## Compatibility Strategy

- `useKbPanel` is unchanged.
- KB API clients are unchanged.
- Upload uses the same `uploadKnowledgeFile` flow and still clears selected file/input value on success.
- Import uses the same `importKnowledgeBaseFile` flow and still clears selected import file/input value on success.
- Export uses the same `exportCurrentKnowledgeBase` flow.
- Refresh uses the same `refreshDocuments` flow.
- Download, reindex, and delete use the same callbacks and stable document row `data-testid` values.
- Delete still uses `window.confirm` before calling the existing delete callback.
- Retrieval Debug still uses the existing `RetrievalDebugPanel`; only its placement changed into `ContextPanel`.

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

- Document detail is local UI selection only; it does not fetch chunk details yet.
- Retrieval Debug remains the existing component and still owns its own form state.
- Knowledge table is still rendered as responsive document cards rather than a dense table.
- Rename document is not shown because there is no existing backend/API capability.

## Next Phase Recommendation

Begin Phase 5: Agent Workspace Refactor.

Recommended order:

1. Keep `useAgentRun` and agent API clients unchanged.
2. Split Agent presentation into workspace, timeline, step, tool call, observation, and final answer components.
3. Preserve planner/tool streaming behavior.
4. Keep MCP/tool registry behavior unchanged.

# React Refactor Phase 2: Shell Foundation

## Scope

This phase establishes the shared React shell structure for Mini ChatChat. It keeps page implementations intact and does not change backend APIs, stores, hooks, streaming, conversation logic, retrieval, or tool execution.

## Modified Components

- `frontend-react/src/components/AppShell.tsx`
  - Keeps one root shell across Chat, Agent, Knowledge, and System.
  - Adds clearer landmarks and mobile conversation drawer backdrop.
  - Passes active workspace context to `TopBar`.

- `frontend-react/src/components/SidebarNavigation.tsx`
  - Keeps the four supported destinations: Chat, Knowledge, Agent, System.
  - Adds `aria-current="page"` for active navigation.
  - Keeps stable `data-testid` values.

- `frontend-react/src/components/TopBar.tsx`
  - Shows runtime summary only: workspace, mode, current KB, model, health.
  - Uses existing read-only `/models` and `/health` clients.
  - Does not add debug, sources, or agent trace controls.

- `frontend-react/src/features/conversation/ConversationSidebar.tsx`
  - Business behavior remains unchanged.
  - Layout is handled by Shell CSS rather than business logic changes.

- `frontend-react/src/features/chat/ChatArea.tsx`
  - Keeps the existing Chat, Agent, streaming, sources, debug, and temp file behavior.
  - Replaces the hand-written right-side detail `<aside>` with the unified `ContextPanel` component.
  - Keeps `DetailsTab` locally to avoid changing stores or hooks.

## Added Components

- `frontend-react/src/components/ContextPanel.tsx`
  - One shared secondary detail surface.
  - Supports workspace variants: chat, agent, knowledge, system.
  - Supports tabs, desktop side panel, and mobile bottom-sheet behavior.

## Deleted Components

- `frontend-react/src/components/DetailsDrawer.tsx`
  - Removed because `ContextPanel` now owns the secondary detail pattern.
  - No remaining imports reference it.

- `frontend-react/src/layouts/AppLayout.tsx`
  - Removed because it was unused and duplicated shell responsibilities.

## Layout Changes

- Added `frontend-react/src/styles/shell.css`.
- `main.tsx` imports shell CSS after existing styles so shell-only rules override legacy page layout safely.
- Desktop shell:
  - Sidebar uses `sidebar-width`.
  - TopBar uses `topbar-height`.
  - Conversation dock scrolls independently.
  - Workspace owns primary scrolling.
  - ContextPanel owns detail scrolling.
- Tablet:
  - Sidebar collapses to icon rail.
  - Chat context panel stays below primary content when constrained.
- Mobile:
  - Navigation becomes compact top rail.
  - Conversation history opens as a drawer with backdrop.
  - ContextPanel opens as a bottom sheet through one details trigger.

## Compatibility Strategy

- Existing Chat, Knowledge, Agent, and System pages remain mounted through `AppShell`.
- Page internals still use legacy classes until later phases.
- No business callbacks, API payloads, streaming behavior, or store state were changed.
- Existing `ToastProvider` from Phase 1 remains mounted at the app root.

## Validation

Typecheck:

- Passed through `npm run build`.

Build:

- `npm run build` passed.

ESLint:

- Not run. The current `frontend-react/package.json` does not define a lint script.

Unit tests:

- Not run. The current project does not define a unit test script.

## Known Limitations

- Chat still contains page-level mode controls, composer, messages, sources, debug, and agent behavior in one component. This is intentionally deferred.
- Knowledge and System pages still use their old page internals.
- ContextPanel is integrated for Chat/Agent detail content first. Knowledge/System detail content will move into it during page-specific refactor phases.
- Mobile ContextPanel bottom sheet is shell-ready, but page-specific detail triggers can be refined in later phases.

## Next Phase Recommendation

Begin Phase 3: Chat Refactor.

Recommended order:

1. Split `ChatArea` into `ChatWorkspace`, `ChatModeControls`, and message/detail sections.
2. Keep `useChatStream`, `useAgentRun`, and conversation store unchanged.
3. Move Sources and Retrieval Debug into the Shell `ContextPanel` pattern without changing API behavior.
4. Refactor `ChatComposer` and `ChatMessageList` after workspace structure is stable.

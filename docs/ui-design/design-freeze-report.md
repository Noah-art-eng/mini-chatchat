# Mini ChatChat Design Freeze Report

This report reviews the current Mini ChatChat design system for React refactor readiness. It covers:

- `01-design-bible.md`
- `02-design-tokens.md`
- `03-page-wireframes.md`
- `04-ui-pattern-library.md`
- `05-component-library.md`
- `component-library.png`
- current `frontend-react/`
- current `backend/` APIs and service capabilities

No new design specification is introduced here. This is a freeze decision and implementation readiness report.

## 1. Overall Assessment

| Area | Score | Assessment |
| --- | ---: | --- |
| Design Completion | 90 / 100 | The system covers philosophy, tokens, page structure, product patterns, and component contracts. It is complete enough to guide a product-grade React refactor. |
| Implementation Readiness | 84 / 100 | React engineers have enough direction to start, but a few token gaps and component consolidation decisions must be handled during Phase 1. |
| Consistency | 87 / 100 | The documents consistently prioritize calm UI, Chat-first hierarchy, source-aware answers, document-centered Knowledge, and timeline-based Agent UI. |
| Maintainability | 86 / 100 | The system separates Bible, Tokens, Wireframes, Patterns, and Components well. Future drift risk is moderate if tokens are not enforced in code. |
| Scalability | 83 / 100 | The system supports Chat, Knowledge, Agent, System, MCP, tools, and future tables/lists. It still needs strict component implementation discipline. |
| Documentation Quality | 91 / 100 | The documentation is clear, structured, and practical. Component contracts are implementation-oriented without becoming code. |

**Overall Score: 87 / 100**

The design system is sufficiently mature to freeze for the next implementation phase. Remaining issues are implementation risks, not design blockers.

## 2. Documentation Coverage

### Coverage Chain

Design Bible:

- Defines product philosophy, hierarchy, workspace roles, Chat/Knowledge/Agent/System experience, motion, micro-interactions, button/input/status language, and brand language.

Design Tokens:

- Defines light-theme semantic colors, typography, spacing, radius, shadow, border, motion, size, z-index, CSS variable examples, and usage rules.

Wireframes:

- Defines App Shell, Sidebar, Chat, Agent, Knowledge, System, Context Panel, dialogs, toast placement, responsive behavior, primary actions, empty states, forbidden patterns, and component mapping.

UI Pattern Library:

- Defines product-level organization patterns for shell, chat, knowledge, agent, system, context panel, CTA hierarchy, empty/loading/error/source/timeline/list/table/dialog/toast flows.

Component Library:

- Defines reusable component contracts across Foundation, Navigation, Input/Action, Feedback, Display/Data, Chat, Knowledge, Agent, System, and Overlay components.

### Repetition

Acceptable repetition exists around:

- One primary CTA.
- Sources stay with assistant answers.
- Agent should be timeline-first.
- Debug should not be default.
- Knowledge should be document-centered.
- Dialogs confirm destructive action.

This repetition is useful because these are key constraints. It is not harmful.

### Omissions

No critical product area is missing. Minor omissions remain:

- Breakpoint and layout token values are suggested but not formalized in `02-design-tokens.md`.
- Toast and Dialog behavior are specified conceptually, but not implemented.
- Some accessibility behaviors, such as focus trap and tab keyboard model, are specified in component contracts but not yet reflected in current components.

### Responsibility Boundaries

The document responsibilities are clean:

- Bible: why the product should feel this way.
- Tokens: what values are allowed.
- Wireframes: what regions exist.
- Pattern Library: how information flows.
- Component Library: how reusable components behave.

No responsibility conflict blocks implementation.

## 3. Token Coverage

### Critical

No critical missing token blocks the React refactor.

### Recommended

These should be added or aliased during Foundation implementation:

- `breakpoint-mobile`
- `breakpoint-tablet`
- `breakpoint-laptop`
- `breakpoint-desktop`
- `breakpoint-wide`
- `topbar-height`
- `page-header-min-height`
- `panel-gap`
- `workspace-padding-x`
- `workspace-padding-y`
- `dialog-width-sm`
- `dialog-width-md`
- `dialog-width-lg`
- `toast-offset-x`
- `toast-offset-y`
- `table-row-height`
- `list-row-height`
- `focus-ring-width`
- `focus-ring-offset`
- `safe-area-bottom`
- `bottom-sheet-max-height`

### Nice to Have

- `timeline-marker-size`
- `timeline-line-width`
- `skeleton-height-sm`
- `skeleton-height-md`
- `skeleton-height-lg`
- `composer-sticky-offset`
- `context-panel-min-width`
- `context-panel-max-width`
- `drawer-width`
- `mobile-nav-height`
- `page-section-gap`

### Token Freeze Assessment

The token system is good enough to start, but Phase 1 should normalize runtime CSS to the documented `02-design-tokens.md` names. Current `frontend-react/src/styles.css` and `frontend-react/src/design-system.css` contain older/raw token systems that do not fully match the frozen token names.

## 4. Component Coverage

### Chat

Existing:

- `ChatArea`
- `ChatComposer`
- `ChatMessageList`
- `ChatEmptyState`
- `SourcesPanel`
- `RetrievalDebugPanel`
- `FeedbackControls`

Missing:

- `AssistantMessage`
- `UserMessage`
- `SourceReferenceList`
- `SourceCard` as a reusable component
- `StreamingMessage`
- `MessageActions`

Optional:

- `AdvancedSettingsDisclosure`
- `TempFileUploader`

Future:

- `CitationPopover`
- `StopGenerationButton`, only if streaming abort is implemented.

### Knowledge

Existing:

- `KnowledgeBasePage`
- `KnowledgeBasePanel`

Missing:

- `KnowledgeWorkspace`
- `KnowledgeBaseList`
- `KnowledgeToolbar`
- `DocumentTable`
- `DocumentRow`
- `DocumentDetailPanel`
- `ChunkViewer`
- `KnowledgeBackupActions`
- `FileUploadArea`

Optional:

- `DocumentActionMenu`
- `DocumentStatusSummary`

Future:

- `DocumentSearch`
- `ChunkSearchResults`

### Agent

Existing:

- `AgentTracePanel`
- agent result rendering helpers inside `AgentTracePanel`

Missing:

- `AgentWorkspace`
- `AgentTimeline`
- `AgentStep`
- `ToolCallSummary`
- `ToolObservation`
- `AgentFinalAnswer`

Optional:

- `RawTraceDisclosure`
- `PlannerPanel`

Future:

- `McpToolObservation`
- `MultiStepPlannerView`

### System

Existing:

- `SettingsPage`
- `LanguageSwitcher`

Missing:

- `SystemOverview`
- `DependencyStatusList`
- `ModelStatusCard`
- `ToolRegistryList`
- `McpStatusList`
- `SystemDetailPanel`

Optional:

- `HealthSummary`
- `ProviderBadge`

Future:

- `RuntimeEnvironmentPanel`

### Foundation / Shared

Existing:

- `ConfirmDialog`
- partial CSS primitives: `.button-primary`, `.button-secondary`, `.button-danger`, `.inline-error`, `.sr-only`

Missing:

- `Text`
- `Heading`
- `Button`
- `Icon`
- `Divider`
- `Surface`
- `Stack`
- `Inline`
- `VisuallyHidden`
- `InlineError`
- `Toast`
- `Skeleton`
- `StatusBadge`
- `DataTable`
- `ContextPanel`

Optional:

- `Tooltip`
- `PopoverMenu`
- `Tabs`

Future:

- `CommandPalette`, only if global command/search is implemented later.

## 5. Pattern Consistency

### Consistent Patterns

The documents consistently enforce:

- One app shell.
- Chat as visual center.
- Sources as answer support.
- Retrieval debug as secondary.
- Knowledge as document workspace.
- Agent as timeline narrative.
- System as factual runtime status.
- One primary CTA per context.
- Dialogs for destructive decisions.
- Toast for lightweight completion feedback.

### Remaining Pattern Conflicts

Context Panel vs Drawer:

- Current React has both `context-panel` inside `ChatArea` and `DetailsDrawer`.
- Design system says one Context Panel pattern should serve all detail surfaces.
- Action: converge during Shell/ContextPanel refactor.

Knowledge Debug placement:

- Current `KnowledgeBasePage` embeds `RetrievalDebugPanel` in the page grid.
- Design system says Knowledge should be document-centered and Debug secondary.
- Action: move Retrieval Debug into Context Panel or an advanced detail area.

System naming:

- Current React route is `settings`; design system calls it System.
- Backend supports true System status.
- Action: keep route name if needed, but user-facing label and component should become System.

Stop Generation:

- Wireframes mention optional Stop Generation.
- Current frontend has streaming but no confirmed abort UI contract.
- Action: do not implement visible Stop until abort behavior exists.

## 6. React Mapping

| Existing Component | Action |
| --- | --- |
| `frontend-react/src/pages/App.tsx` | Refactor |
| `frontend-react/src/components/AppShell.tsx` | Refactor |
| `frontend-react/src/layouts/AppLayout.tsx` | Remove |
| `frontend-react/src/components/SidebarNavigation.tsx` | Refactor |
| `frontend-react/src/components/TopBar.tsx` | Refactor |
| `frontend-react/src/features/conversation/ConversationSidebar.tsx` | Refactor |
| `frontend-react/src/features/chat/ChatArea.tsx` | Replace |
| `frontend-react/src/components/ChatComposer.tsx` | Refactor |
| `frontend-react/src/components/ChatMessageList.tsx` | Refactor |
| `frontend-react/src/components/ChatEmptyState.tsx` | Refactor |
| `frontend-react/src/components/SourcesPanel.tsx` | Refactor |
| `frontend-react/src/components/RetrievalDebugPanel.tsx` | Refactor |
| `frontend-react/src/components/FeedbackControls.tsx` | Refactor |
| `frontend-react/src/components/AgentTracePanel.tsx` | Replace |
| `frontend-react/src/features/kb/KnowledgeBasePage.tsx` | Replace |
| `frontend-react/src/components/KnowledgeBasePanel.tsx` | Replace |
| `frontend-react/src/features/settings/SettingsPage.tsx` | Replace |
| `frontend-react/src/components/ConfirmDialog.tsx` | Refactor |
| `frontend-react/src/components/DetailsDrawer.tsx` | Remove |
| `frontend-react/src/components/LanguageSwitcher.tsx` | Keep |
| `frontend-react/src/hooks/useChatStream.ts` | Keep |
| `frontend-react/src/hooks/useAgentRun.ts` | Keep |
| `frontend-react/src/hooks/useKbPanel.ts` | Keep |
| `frontend-react/src/stores/conversationStore.tsx` | Keep |
| `frontend-react/src/api/chat.ts` | Keep |
| `frontend-react/src/api/agent.ts` | Keep |
| `frontend-react/src/api/kb.ts` | Keep |
| `frontend-react/src/api/conversations.ts` | Keep |
| `frontend-react/src/api/feedback.ts` | Keep |
| `frontend-react/src/api/system.ts` | Refactor |
| `frontend-react/src/types/*.ts` | Keep |
| `frontend-react/src/styles.css` | Replace |
| `frontend-react/src/design-system.css` | Replace |
| `Text` | New |
| `Heading` | New |
| `Button` | New |
| `Icon` | New |
| `Surface` | New |
| `Stack` | New |
| `Inline` | New |
| `InlineError` | New |
| `ToastProvider` | New |
| `Skeleton` | New |
| `StatusBadge` | New |
| `ContextPanel` | New |
| `DocumentTable` | New |
| `DocumentRow` | New |
| `AgentTimeline` | New |
| `ToolObservation` | New |
| `SystemOverview` | New |

## 7. API Mapping

### Components Covered by Real Backend API

Chat components:

- `/kb_chat`
- `/chat`
- `/chat/completions`
- `/chat/feedback`
- `/temp_upload`
- `/file_chat`

Conversation components:

- `GET /conversations`
- `GET /conversations/{conversation_id}/messages`
- `PATCH /conversations/{conversation_id}`
- `DELETE /conversations/{conversation_id}`

Knowledge components:

- `GET /knowledge_bases`
- `POST /knowledge_bases`
- `DELETE /knowledge_bases/{kb_name}`
- `POST /switch_kb`
- `GET /documents`
- `POST /upload`
- `GET /documents/{filename}/download`
- `POST /documents/{filename}/reindex`
- `DELETE /documents/{filename}`
- `GET /knowledge_bases/{kb_name}/export`
- `POST /knowledge_bases/import`
- `GET /file_docs/{filename}`
- `GET /chunk/{chunk_id}`
- `GET /stats`
- `POST /reload`
- `POST /sync_files`
- `POST /search_docs`

Agent components:

- `GET /agent/tools`
- `POST /agent/tools/{tool_name}/run`
- `POST /agent/decide`
- `POST /agent/run_once`
- `POST /agent/run`
- `POST /agent/run_multi`
- `POST /agent/plan_run`
- `POST /agent/plan_run_stream`
- `GET /agent/mcp/servers`
- `GET /agent/mcp/tools`
- `POST /agent/mcp/tools/{tool_name}/run`
- `POST /agent/mcp/servers/{server_name}/shutdown`

System components:

- `GET /health`
- `GET /health/deps`
- `GET /models`

### Designed Components Without Current Backend-Dependent UI

These are design-ready and backend-supported, but not fully represented in current React:

- `ToolRegistryList`
- `McpStatusList`
- `SystemDetailPanel`
- `DocumentDetailPanel`
- `ChunkViewer`
- `DocumentTable`
- `AgentTimeline`
- `ToolObservation`

### Design Exceeds Backend Capability

- `StopGenerationButton`: do not implement unless frontend stream abort behavior is confirmed.
- Login/Auth: not in design freeze and not supported by backend.
- Global Search across all conversations/KB: not in design freeze and not supported as a unified backend API.
- Editable provider/model settings: explicitly forbidden; backend only exposes read-only model/status info.

### Backend Supported but UI Not Fully Reflected

- `/agent/mcp/servers`
- `/agent/mcp/tools`
- `/agent/mcp/tools/{tool_name}/run`
- `/agent/plan_run_stream`
- `/file_docs/{filename}`
- `/chunk/{chunk_id}`
- `/sync_files`
- `/reload`
- `/chat/completions` status/availability display

These do not block refactor. They inform System, Agent, and Knowledge later phases.

## 8. Refactor Readiness

**YES**

React refactor can start now.

Why:

- The product philosophy is stable.
- Tokens provide a semantic foundation.
- Wireframes define all major workspaces and states.
- Pattern Library defines information flow and action hierarchy.
- Component Library defines reusable component contracts.
- Backend APIs are sufficient for all core designed experiences.
- No critical design conflict remains.

Conditions:

- Start with Foundation and Shell before page refactors.
- Normalize CSS variables to `02-design-tokens.md`.
- Remove duplicate detail patterns by converging `DetailsDrawer` and `context-panel`.
- Do not implement fake unsupported controls.

## 9. Refactor Roadmap

### Phase 1: Foundation

Implement design tokens and primitives first.

- Normalize CSS variables to `02-design-tokens.md`.
- Add missing recommended layout tokens in implementation if not yet documented.
- Build `Text`.
- Build `Heading`.
- Build `Button`.
- Build `Icon`.
- Build `Divider`.
- Build `Surface`.
- Build `Stack`.
- Build `Inline`.
- Build `VisuallyHidden`.
- Build `InlineError`.
- Build `StatusBadge`.
- Build `Skeleton`.

### Phase 2: Shell

Create the stable product frame.

- Refactor `AppShell`.
- Refactor `SidebarNavigation`.
- Refactor `ConversationSidebar`.
- Refactor `TopBar`.
- Build `ContextPanel`.
- Build `ToastProvider`.
- Refactor `ConfirmDialog`.
- Remove `AppLayout`.
- Remove or replace `DetailsDrawer`.

### Phase 3: Chat

Rebuild the core reading experience.

- Replace `ChatArea` with `ChatWorkspace`.
- Refactor `ChatComposer`.
- Split `ChatMessageList` into `UserMessage`, `AssistantMessage`, `StreamingMessage`.
- Build `SourceReferenceList`.
- Refactor `SourcesPanel` using `SourceCard`.
- Refactor `FeedbackControls`.
- Keep `useChatStream` and conversation store.

### Phase 4: Knowledge

Make KB management a document workspace.

- Replace `KnowledgeBasePage`.
- Replace `KnowledgeBasePanel`.
- Build `KnowledgeWorkspace`.
- Build `KnowledgeBaseList`.
- Build `KnowledgeToolbar`.
- Build `DocumentTable`.
- Build `DocumentRow`.
- Build `FileUploadArea`.
- Build `KnowledgeBackupActions`.
- Build `DocumentDetailPanel`.
- Build `ChunkViewer`.
- Move Retrieval Debug out of the main KB grid.

### Phase 5: Agent

Make Agent execution understandable.

- Replace `AgentTracePanel`.
- Build `AgentWorkspace`.
- Build `AgentTimeline`.
- Build `AgentStep`.
- Build `ToolCallSummary`.
- Build `ToolObservation`.
- Build `AgentFinalAnswer`.
- Keep `useAgentRun`.
- Support existing agent, planner, MCP, readonly tool result types.

### Phase 6: System

Convert Settings into real System workspace.

- Replace `SettingsPage` with `SystemOverview`.
- Connect `/health`.
- Connect `/health/deps`.
- Connect `/models`.
- Connect `/agent/tools`.
- Connect `/agent/mcp/servers`.
- Connect `/agent/mcp/tools`.
- Build `DependencyStatusList`.
- Build `ModelStatusCard`.
- Build `ToolRegistryList`.
- Build `McpStatusList`.
- Build `SystemDetailPanel`.

### Phase 7: Integration QA

Validate end-to-end behavior.

- Desktop/laptop/tablet/mobile layout checks.
- Chat local KB/search/temp KB.
- Agent calculator/KB/filesystem/sqlite/browser observations.
- Knowledge upload/import/export/reindex/delete.
- System health/deps/models/tools/MCP.
- Conversation history, rename, delete, restore.
- Sources persistence.
- Feedback.
- No console errors.
- No network payload regressions.

## 10. Risks

### Risk 1: Token Drift

Current CSS has multiple token systems and raw/legacy values. If refactor starts page-by-page without Foundation normalization, visual drift will continue.

Impact:

- Rework.
- Inconsistent UI.
- Hard-to-maintain CSS.

Mitigation:

- Phase 1 must normalize tokens before page work.

### Risk 2: Duplicate Detail Surfaces

Current code has `context-panel` and `DetailsDrawer`. If both survive, mobile/desktop behavior will diverge.

Impact:

- Confusing UX.
- Duplicate state logic.
- Accessibility bugs.

Mitigation:

- Build one `ContextPanel` with responsive sheet behavior.

### Risk 3: Over-large Page Components

`ChatArea`, `KnowledgeBasePanel`, and `AgentTracePanel` currently mix orchestration, layout, state decisions, and rendering variants.

Impact:

- Hard refactor.
- Fragile tests.
- Repeated bugs when adding states.

Mitigation:

- Split into workspace, list, row/card, observation, and action components.

### Risk 4: Fake Controls

Design mentions optional capabilities such as Stop Generation or System details that require real behavior. Implementing them without backend/frontend support would break trust.

Impact:

- Product feels unfinished.
- Test failures.
- User confusion.

Mitigation:

- Only expose actions backed by real API or real local behavior.

### Risk 5: Accessibility Debt

Current `ConfirmDialog` lacks focus trap and robust keyboard behavior. Tabs and popovers are basic.

Impact:

- Keyboard issues.
- Screen reader issues.
- Modal escape/focus bugs.

Mitigation:

- Treat accessibility as component contract in Phase 1/2, not a final polish task.

### Risk 6: System Page Scope Creep

System can become a random dashboard if Tools, MCP, Health, Models, and Dependencies are not grouped by the frozen pattern.

Impact:

- Visual clutter.
- Maintenance complexity.

Mitigation:

- Follow Overview -> Dependencies -> Models -> Tools -> MCP -> Detail.

## 11. Freeze Decision

**APPROVED**

Design documentation should be frozen for the React refactor.

React refactor should begin immediately, starting with Foundation and Shell.

Critical issues:

- **0**

Required implementation constraints:

- Do not add new design documents before starting React work.
- Do not add unsupported UI controls.
- Do not keep duplicate detail surface patterns.
- Do not continue patching current page CSS as the main strategy.
- Build the refactor from tokens and reusable components upward.

# Mini ChatChat UI Pattern Library v1

This document defines product-level UI patterns for Mini ChatChat. It describes how regions, information flows, details, and actions are organized across the product.

This is not a wireframe, component library, or interaction specification. It does not define button visuals, input styles, cards, color values, shadows, or component implementation details. Those belong in `02-design-tokens.md` and future component documentation.

The patterns below are based on the current product capabilities: chat, local KB, temp KB, search engine mode, conversations, sources, feedback, knowledge base management, system health, agent tools, MCP status, and readonly tool observations.

## 1. App Shell Pattern

The product has one app pattern:

Sidebar -> TopBar -> Workspace -> Context Panel -> Toast -> Dialog

The shell keeps orientation stable while each workspace changes its center content.

### Responsibilities

Sidebar:

- Provides product identity.
- Holds primary workspace navigation.
- Holds conversation history when the active workspace is Chat or Agent.
- Contains the only global New Chat action.
- Stays quiet and secondary to the workspace.

TopBar:

- Shows current runtime context at a glance.
- May show provider/model/health summary.
- Must not become a developer status dump.
- Must not contain retrieval debug controls.

Workspace:

- Owns the page's primary task.
- Contains the page header, central content flow, and primary CTA.
- Owns primary vertical scrolling.

Context Panel:

- Shows details that support the selected workspace content.
- Uses the same conceptual pattern across Chat, Knowledge, Agent, and System.
- Owns its own scroll.
- Can collapse on constrained viewports.

Toast:

- Reports completed background or secondary actions.
- Never replaces inline errors for failed primary tasks.

Dialog:

- Handles destructive or blocking decisions.
- Must interrupt only when the user needs to confirm or resolve something.

### Permanence

Always present:

- Sidebar or mobile navigation entry.
- TopBar.
- Workspace.
- Toast layer.
- Dialog layer.

Page-dependent:

- Conversation history dock.
- Context Panel contents.
- Workspace controls.

Collapsible:

- Sidebar on tablet/mobile.
- Context Panel on tablet/mobile.
- Advanced controls inside workspace or panel.

### Scroll Ownership

- Workspace scrolls page content.
- Context Panel scrolls detail content.
- Sidebar conversation history scrolls independently.
- Dialog body scrolls only when content exceeds available height.

### Do

- Keep the user's current task in the Workspace.
- Use Context Panel for supporting evidence and detail.
- Keep Sidebar visually quieter than Chat content.
- Use tokens for shell widths, spacing, z-index, and motion.

### Don't

- Put global debug controls in TopBar.
- Create separate drawer, panel, and modal patterns for the same detail.
- Let Sidebar become the visual center.
- Depend on hidden body overflow that makes content unreachable.

## 2. Chat Pattern

Chat is an evidence-aware reading flow.

Information order:

Page Header -> Conversation -> Assistant Message -> Source References -> Message Actions -> Composer -> Context Panel

### Why This Order

The user asks, reads, verifies, and continues. The answer must be visually dominant, the composer must remain available, and sources must be close enough to build trust without interrupting reading.

### Required Elements

Always present:

- Page header with current mode context.
- Conversation stream or empty state.
- Composer.
- Context Panel access.

Present when available:

- Sources after assistant messages.
- Feedback actions after assistant messages.
- Streaming state during generation.
- Inline error near failed generation.

Mode-specific:

- `local_kb`: show current KB context.
- `search_engine`: show Web Search Mode context.
- `temp_kb`: show temp file upload/status before send.
- `agent`: use Agent Pattern instead of normal Chat Pattern.

### Expansion Rules

Collapsed by default:

- Top K.
- Score threshold.
- Rerank.
- Prompt name.
- Model and temperature controls.
- Raw retrieval details.

Never in Header:

- Chunk previews.
- Full source cards.
- Retrieval debug controls.
- Raw prompt/debug data.
- Tool trace.

### Source Relationship

Assistant answer -> compact source references -> right panel source detail.

The answer owns the source references. The Context Panel expands them.

### Do

- Keep the current answer as the visual center.
- Place source references immediately after the relevant answer.
- Keep feedback low-emphasis.
- Keep advanced retrieval controls out of the main reading flow.
- Keep composer aligned with message reading width.

### Don't

- Make messages look like consumer chat bubbles if readability suffers.
- Put sources in the page header.
- Show database fields as source primary content.
- Show Retrieval Debug by default.
- Let mode controls overpower the conversation.

## 3. Knowledge Pattern

Knowledge is a document workspace.

Workflow:

Knowledge Selection -> Toolbar -> Document List -> Document Detail -> Chunk Viewer -> Context Panel

### Why Document Is Center

The user is managing evidence. The document is the core object. Knowledge base selection scopes the workspace, but the document list is where users inspect health, act, and recover from errors.

### Required Elements

Always present:

- Current KB identity.
- KB list or selector.
- Document list state.
- Upload entry when a KB exists.

Present when available:

- Document status.
- Chunk count.
- Upload parameters.
- Row actions.
- Import/export.
- Selected document detail.
- Chunk viewer.

### Information Ownership

Knowledge Selection:

- Selects active KB.
- Creates workspace scope.
- Does not replace document management.

Toolbar:

- Holds primary KB-local operation.
- Contains Upload Document as the normal primary action.
- Keeps Import ZIP and Export as secondary workspace operations.

Document List:

- Owns scanning and row actions.
- Shows status, chunks, parameters, and errors.
- Keeps repeated row actions compact.

Document Detail:

- Owns metadata, path detail, error detail, and selected document status.
- It is the right place for long filenames and internal paths when useful.

Chunk Viewer:

- Belongs to a selected document.
- Never floats as an unrelated dashboard card.

Context Panel:

- Shows selected document detail, chunk detail, and stats.

### Do

- Make Document List the center of Knowledge.
- Treat Chunk Viewer as detail, not global content.
- Keep Delete behind confirmation.
- Keep Import ZIP and Export grouped as backup/migration actions.
- Show indexing failures close to the document.

### Don't

- Turn Knowledge into a button collection.
- Put chunk details above the document list by default.
- Expose `.json` import when backend supports ZIP import.
- Make every row action primary.
- Show internal paths as the first thing users read.

## 4. Agent Pattern

Agent is a guided execution narrative.

Information order:

Goal -> Planning -> Timeline -> Tool -> Observation -> Final Answer -> Composer -> Trace Panel

### Why This Order

Agent work needs explainability. The user should understand what the agent decided, what it used, what it observed, and what answer it produced. Final Answer is the destination; trace is supporting evidence.

### Required Elements

Always present:

- Goal or empty goal prompt.
- Composer / Run request entry.
- Agent mode context.
- Trace Panel access.

Running state:

- Planning.
- Current step.
- Tool call summary.
- Observation summary when available.

Completed state:

- Timeline status.
- Tool used.
- Observation.
- Final Answer.

Failure state:

- Failed step.
- Tool error.
- Recovery action when available.
- Final answer explaining limitation if generated.

### Tool Information Pattern

Every tool follows:

Tool name -> arguments summary -> observation summary -> optional raw detail

Tool-specific content should be formatted for humans:

- `calculator`: expression and result.
- `kb_search`: sources, chunks, score summary.
- `sqlite_readonly_query`: columns, rows, row count, truncated state.
- `filesystem_readonly_read`: path, content preview, truncated state.
- `browser_search`: title, URL, snippet.
- `browser_read`: title, URL, text preview, truncated state.
- `current_time`: UTC and local time.

### Raw JSON

Raw JSON is always secondary:

- Collapsed by default.
- Used for debugging or verification.
- Never the main Agent page content.

### Do

- Make Final Answer the visual endpoint.
- Use a timeline over a console log.
- Use plain-language step labels.
- Show tool failures in the timeline.
- Keep raw payloads collapsible.

### Don't

- Make Agent look like terminal output.
- Show raw JSON as primary content.
- Hide the final answer below trace details.
- Create a different layout for every tool.
- Let tool observation replace the answer.

## 5. System Pattern

System is a runtime overview, not a dashboard.

Information order:

Overview -> Dependencies -> Models -> Tools -> MCP -> Detail

### Why Overview Is First

System exists to answer one question quickly: can this workspace run correctly now? The user should see overall health before inspecting dependencies.

### Required Elements

Overview:

- Service status.
- Provider.
- Version.
- Environment summary when supported.

Dependencies:

- Database.
- Data directory.
- Uploads directory.
- Chat provider.
- Embedding model.

Models:

- Current chat provider.
- Default chat model.
- Base URL without API key.
- Embedding model.

Tools:

- Tool registry availability.
- Built-in tools.
- Tool health/status if available.

MCP:

- MCP server status.
- MCP tool availability.
- Degraded/unavailable explanation.

Detail:

- Expandable dependency/model/tool/MCP details.
- No editable settings unless backend can save them.

### Do

- Show real status from real APIs.
- Put Overview at the top.
- Keep API keys hidden.
- Let users refresh status.
- Treat degraded state as actionable but calm.

### Don't

- Create fake settings forms.
- Show random cards without hierarchy.
- Put provider secrets on screen.
- Mix System controls into Chat header.
- Make MCP errors look like full app failure when core chat still works.

## 6. Context Panel Pattern

Mini ChatChat has one Context Pattern.

Context Panel is a secondary detail surface that changes by workspace:

- Chat: Sources, Chunks, Retrieval.
- Knowledge: Document details, Chunk details, Stats.
- Agent: Plan, Tools, Trace.
- System: Dependency detail, Model detail, Tool detail, MCP detail.

### Open Rules

Open by default on desktop when:

- Chat has sources or selected message detail.
- Agent is running or has completed trace.
- Knowledge has selected document detail.
- System has selected dependency/tool/MCP detail.

Collapsed by default when:

- No detail exists.
- Viewport is tablet/mobile.
- User is in a primary writing/reading flow and panel would crowd content.

Empty when:

- No sources for current or selected assistant message.
- No agent trace yet.
- No document selected.
- No system detail selected.

### State Priority

Selected item detail beats latest detail:

- Selected assistant message sources over latest sources.
- Selected document over global stats.
- Selected agent step over full trace summary.
- Selected dependency/tool over general system overview.

### Do

- Reuse the same panel mental model everywhere.
- Keep detail secondary.
- Allow collapse.
- Give every empty panel a clear empty state.

### Don't

- Create separate detail mechanisms per page.
- Duplicate identical detail in panel and modal.
- Show raw debug data by default.
- Let Context Panel steal focus from the primary workspace.

## 7. Primary Action Pattern

Each page or local region has at most one Primary CTA.

### Page Primary Actions

Chat:

- Primary: Send Message.
- Location: Composer.

Agent:

- Primary: Run Agent / Send Request.
- Location: Composer.

Knowledge:

- Primary: Upload Document when KB exists.
- Primary: Create KB only when no KB exists.
- Location: Knowledge toolbar or empty state.

System:

- Primary: Refresh Status.
- Location: System overview header.

### Secondary Actions

Secondary actions support the primary task:

- Select chat mode.
- Select KB.
- Open advanced settings.
- Download document.
- Reindex document.
- Import ZIP.
- Export KB.
- Show detail.
- Retry failed operation.

### Danger Actions

Danger actions are destructive:

- Delete conversation.
- Delete document.
- Delete knowledge base.

Danger actions:

- Never share primary styling.
- Require confirmation.
- Stay visually distinct.

### Do

- Keep one primary action per context.
- Place primary action where the task is performed.
- Make secondary actions quieter.
- Confirm destructive actions.

### Don't

- Put multiple primary buttons in one toolbar.
- Make row actions primary.
- Place danger actions beside primary actions with equal weight.
- Use disabled buttons without explanation when the reason is user-fixable.

## 8. Empty State Pattern

All empty states follow:

Title -> Description -> One Action

### Content Rules

Title:

- Short.
- Names the state.

Description:

- One sentence.
- Explains what happened or what to do next.

Action:

- Optional.
- At most one.
- Must be real and supported.

### Common Empty States

No conversations:

- Action: New Chat.

Empty chat:

- Action: focus composer or use one suggestion.

No sources:

- Action: none.

No knowledge bases:

- Action: Create KB.

Empty knowledge base:

- Action: Upload Document.

No agent trace:

- Action: Run Agent.

MCP unavailable:

- Action: Refresh Status.

System degraded:

- Action: Refresh Status.

### Do

- Keep empty states calm.
- Use one useful action.
- Match the current workspace.
- Use real backend-supported actions.

### Don't

- Use marketing copy.
- Show decorative illustration stacks.
- Offer many buttons.
- Pretend unsupported features exist.

## 9. Loading Pattern

Loading communicates scope.

### Loading Types

Skeleton:

- Use for known layout loading.
- Best for conversation list, document list, system sections, and source cards.

Spinner:

- Use for small inline actions.
- Best for button-level work such as Refresh, Reindex, Import, Export.

Progress:

- Use when a multi-step task is happening.
- Best for upload/import/indexing/agent planning when progress can be described.

Inline:

- Use for local action status.
- Best for streaming, temp upload, file upload, and feedback save.

### Workspace Loading

Chat:

- Conversation history loading can use skeleton rows.
- Message generation uses streaming state, not a generic spinner.

Knowledge:

- Document list loading uses skeleton list/table.
- Upload/import/reindex uses inline progress text near the action.

Agent:

- Running state uses timeline progress.
- Tool call status appears in timeline.

System:

- System sections can load independently.
- Overall page can show a quiet loading state only on first load.

### Do

- Match loading indicator to scope.
- Keep layout stable.
- Show which operation is running.
- Disable repeated action only after request starts.

### Don't

- Use full-page spinner for small row actions.
- Replace streaming with spinner-only state.
- Let loading silently block user input.
- Use progress when no progress meaning exists.

## 10. Error Pattern

Errors appear where recovery happens.

### Error Types

Inline Error:

- Failed chat generation.
- Missing temp file.
- Upload parse/index error.
- Form validation.
- Tool failure.
- System dependency row failure.

Toast Error:

- Background action failed after user leaves the immediate context.
- Non-blocking secondary action failed.

Dialog Error:

- Blocking action failed inside an already-open dialog.
- Destructive confirmation failed after submit.

Page Error:

- Whole workspace cannot load.
- Backend unavailable for that workspace.

### Error Content

Every error should answer:

- What failed?
- Why, if known?
- What can the user do next?

### Do

- Keep errors close to the failed action.
- Preserve user input where possible.
- Keep conversation id and state when chat errors.
- Show tool errors inside Agent timeline.
- Keep API keys hidden.

### Don't

- Use toast as the only feedback for a failed primary action.
- Clear current state on recoverable errors.
- Show raw stack traces by default.
- Display `invalid_api_key` without a user-readable explanation.

## 11. Source Pattern

Sources support trust.

Information order:

Assistant Answer -> Source References -> Context Panel Detail

### Source Reference

Appears directly after an assistant answer:

- Compact.
- Numbered.
- Shows readable file/title/URL.
- Does not show all retrieval metadata.

### Context Panel Detail

Expands source detail:

- Title or file name.
- URL when available.
- Preview text.
- Chunk reference when useful.
- Score/debug fields only in Retrieval mode.

### Retrieval Debug

Retrieval Debug may show:

- `source`
- `chunk_id`
- `distance`
- `vector_distance`
- `bm25_score`
- `hybrid_score`
- `rerank_score`

Normal Sources must not lead with these fields.

### Do

- Keep sources attached to the answer they support.
- Use readable source labels.
- Make URL sources clickable.
- Preserve source detail for historical assistant messages when metadata exists.

### Don't

- Put sources in the Header.
- Show database field names as primary source content.
- Mix debug scores into normal citation cards.
- Claim historical sources exist when they were not saved.

## 12. Timeline Pattern

Timeline represents process.

Standard flow:

Planning -> Searching -> Calling Tool -> Observation -> Completed

### Timeline Item

Each item contains:

- Status.
- Plain-language label.
- Optional tool name.
- Short observation.
- Optional detail disclosure.

### Statuses

- Pending.
- Running.
- Completed.
- Failed.
- Skipped.

### Tool Timeline

All tools use the same timeline pattern:

- `calculator`
- `current_time`
- `kb_search`
- `browser_search`
- `browser_read`
- `filesystem_readonly_read`
- `sqlite_readonly_query`
- MCP-backed tools when enabled.

### Do

- Use timeline for Agent progress.
- Keep observations summarized.
- Put raw details behind disclosure.
- Show failure at the exact failed step.

### Don't

- Render agent execution as console text.
- Invent a different process display for each tool.
- Hide final answer below long trace.
- Show raw JSON before human-readable state.

## 13. List Pattern

Lists are for scanning selectable objects.

Shared by:

- Conversations.
- Documents when table density is not needed.
- Tools.
- Dependencies.
- Models.
- MCP servers.

### List Item Structure

Primary label -> Secondary metadata -> Status -> Optional actions

### States

Hover:

- Reveals low-emphasis actions or menu.

Selected:

- Uses selected background.
- Indicates active object.

Action:

- Row-level actions are secondary.
- Overflow menu is preferred when actions exceed two.

Empty:

- Uses Empty State Pattern.

### Do

- Keep row labels readable.
- Truncate long content safely.
- Use status consistently.
- Keep actions aligned and quiet.

### Don't

- Turn every list row into a card wall.
- Show too many actions by default.
- Make selected row look like a primary CTA.
- Use hover-only actions without keyboard access in final implementation.

## 14. Table Pattern

Tables are for dense, comparable data.

Used by:

- Knowledge documents.
- System dependencies.
- Model/tool status when density increases.
- Future analytics if supported.

### Table Structure

Header -> Rows -> Optional pagination/summary -> Row actions

### Content Rules

- First column is object identity.
- Status has a consistent badge.
- Numeric columns use tabular alignment.
- Long text truncates with access to detail.
- Row actions are compact.

### Responsive Rule

- Desktop: table.
- Tablet/mobile: list rows with the same information order.

### Do

- Use tables only when comparison matters.
- Keep row height consistent.
- Put destructive row actions behind confirmation.
- Use detail panel for long metadata.

### Don't

- Use tables for narrative content.
- Put raw JSON into table cells.
- Create full grid borders unless necessary.
- Make every cell interactive.

## 15. Dialog Pattern

Dialogs handle focused decisions.

Information order:

Header -> Description -> Body -> Actions

### Dialog Roles

Confirm:

- Destructive or irreversible action.

Blocking form:

- Import knowledge base.
- Retry upload failure when file still exists.

Detail:

- Tool failure detail when inline summary is insufficient.

### Action Order

Left to right:

Secondary -> Primary -> Danger

Danger action is farthest right when present.

### Behavior

- ESC cancels unless a request is in progress.
- Enter submits only when focus is on the intended action.
- Loading disables repeated submit.
- Error appears inside dialog body.

### Do

- Use dialog only when interruption is necessary.
- Keep descriptions specific.
- Preserve user context after close.
- Put danger action on the right.

### Don't

- Use dialog for simple success messages.
- Put unrelated controls in dialog footer.
- Close automatically on failed submit.
- Use dialog and toast for the same error.

## 16. Toast Pattern

Toast is lightweight completion feedback.

### Types

Success:

- Feedback saved.
- Document downloaded.
- Reindex completed.
- Import/export completed.

Error:

- Secondary action failed outside the immediate form area.

Warning:

- Non-blocking degraded condition.

Info:

- Background operation notice.

### Placement

- Top-right on desktop.
- Bottom or top safe-area aware stack on mobile.
- Above app content, below blocking dialogs.

### Quantity

- Keep a small stack.
- Newest toast appears closest to attention.
- Similar repeated toasts should merge when possible.

### Lifecycle

- Success/info auto-dismiss.
- Error/warning stays longer.
- Actionable toast can include one action.

### Do

- Use toast for completed secondary actions.
- Keep messages short.
- Include action name and result.
- Respect safe areas.

### Don't

- Use toast as the only error for failed Chat, Agent, Upload, or Form actions.
- Stack unlimited messages.
- Show raw backend payloads.
- Use toast for persistent system health.

## 17. Do / Don't Summary

### App Shell

Do:

- Keep Sidebar, Workspace, and Context Panel roles distinct.

Don't:

- Let every page invent its own layout shell.

### Chat

Do:

- Place sources after the answer and details in Context Panel.

Don't:

- Put sources or retrieval controls in Header.

### Knowledge

Do:

- Keep Document List central and Chunk Viewer in detail.

Don't:

- Make Knowledge a grid of action buttons.

### Agent

Do:

- Show Thinking, Planning, Tool, Observation, Final Answer as a narrative.

Don't:

- Show raw JSON logs as the default experience.

### System

Do:

- Show real health, dependencies, models, tools, and MCP state.

Don't:

- Add settings that cannot be saved.

### Context Panel

Do:

- Use one panel pattern across product.

Don't:

- Create duplicate drawer/modal/panel routes for the same detail.

### Primary Action

Do:

- Keep one primary CTA per local context.

Don't:

- Make row actions primary.

### Empty State

Do:

- Use Title, Description, One Action.

Don't:

- Use marketing copy or multiple competing actions.

### Loading

Do:

- Match indicator to operation scope.

Don't:

- Use full-page loading for small local actions.

### Error

Do:

- Put errors where users can recover.

Don't:

- Clear useful state on recoverable failures.

### Source

Do:

- Use readable citations and put debug scores only in Retrieval.

Don't:

- Lead with database fields.

### Timeline

Do:

- Use one timeline model for all tools.

Don't:

- Create tool-specific layout chaos.

### List

Do:

- Use consistent selected, hover, action, and empty states.

Don't:

- Turn lists into competing card walls.

### Table

Do:

- Use tables for comparable document/system data.

Don't:

- Use tables for narrative chat or agent content.

### Dialog

Do:

- Put danger action farthest right.

Don't:

- Use dialogs for non-blocking success.

### Toast

Do:

- Use toast for lightweight completion feedback.

Don't:

- Use toast as the only primary-task error.

## 18. Pattern to Component Mapping

| Pattern | Future components |
| --- | --- |
| App Shell Pattern | `AppShell`, `Sidebar`, `TopBar`, `Workspace`, `ContextPanel`, `ToastProvider`, `DialogProvider` |
| Chat Pattern | `ChatWorkspace`, `ConversationStream`, `UserMessage`, `AssistantMessage`, `MessageActions`, `Composer`, `SourceReferenceList`, `ContextPanel` |
| Knowledge Pattern | `KnowledgeWorkspace`, `KnowledgeBaseList`, `KnowledgeToolbar`, `DocumentTable`, `DocumentList`, `DocumentDetail`, `ChunkViewer`, `KnowledgeBackupActions` |
| Agent Pattern | `AgentWorkspace`, `AgentGoal`, `AgentTimeline`, `AgentStep`, `ToolCallSummary`, `ToolObservation`, `AgentFinalAnswer`, `TracePanel` |
| System Pattern | `SystemWorkspace`, `SystemOverview`, `DependencyList`, `ModelStatusList`, `ToolRegistryList`, `McpStatusList`, `SystemDetailPanel` |
| Context Panel Pattern | `ContextPanel`, `ContextTabs`, `SourceDetail`, `ChunkDetail`, `ToolDetail`, `DependencyDetail`, `DocumentDetail` |
| Primary Action Pattern | `PrimaryActionSlot`, `SecondaryActionGroup`, `DangerAction`, `ToolbarActions` |
| Empty State Pattern | `EmptyState`, `EmptyStateAction` |
| Loading Pattern | `SkeletonList`, `InlineLoading`, `ProgressStatus`, `StreamingStatus`, `TimelineProgress` |
| Error Pattern | `InlineError`, `PageError`, `DialogError`, `ToastError`, `ToolError` |
| Source Pattern | `SourceReferenceList`, `SourceReference`, `SourceDetailCard`, `RetrievalDebugResult` |
| Timeline Pattern | `Timeline`, `TimelineItem`, `TimelineStatus`, `TimelineObservation` |
| List Pattern | `List`, `ListItem`, `SelectableListItem`, `ListItemMenu`, `ListEmptyState` |
| Table Pattern | `DataTable`, `TableRow`, `TableStatusCell`, `TableActions`, `ResponsiveTableList` |
| Dialog Pattern | `Dialog`, `ConfirmDialog`, `ImportDialog`, `FailureDetailDialog` |
| Toast Pattern | `ToastProvider`, `ToastViewport`, `Toast`, `ToastAction` |

## 19. Token References

Patterns should be implemented using the existing design token categories:

- Color tokens for semantic status and surfaces.
- Typography tokens for hierarchy.
- Spacing tokens for page rhythm and local gaps.
- Radius tokens for panels, dialogs, and selectable rows.
- Shadow tokens only for functional elevation.
- Border tokens for separators and controls.
- Motion tokens for transition timing.
- Size tokens for shell widths, composer width, context panel width, and controls.
- Z-index tokens for dropdown, overlay, dialog, toast, and tooltip layering.

Known token gaps that affect these patterns:

- Breakpoint tokens.
- TopBar height token.
- Page header height/min-height token.
- Panel gap token.
- Dialog width tokens.
- Toast offset tokens.
- Table/list row height tokens.
- Safe-area tokens.
- Focus ring thickness/offset tokens.

These gaps should be resolved in token documentation before broad React refactor implementation.

## 20. Pattern Conflict Notes

No blocking pattern conflict was found.

Watch items:

- Current React uses both `context-panel` and `DetailsDrawer`; future refactor should converge to one Context Panel pattern.
- Current Knowledge page exposes Retrieval Debug inside the page grid; this should move to a secondary context/debug pattern so Knowledge remains document-centered.
- Stop Generation should not be implemented as a visible action unless the frontend actually supports aborting the stream.
- System Pattern includes Tools and MCP because backend APIs exist, but current frontend has not fully connected them yet.

# Mini ChatChat Page Wireframes v1

This document defines low-fidelity page structure for Mini ChatChat. It is not a visual mockup and does not replace `01-design-bible.md` or `02-design-tokens.md`.

The goal is to make every page implementable without inventing unsupported controls. Wireframes must stay aligned with the current backend capabilities: chat, agent, conversations, local KB, temp KB, search engine mode, document management, health/model status, tool registry, and MCP status inspection.

## 1. Global App Shell

Mini ChatChat uses one app shell across all workspaces.

Desktop:

```text
┌────────────────┬──────────────────────────────────────────────────────────────┬────────────────────────┐
│ Sidebar        │ Top Bar                                                      │ Context Panel          │
│                ├──────────────────────────────────────────────────────────────┤                        │
│ Brand          │ Main Workspace                                               │ Sources / Tools /      │
│ Navigation     │                                                              │ Document / System      │
│ Conversations  │ Page-specific content                                        │ detail                 │
│ Utilities      │                                                              │                        │
└────────────────┴──────────────────────────────────────────────────────────────┴────────────────────────┘
```

Structure:

- Sidebar uses `sidebar-width`.
- Collapsed Sidebar uses `sidebar-collapsed-width`.
- Context Panel uses `context-panel-width`.
- Main Workspace fills the remaining width.
- Top Bar height should be a fixed layout token. Recommended missing token: `topbar-height = 64px`.
- Chat composer is sticky to the bottom of the Main Workspace, not the global viewport.
- Main Workspace owns primary scrolling.
- Context Panel owns its own scrolling.
- Sidebar conversation list owns its own scrolling.
- Do not rely on global `body { overflow: hidden; }` if it makes content unreachable.

Context Panel visibility:

- Chat: shown by default on desktop, collapsible on tablet/mobile.
- Agent: shown by default as Agent Trace / Plan / Tools.
- Knowledge: shown for selected document details, chunks, and stats.
- System: optional detail panel for dependency/model/tool/MCP detail.

Layering:

- Toast Layer sits above app shell using `z-toast`.
- Dialog Layer sits above overlays using `z-dialog`.
- Dropdowns and conversation menus use `z-dropdown`.
- Only one overlay family should be active at a time.

## 2. Sidebar Wireframe

Sidebar is orientation, not the product center. The only primary CTA in Sidebar is New Chat.

Expanded desktop:

```text
┌────────────────────────────┐
│ Brand Mark  Mini ChatChat  │
│            AI Workspace    │
├────────────────────────────┤
│ + New Chat                 │  Primary CTA
├────────────────────────────┤
│ Navigation                 │
│  Chat                      │
│  Agent                     │
│  Knowledge                 │
│  System                    │
├────────────────────────────┤
│ Conversation History       │
│ [Search conversations]     │
│                            │
│ Today                      │
│  Docker 是什么        ...  │
│  25 * 8              ...  │
│                            │
│ Recent                     │
│  RAG 检索优化        ...  │
├────────────────────────────┤
│ Workspace / user utility   │
│ Collapse                   │
└────────────────────────────┘
```

Collapsed desktop:

```text
┌────────┐
│ Mark   │
├────────┤
│  +     │
├────────┤
│ Chat   │
│ Agent  │
│ KB     │
│ Sys    │
├────────┤
│ User   │
└────────┘
```

Mobile drawer:

```text
┌──────────────────────────────┐
│ Mini ChatChat          Close │
├──────────────────────────────┤
│ + New Chat                   │
│ Chat / Agent / Knowledge     │
│ System                       │
├──────────────────────────────┤
│ Search conversations         │
│ Conversation list            │
└──────────────────────────────┘
```

States:

- Active navigation uses selected background and medium text.
- Conversation hover reveals secondary menu.
- Conversation row click loads history.
- Conversation menu contains Rename and Delete.
- Delete must open confirmation.
- Empty history shows one short explanation and New Chat action.
- Sidebar must not become a stack of large cards.
- Sidebar visual weight must be below Chat content.

## 3. Chat Page Wireframe

Chat is the default product center.

### A. Empty Chat State

```text
┌──────────────────────────────────────────────────────────────┬────────────────────────┐
│ Chat Header                                                   │ Sources Panel          │
│ Current mode: Local KB · KB: default                          │                        │
├──────────────────────────────────────────────────────────────┤ No sources yet         │
│                                                              │                        │
│                  Mini ChatChat                               │                        │
│        Ask across local knowledge, files, or web.             │                        │
│                                                              │                        │
│  Suggested prompts                                            │                        │
│  [Summarize this KB] [Find Docker notes] [Use web search]      │                        │
│                                                              │                        │
│  ┌──────────────────────────────────────────────┐             │                        │
│  │ Message Mini ChatChat...                    │ Send         │                        │
│  └──────────────────────────────────────────────┘             │                        │
└──────────────────────────────────────────────────────────────┴────────────────────────┘
```

Rules:

- No oversized marketing hero.
- Greeting is quiet and useful.
- Suggested prompts are optional shortcuts, not cards competing with input.
- Composer is aligned to `composer-max-width`.

### B. Active Conversation State

```text
┌──────────────────────────────────────────────────────────────┬────────────────────────┐
│ Chat Header: mode, KB/search/temp context                     │ Sources                │
├──────────────────────────────────────────────────────────────┤                        │
│                                                              │ [01] README.md         │
│  User                                                        │ Preview...             │
│  Docker 是什么                                               │                        │
│                                                              │ [02] docker.txt        │
│  Assistant                                                   │ Preview...             │
│  Docker is ...                                               │                        │
│                                                              │                        │
│  Sources: [01] [02]                                          │                        │
│  Like  Dislike                                               │                        │
│                                                              │                        │
│  ┌──────────────────────────────────────────────┐             │                        │
│  │ Ask a follow-up...                          │ Send         │                        │
│  └──────────────────────────────────────────────┘             │                        │
└──────────────────────────────────────────────────────────────┴────────────────────────┘
```

Rules:

- Chat content max width uses `chat-message-max-width`.
- User and assistant messages are reading blocks, not WeChat-style bubbles.
- User message can be lightly aligned right or visually compact; assistant answer is the primary text block.
- Sources stay close to the corresponding answer.
- Feedback actions are low-emphasis and appear after the assistant answer.
- Composer aligns with assistant text.
- If an assistant message is selected, Context Panel shows that message's persisted sources.

### C. Streaming / Error State

```text
Assistant
Thinking / generating...

Partial answer text▌

[Stop Generation]                         Optional while streaming

Inline error, if generation fails:
Could not complete the response. [Retry]
```

Rules:

- Streaming cursor appears inline at the end of generated text.
- Stop Generation belongs near the active generation, not in the Top Bar.
- Retry belongs next to the failed assistant message.
- Error does not clear conversation id.
- Error does not cause major layout shift.
- Sources event may arrive before answer; panel can update immediately.

### Chat Context Panel

Tabs:

- Sources: default for normal chat.
- Chunks: optional document chunk inspection when linked from sources.
- Retrieval: advanced debugging only.

Advanced settings placement:

- Top K, Threshold, Rerank, Prompt, Model, Temperature belong in a collapsed Advanced Settings area or Retrieval tab.
- They must not permanently occupy the top of the main Chat page.
- Normal users should see mode, KB/search/temp context, messages, sources, and composer first.

Temp file entry:

- Temp upload is visible only in `temp_kb` mode.
- Upload status appears inline above the composer.
- A missing temp file blocks send with inline error: "Please upload a temp file first."

## 4. Agent Page Wireframe

Agent is a separate workspace for tool-assisted work. It should tell a story, not show raw logs.

### A. Empty Agent State

```text
┌──────────────────────────────────────────────────────────────┬────────────────────────┐
│ Agent Header                                                  │ Plan / Tools / Trace   │
│ Tools: calculator, time, KB search, browser, readonly files    │                        │
├──────────────────────────────────────────────────────────────┤ No trace yet           │
│                                                              │                        │
│               What should the agent work on?                  │                        │
│                                                              │                        │
│  Examples                                                     │                        │
│  [Calculate 25 * 8] [Search KB for Docker] [Read README.md]    │                        │
│                                                              │                        │
│  ┌──────────────────────────────────────────────┐             │                        │
│  │ Give the agent a goal...                    │ Run          │                        │
│  └──────────────────────────────────────────────┘             │                        │
└──────────────────────────────────────────────────────────────┴────────────────────────┘
```

### B. Running Agent State

```text
User goal
"Read README.md and summarize the project"

Timeline
● Planning
│  Understanding the request and selecting tools
● Calling tool: filesystem_readonly_read
│  Path: README.md
○ Reviewing result
○ Final answer

Composer remains visible but disabled or secondary while running.
```

### C. Completed Agent State

```text
Timeline
✓ Planning
✓ Calling tool: kb_search
✓ Reviewing result
✓ Completed

Final Answer
Docker is ...

Observation Summary
Sources: README.md, docker.txt

[Show raw JSON]
```

### D. Tool Failure State

```text
Timeline
✓ Planning
✕ Calling tool: sqlite_readonly_query
  The query was rejected because only SELECT is allowed.

Final Answer
I could not complete the database query because the requested operation is not allowed.

[Retry] [Show details]
```

Rules:

- Default view shows human-readable state labels: Planning, Searching, Calling Tool, Reviewing, Completed.
- Raw JSON appears only in collapsed details.
- Agent Trace appears only in Agent page/mode.
- Tool result cards use one shared pattern.
- Supported tools follow the same display model: `browser_search`, `browser_read`, `filesystem_readonly_read`, `sqlite_readonly_query`, `kb_search`, `calculator`, `current_time`.
- Final Answer is the visual endpoint.
- Do not make Agent page look like a console or log stream.

Agent Context Panel tabs:

- Plan
- Tools
- Trace

## 5. Knowledge Page Wireframe

Knowledge is a document workspace, not a button collection.

Desktop:

```text
┌────────────────────┬──────────────────────────────────────────────┬────────────────────────┐
│ KB List            │ Document Workspace                           │ Document Detail        │
│                    │                                              │                        │
│ Current KB         │ Header: default KB                            │ Selected document      │
│ [default]          │ Stats: docs, indexed, chunks, failed          │ Status                 │
│ [python]           │                                              │ Chunks                 │
│                    │ Toolbar: Upload Document   Search / Filter    │ Metadata               │
│ Create KB          │ Secondary: Import ZIP, Export                 │ Chunk preview          │
│ Import ZIP         │                                              │                        │
│ Export             │ Document Table                                │                        │
│                    │ filename | status | chunks | updated | actions│                        │
└────────────────────┴──────────────────────────────────────────────┴────────────────────────┘
```

### A. Empty KB State

```text
Current KB: default

No documents yet.
Upload a .txt, .pdf, .docx, .md, or .csv file to start building this knowledge base.

[Upload Document]
```

Primary action:

- Upload Document when a KB exists.
- Create KB only when no KB exists or user is in KB list management.

### B. KB With Documents

```text
Header
default · 12 documents · 128 chunks · healthy

Toolbar
[Upload Document]  Search documents...
More: Import ZIP, Export

Table
README.md       indexed   12 chunks   300 / 50   Download Reindex Delete
docker.txt      failed    0 chunks     300 / 50   View error Delete
```

### C. Uploading State

```text
Upload area
Selected: sample_rag.txt
Uploading and indexing...
[progress / spinner]

Document row may show status: uploaded → indexed or failed
```

### D. Selected Document State

```text
Document Detail
README.md
Status: indexed
Chunks: 12
Chunk size / overlap: 300 / 50
Original file path
Content path

Chunks
[01] Preview...
[02] Preview...
```

### E. Delete Confirmation

```text
Delete document?
This removes the document metadata and its chunks from the current knowledge base.

[Cancel] [Delete Document]
```

### F. Import / Export State

```text
Backup
[Export KB]

Import
Choose .zip
[Import KB]

Importing...
Restoring files, metadata, and vector store.
```

Rules:

- `.json` import must not appear; backend supports ZIP import.
- Delete never executes from a bare row click; confirm first.
- Row actions are secondary and should appear as compact actions or a row menu.
- Long filenames truncate in the middle or end with tooltip/detail panel access.
- Document list scrolls in the Document Workspace.
- KB list scrolls separately.
- Stats belong near the page header, not in random cards.
- Chunk viewer belongs in Document Detail panel or full detail view.

## 6. System Page Wireframe

Settings becomes System: a status workspace based on real read-only APIs.

Real APIs:

- `/health`
- `/health/deps`
- `/models`
- `/agent/tools`
- `/agent/mcp/servers`
- `/agent/mcp/tools`

### A. Healthy State

```text
┌──────────────────────────────────────────────────────────────┬────────────────────────┐
│ System                                                       │ Detail                 │
│ All core services are available.                             │ Dependency detail      │
│ [Refresh Status]                                             │                        │
├──────────────────────────────────────────────────────────────┤                        │
│ Overview                                                     │                        │
│ Status: ok · Provider: deepseek · Version: x.y.z              │                        │
│                                                              │                        │
│ Dependencies                                                 │                        │
│ Database ok  Data dir ok  Uploads ok  Embedding ok            │                        │
│                                                              │                        │
│ Models                                                       │                        │
│ Chat model  Embedding model                                  │                        │
│                                                              │                        │
│ Tools                                                        │                        │
│ calculator current_time kb_search browser_search ...          │                        │
│                                                              │                        │
│ MCP                                                          │                        │
│ filesystem available / sqlite available / playwright status   │                        │
└──────────────────────────────────────────────────────────────┴────────────────────────┘
```

### B. Degraded State

```text
Status: degraded
Some dependencies need attention.

Dependency row: embedding_model warning
[View detail]
```

### C. Dependency Failure State

```text
Database failed
The backend could not connect to SQLite.

[Refresh Status]
[Show error detail]
```

### D. MCP Unavailable State

```text
MCP
No MCP servers are currently reachable.

This does not affect local KB chat.
[Refresh Status]
```

Rules:

- No fake settings controls.
- No forms for values that cannot be saved.
- Show real status, model, provider, tools, MCP availability, and version.
- Error detail is expandable.
- Refresh has real behavior.
- System page is not a wall of unrelated cards; it is Overview → Dependencies → Models → Tools → MCP.
- API keys are never displayed.

## 7. Context Panel Patterns

Context Panel is one consistent right-side detail system.

Chat:

- Sources
- Chunks
- Retrieval

Agent:

- Plan
- Tools
- Trace

Knowledge:

- Document details
- Chunk details
- Stats

System:

- Dependency detail
- Model detail
- Tool detail
- MCP detail

Desktop:

```text
┌────────────────────────┐
│ Tabs                   │
├────────────────────────┤
│ Selected detail body   │
│ Own scroll container   │
└────────────────────────┘
```

Tablet:

- Context Panel becomes collapsible side sheet.
- Opened from a single "Details" or "Sources" control.
- It must not duplicate content already visible in the main workspace.

Mobile:

- Context Panel becomes bottom sheet or separate tab/page.
- Bottom sheet must be dismissible and scroll independently.

Rules:

- Panel can be collapsed.
- Empty states are explicit.
- Do not create multiple competing Drawer/Modal/Panel entrances for the same detail.
- Do not show Retrieval Debug by default in normal Chat.

## 8. Dialog Wireframes

Dialogs are reserved for irreversible or blocking actions.

### Delete Conversation

- Title: Delete conversation?
- Description: This removes the conversation and all messages.
- Primary action: none.
- Secondary action: Cancel.
- Danger action: Delete Conversation.
- ESC: cancel.
- Enter: confirm only when focus is on danger action.
- Loading: danger action shows progress and disables all actions.
- Error: inline message inside dialog.

### Delete Document

- Title: Delete document?
- Description: This removes the document from the current KB and rebuilds the index.
- Secondary action: Cancel.
- Danger action: Delete Document.
- ESC: cancel.
- Enter: confirm only when focus is on danger action.
- Loading: show "Deleting..." and disable repeated action.
- Error: inline error with retry option.

### Delete Knowledge Base

- Title: Delete knowledge base?
- Description: This removes uploaded files, parsed content, vector store, and metadata for this KB.
- Secondary action: Cancel.
- Danger action: Delete Knowledge Base.
- ESC: cancel.
- Enter: confirm only when focus is on danger action.
- Loading: show progress.
- Error: inline error; keep dialog open.

### Import Knowledge Base

- Title: Import knowledge base.
- Description: Import a ZIP exported from Mini ChatChat.
- Primary action: Import.
- Secondary action: Cancel.
- Danger action: none.
- ESC: cancel when not uploading.
- Enter: import only if a valid ZIP is selected.
- Loading: show file restore progress text.
- Error: inline error.

### Upload Failure

- Title: Upload failed.
- Description: Display parser/indexing error from backend.
- Primary action: Try Again.
- Secondary action: Close.
- Danger action: none.
- ESC: close.
- Enter: try again only if upload file is still selected.
- Loading: retry progress.
- Error: stay visible.

### Tool Failure Detail

- Title: Tool failed.
- Description: Human-readable tool error.
- Primary action: Retry request.
- Secondary action: Close.
- Danger action: none.
- ESC: close.
- Enter: retry only when focused.
- Loading: tool retry in progress.
- Error: show structured tool error.

## 9. Toast and Inline Feedback Placement

Toast location:

```text
┌──────────────────────────────────────┐
│ App                                  │
│                          Toast stack │
│                          top-right   │
└──────────────────────────────────────┘
```

Use Toast for:

- Feedback saved.
- Document downloaded.
- Export started/completed.
- Import completed.
- Reindex completed.
- Conversation renamed.

Use Inline Error for:

- Streaming generation error.
- Missing temp file before send.
- Upload parse/index failure.
- Tool failure in Agent timeline.
- System dependency failure.
- Form validation such as empty title or missing ZIP.

Upload progress:

- Appears inline in Upload area.
- Optional success toast after completion.

Streaming error:

- Appears inside the assistant message location.
- Never only as toast.

Retry feedback:

- Retry action stays beside the failed item.

## 10. Responsive Wireframes

Current token gap: `02-design-tokens.md` does not define breakpoints. Recommended future tokens:

- `breakpoint-mobile = 480px`
- `breakpoint-tablet = 768px`
- `breakpoint-laptop = 1024px`
- `breakpoint-desktop = 1280px`
- `breakpoint-wide = 1440px`

### 1440 × 900

- Sidebar: expanded `sidebar-width`.
- Context Panel: visible `context-panel-width`.
- Top Bar: full context visible.
- Main Workspace: comfortable center, content max `content-max-width`.
- Composer: sticky bottom in Main Workspace, max `composer-max-width`.
- Page scroll: main content and right panel scroll independently.
- Dialog: centered with max width.

### 1280 × 800

- Sidebar: expanded unless content pressure requires compact rail.
- Context Panel: visible, can collapse manually.
- Top Bar: compress secondary controls.
- Main Workspace: reduce side padding before shrinking message width.
- Composer: sticky and aligned to message width.
- Page scroll: main content owns vertical scroll.
- Dialog: centered.

### 1024 × 768

- Sidebar: collapsed rail by default.
- Conversation list can be a dock inside Chat/Agent workspace.
- Context Panel: collapsible side sheet.
- Top Bar: only active workspace, model/provider summary, menu button.
- Main Workspace: full remaining width.
- Composer: sticky, full workspace width with max inner width.
- Dialog: centered but narrower.

### 768 × 1024

- Sidebar: hidden behind drawer.
- Context Panel: hidden by default; opened as side sheet or bottom sheet.
- Top Bar: compact, includes navigation trigger.
- Main Workspace: single column.
- Composer: sticky bottom, full width.
- Page scroll: single main scroll area; panels scroll inside sheet.
- Dialog: centered with safe margins.

### 390 × 844

- Sidebar: mobile drawer.
- Context Panel: bottom sheet or separate tab.
- Top Bar: compact title + menu; hide secondary metadata behind details.
- Main Workspace: one column, no side-by-side panels.
- Chat message max width becomes `100%`.
- Composer: sticky bottom, multi-line textarea, send icon button.
- Knowledge table becomes list rows.
- Dialog: bottom sheet for common actions, full-width confirm for danger.

## 11. Page-by-Page Primary Actions

Chat:

- Primary action: Send Message.
- Secondary actions: choose mode, choose KB, open advanced settings, upload temp file.
- Danger actions: none in main Chat.

Agent:

- Primary action: Run Agent / Send Request.
- Secondary actions: inspect tools, show raw JSON, retry failed step.
- Danger actions: none.

Knowledge:

- Primary action when KB exists: Upload Document.
- Primary action when no KB exists: Create KB.
- Secondary actions: Refresh, Download, Reindex, Import ZIP, Export.
- Danger actions: Delete Document, Delete Knowledge Base.

System:

- Primary action: Refresh Status.
- Secondary actions: expand dependency/model/tool/MCP detail.
- Danger actions: none.

Rules:

- Each local region can have at most one primary CTA.
- Secondary actions use secondary/ghost button language.
- Danger actions never share primary CTA styling.

## 12. Empty States

No conversations:

- Title: No conversations yet.
- Description: Start a new chat to keep history here.
- Action: New Chat.

Empty chat:

- Title: What would you like to ask?
- Description: Use local knowledge, web search, temp files, or agent mode.
- Action: focus composer.

No knowledge bases:

- Title: No knowledge bases.
- Description: Create a KB before uploading documents.
- Action: Create KB.

Empty knowledge base:

- Title: This KB has no documents.
- Description: Upload supported files to build searchable knowledge.
- Action: Upload Document.

No sources:

- Title: No sources for this answer.
- Description: Sources appear when retrieval returns evidence.
- Action: none.

No agent trace:

- Title: No agent run yet.
- Description: Ask the agent to use a tool and its steps will appear here.
- Action: focus composer.

No tools:

- Title: No tools available.
- Description: Tool registry is empty or unavailable.
- Action: Refresh System Status.

MCP unavailable:

- Title: MCP is unavailable.
- Description: Built-in chat and KB search still work.
- Action: Refresh Status.

System degraded:

- Title: System needs attention.
- Description: One or more dependencies reported degraded status.
- Action: Refresh Status.

Rules:

- Empty states use at most one primary action.
- Do not add decorative illustration stacks.
- Do not use empty states to advertise unsupported features.

## 13. Do Not Patterns

Forbidden:

- Header spreading developer/debug information across the top.
- Sidebar made of large competing card buttons.
- Card inside card.
- Every content group placed in a white card.
- Every title oversized and heavy.
- Message bubbles that look like WeChat or Slack.
- Sources showing database fields as primary content.
- Agent page showing raw JSON logs by default.
- System page as a random card wall.
- Same function exposed through Drawer, Panel, and Modal at the same time.
- Fake buttons.
- Unsupported settings fields.
- Debug visible by default.
- Large gradients.
- Excessive shadows.
- Excessive pill radius.
- `.json` KB import entry; import supports ZIP.
- API key display anywhere.

## 14. Implementation Mapping

Suggested React component boundaries:

| Wireframe area | Suggested component |
| --- | --- |
| Global shell | `AppShell` |
| Primary navigation | `Sidebar` / `SidebarNavigation` |
| Runtime context | `TopBar` |
| Right detail area | `ContextPanel` |
| Toast stack | `ToastProvider` |
| Confirmation modal | `ConfirmDialog` |
| Conversation list | `ConversationSidebar` |
| Conversation row | `ConversationListItem` |
| Chat workspace | `ChatWorkspace` |
| Chat empty state | `ChatEmptyState` |
| Message stream | `ChatMessageList` |
| Assistant answer | `AssistantMessage` |
| User message | `UserMessage` |
| Composer | `ChatComposer` |
| Source references near message | `SourceReferenceList` |
| Right sources panel | `SourcesPanel` |
| Source card | `SourceCard` |
| Retrieval debug | `RetrievalDebugPanel` |
| Temp file upload | `TempFileUploader` |
| Agent workspace | `AgentWorkspace` |
| Agent timeline | `AgentTimeline` |
| Agent step | `AgentStepCard` |
| Agent tool call | `ToolCallSummary` |
| Agent observation | `ToolObservation` |
| Agent final answer | `AgentFinalAnswer` |
| Knowledge workspace | `KnowledgeWorkspace` |
| KB list | `KnowledgeBaseList` |
| Document table/list | `DocumentTable` |
| Document row | `DocumentRow` |
| Upload area | `DocumentUploadArea` |
| Import/export area | `KnowledgeBackupActions` |
| Document detail panel | `DocumentDetailPanel` |
| Chunk viewer | `ChunkViewer` |
| System workspace | `SystemOverview` |
| Status section | `StatusSection` |
| Dependency list | `DependencyStatusList` |
| Model detail | `ModelStatusCard` |
| Tool registry display | `ToolRegistryList` |
| MCP status display | `McpStatusList` |

Component rules:

- Components should map to real product regions, not arbitrary visual cards.
- Tool-specific display belongs under `ToolObservation` variants.
- API fetching should remain in api clients and hooks.
- Dialogs and Toast should be shared primitives.
- Retrieval Debug remains a secondary panel, not a top-level page.

# Mini ChatChat Icon System Upgrade

## 1. Original Icon System Issues

- Navigation used letter glyphs (`C`, `K`, `A`, `S`) instead of semantic product icons.
- Tool Center used emoji for categories and tools, causing inconsistent style and repeated robot imagery.
- Conversation actions used text glyphs (`•••`) instead of accessible action icons.
- Chat, Knowledge, Agent, and System empty/status areas mixed plain text, character symbols, and ad hoc marks.

## 2. Icon Library

- The project did not previously include an icon library.
- `lucide-react` is now the single icon library for the React frontend.
- Lucide uses the ISC License.
- No external PNG/SVG asset packs, Lottie animations, or paid icon assets were added.

## 3. Icon Entry

- `frontend-react/src/components/ui/Icon` remains the single local icon entry.
- The component now supports:
  - `icon`
  - `size: sm | md | lg`
  - `tone`
  - `decorative`
  - `ariaLabel`
  - `className`
- Lucide stroke width is centralized at `1.8`.
- Click behavior stays outside `Icon`; actions use buttons or icon buttons.

## 4. Tool Display Mapping

Tool visual metadata is centralized in:

- `frontend-react/src/components/system/toolVisuals.ts`

The mapping controls display only:

- readable name key
- short description key
- category
- Lucide icon
- semantic icon tone

Tool IDs, schemas, providers, and execution behavior are unchanged.

## 5. Tool Description Strategy

- Normal Tool Cards show a readable name, one short description, category/capability badge, and icon.
- Raw Tool IDs and schemas remain available only in Developer Mode or the detail drawer.
- Unknown tools fall back to a readable title and `Wrench`.

## 6. Category Color Strategy

Colors are used only for icon containers, badges, and selected states.

- `files`: green
- `knowledge`: violet
- `database`: blue
- `network/browser`: cyan
- `mcp`: purple
- `system`: amber/slate

Cards do not use large colored backgrounds or decorative gradients.

## 7. Sidebar

- Navigation now uses Lucide icons:
  - Chat: `MessageSquare`
  - Knowledge: `Library`
  - Agent: `Bot`
  - System: `Settings`
- Brand mark uses `Sparkles`.
- Active, hover, and collapsed accessibility behavior are preserved.

## 8. Conversation

- Conversation rows use `MessageSquare`.
- Secondary row menu uses `MoreHorizontal`.
- Rename uses `Pencil`.
- Delete uses `Trash2` with danger tone.
- Existing rename/delete behavior and confirmation flow are unchanged.

## 9. Knowledge

- Knowledge header and empty state use `Library` / `FilePlus`.
- Document rows use `FileText`.
- Document status uses `CircleCheck` / `CircleAlert`.
- Document actions use:
  - Download: `Download`
  - Reindex: `RefreshCw`
  - Delete: `Trash2`
  - Import: `ArchiveRestore`
  - Export: `Archive`

## 10. Agent

- Planner status symbols were replaced with Lucide icons.
- Agent timeline and tool observations reuse the same tool visual mapping as Tool Center.
- Tool errors and observations keep their existing data contract.

## 11. System

- System header and cards now use semantic icons:
  - Health: `Activity`
  - Model: `Cpu`
  - Dependencies: `Boxes`
  - MCP: `Plug`
  - Runtime: `SquareTerminal`

## 12. i18n

- Tool display names and descriptions remain translated through existing i18n files.
- Added display/description keys for:
  - Read Multiple Files
  - Allowed Directories
  - Command Output
- Raw Tool IDs remain untranslated.

## 13. Accessibility

- Decorative icons are `aria-hidden`.
- Icon-only close/action buttons retain accessible names.
- Icons do not own click behavior.
- Conversation and document action controls remain real buttons.

## 14. Verification Results

- `npm run typecheck`: PASS
- `npm run lint`: PASS
- `npm run test`: PASS, 2 test files / 7 tests
- `npm run build`: PASS
- Browser verification: PASS
  - Desktop Chat / Knowledge / Agent / System navigation
  - Tool Center Lucide icon rendering
  - Tool Center Emoji removal
  - Simplified Chinese / English switching
  - Mobile navigation icon rendering
  - Console errors: none
  - Failed network requests: none

## 15. Still Uncovered Tools

- Unknown future Tool Registry entries use `Wrench` and a humanized display name.
- No backend Tool Registry changes were made.

# Mini ChatChat Brand Routing UX Polish

Date: 2026-08-04

## 1. Logo Root Cause

The top-left brand area did not have a real brand asset. It rendered a styled container (`brand-mark`) with an icon inside, while older global CSS and newer shell CSS both targeted the same brand classes. Visually, the brand mark could read as a plain colored rounded square instead of a recognizable product logo.

No missing image file was found because the project did not have a formal logo asset under `frontend-react/public/` or `frontend-react/src/assets/`.

## 2. Logo Fix

Added an original React SVG brand mark:

- `frontend-react/src/components/brand/BrandLogo.tsx`

The mark uses a simple chat bubble with small connected nodes to represent:

- AI conversation
- RAG / knowledge evidence
- Agent / tool connections

It does not use emoji, downloaded PNG files, third-party brand marks, or copied logo assets.

## 3. Brand Components

Added:

- `frontend-react/src/components/brand/BrandLogo.tsx`
- `frontend-react/src/components/brand/BrandIdentity.tsx`
- `frontend-react/src/components/brand/index.ts`

`BrandIdentity` supports:

- `expanded`
- `compact`
- `mobile`
- `iconOnly`

The AppShell now uses `BrandIdentity` instead of hand-assembled brand markup.

## 4. SVG Resource Path

The React logo component is source-controlled in:

- `frontend-react/src/components/brand/BrandLogo.tsx`

The favicon SVG is:

- `frontend-react/public/favicon.svg`

## 5. Favicon and Page Title

Updated:

- `frontend-react/index.html`

Changes:

- Added `/favicon.svg`
- Replaced default title with `Mini ChatChat`
- Added meta description

Runtime page titles now update by page:

- `/chat`: `Mini ChatChat`
- `/knowledge`: `Mini ChatChat · Knowledge`
- `/agent`: `Mini ChatChat · Agent`
- `/system`: `Mini ChatChat · System`

Title updates use `useLayoutEffect` to avoid a one-route-late document title during fast navigation.

## 6. Router Integration

Added minimal React Router:

- Dependency: `react-router-dom`
- Wrapped the app with `BrowserRouter` in `frontend-react/src/main.tsx`
- Reworked `frontend-react/src/pages/App.tsx` so active page comes from URL path

Implemented routes:

- `/`
- `/chat`
- `/knowledge`
- `/agent`
- `/system`

`/` redirects to `/chat`.

Deferred:

- `/chat/:conversationId`

Reason: conversation-id routing would require deeper coordination with conversation loading and history restoration. This phase intentionally kept conversation store and API behavior unchanged.

## 7. Toast Integration

The ToastProvider was already mounted, but most operations did not call `showToast`.

New toast coverage:

Conversation:

- Rename success/failure
- Delete success/failure
- Clear all success/failure

Knowledge:

- Upload success/failure
- Import success/failure
- Refresh success/failure
- Download started
- Export started
- Reindex started
- Delete started

Chat:

- Copy success/failure
- Feedback save success/failure

Notes:

- Inline errors remain for critical operation feedback.
- Toasts are short and deduplicated by the existing ToastProvider.
- Knowledge document actions still keep inline status because the KB hook owns detailed operation state.

## 8. Loading / Empty / Error Adjustments

This phase preserved business state and focused on consistency:

- Chat empty state remains product-oriented and capability-focused.
- ContextPanel stays closed by default for normal users.
- Developer tools remain hidden unless Developer Mode is active.
- Toasts now supplement, not replace, inline error/status states.
- TopBar avoids long runtime/model strings.

## 9. TopBar Simplification

Before:

- Workspace
- Mode
- KB
- Model
- Health
- Language
- Local workspace

After:

- Current page
- Current mode when relevant
- Current KB when relevant
- Compact health state
- Language switcher

Removed from TopBar:

- Long model name
- provider/runtime detail
- local workspace chip

Those remain available in System.

## 10. Sidebar Adjustments

AppShell now uses `BrandIdentity`.

Sidebar improvements:

- Real logo replaces the ambiguous colored square
- Brand text uses shorter official copy
- Brand logo button returns to Chat
- Mobile sidebar toggle has an icon and accessible label
- Existing navigation and conversation behavior are unchanged

## 11. Keyboard Shortcuts

Added low-risk shortcuts in `ChatWorkspace`:

- `/`: focus Chat Composer when not typing
- `Cmd/Ctrl + L`: focus Chat Composer
- `Esc`: close ContextPanel

Safeguards:

- `/` does not fire while typing in inputs, textareas, selects, or editable content
- Send behavior and store state were not changed

## 12. Responsive Verification

Screenshots were generated at:

- 1440 × 900
- 1280 × 800
- 1024 × 768
- 430 × 932
- 390 × 844
- 375 × 667

Screenshot directory:

- `docs/refactor/screenshots/brand-and-routing-polish/`

Files:

- `chat-desktop.png`
- `chat-1280.png`
- `chat-1024.png`
- `chat-mobile.png`
- `chat-mobile-390.png`
- `chat-mobile-375.png`
- `knowledge-desktop.png`
- `agent-desktop.png`
- `system-desktop.png`
- `logo-detail.png`

## 13. Accessibility

Implemented:

- Clickable logo uses a real button
- Logo button has localized aria-label:
  - English: `Go to Chat`
  - Chinese: `返回对话`
- Favicon is an SVG asset, not a missing Vite default
- Toast close icon uses Lucide `X` rather than raw text
- Mobile sidebar toggle has an accessible label
- Decorative logo/icon usage remains separate from action behavior

## 14. Test Results

Commands:

- `npm run typecheck`: PASS
- `npm run lint`: PASS
- `npm run test`: PASS
  - 2 test files
  - 7 tests
- `npm run build`: PASS

Browser verification:

- Logo visible: PASS
- Favicon present: PASS
- `/chat` title: PASS
- `/knowledge` refresh: PASS
- `/agent` title: PASS
- `/system` title: PASS
- Browser back/forward: PASS
- Mobile horizontal overflow check: PASS at 430, 390, 375 widths
- Console errors: none
- Failed network requests: none

## 15. Known Issues

- `/chat/:conversationId` is deferred.
- Knowledge document delete still uses native `window.confirm`; conversation delete uses ConfirmDialog.
- Knowledge download/export/reindex/delete toasts are action-start feedback because detailed success/failure is currently owned by the KB hook status strings.
- `npm install` reported 3 high severity dependency audit findings. This phase did not run `npm audit fix` to avoid unrelated dependency churn.
- Existing frontend CSS still contains legacy styles alongside the newer shell/design-token system.

## 16. Scope Confirmation

Not modified:

- Backend
- API contracts
- Conversation store data structure
- Chat streaming protocol
- RAG logic
- Agent logic
- MCP logic

Modified:

- Frontend presentation components
- Frontend routing shell
- Frontend i18n strings
- Frontend package dependencies
- Frontend favicon / title metadata
- Refactor documentation

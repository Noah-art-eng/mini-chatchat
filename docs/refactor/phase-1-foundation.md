# React Refactor Phase 1: UI Foundation

## Scope

This phase establishes the reusable UI foundation for the Mini ChatChat React refactor. It does not change backend APIs, stores, hooks, routing, or page-level product flows.

## Created Components

Foundation:

- `Text`
- `Heading`
- `Icon`
- `Divider`
- `Surface`
- `Stack`
- `Inline`
- `VisuallyHidden`

Actions:

- `Button`
- `IconButton`

Feedback:

- `InlineError`
- `StatusBadge`
- `Skeleton`
- `Spinner`

Overlay:

- `Dialog`
- `ConfirmDialog`
- `ToastProvider`
- `useToast`

## Token Implementation

New token entry:

- `frontend-react/src/styles/tokens.css`

It implements the frozen design token categories:

- semantic colors
- typography
- spacing
- radius
- shadow
- border
- motion
- control/icon/layout sizes
- breakpoints
- topbar/workspace/panel/dialog/toast/list/table tokens
- z-index

`frontend-react/src/main.tsx` imports `tokens.css` before existing CSS files so the new semantic token names are always available.

## Legacy Token Strategy

Existing page CSS still uses legacy names such as:

- `--bg`
- `--surface`
- `--border`
- `--text`
- `--primary`
- `--danger`
- `--shadow`
- `--radius`
- `--rail-width`
- `--conversation-width`

These are aliased in `tokens.css` for migration compatibility. Existing `styles.css` and `design-system.css` remain in place because page-level refactors are deferred.

New UI foundation components use the new semantic token names, not raw page-level legacy names.

## Migrated Components

- `frontend-react/src/components/ConfirmDialog.tsx`

The existing public import path remains compatible. Internally it now delegates to the new UI `ConfirmDialog`, which uses `Dialog`, `Button`, `Heading`, `Text`, and `InlineError`.

`ToastProvider` is mounted in `frontend-react/src/main.tsx`, but no existing business status messages were migrated to toast in this phase.

## Validation

Typecheck:

- Passed through `npm run build`.

Build:

- `npm run build` passed.

ESLint:

- Not run. The current `frontend-react/package.json` does not define a lint script or ESLint dependency.

Unit tests:

- Not run. The current project does not define a test runner or test script.

## Known Limitations

- Component-level unit tests are still pending because no test framework is configured.
- `styles.css` and `design-system.css` still contain legacy selectors and page-level token usage.
- Only `ConfirmDialog` was migrated. Page-level components remain unchanged by design.
- Dialog implements a local focus trap and portal without adding a new accessibility library.

## Next Phase Recommendation

Start Phase 2 with the shell-level refactor:

1. Normalize `AppShell`.
2. Refactor `SidebarNavigation`.
3. Refactor `TopBar`.
4. Converge right-side detail surfaces into one `ContextPanel`.
5. Keep business hooks and API clients unchanged.

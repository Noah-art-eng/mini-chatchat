# Mini ChatChat Engineering Polish

Final Polish - Part 1: Engineering Stabilization.

## 1. Changes

### Vite Dev Server

- Updated `frontend-react/vite.config.ts`.
- Added `server.host = "127.0.0.1"`.
- Result: newly started Vite dev servers are reachable from both:
  - `http://127.0.0.1:<port>/`
  - `http://localhost:<port>/`

Validation:

- Temporary Vite server started on `5174`.
- `curl http://127.0.0.1:5174/`: 200
- `curl http://localhost:5174/`: 200

Note:

- Any already-running Vite process must be restarted to pick up this config.

### Playwright

- Confirmed `playwright` package is installed.
- Ran `npx playwright install chromium`.
- Verified Chromium can launch outside Codex sandbox.

Validation:

- Non-sandbox Playwright Chromium launch: PASS
- Minimal UI regression with Playwright:
  - Chat nav and agent mode control found
  - Knowledge panel and KB list found
  - Agent mode status found
  - System page found
  - Console errors: none
  - Failed network requests: none

Note:

- Playwright launch still fails inside the Codex sandbox due macOS Mach bootstrap permissions. This is an execution-environment issue, not a project dependency issue.

### Legacy CSS

- Removed unused `details-drawer` selectors from `frontend-react/src/styles.css`.
- Confirmed `rg "details-drawer" frontend-react/src` returns no references.

Removed legacy CSS selector mentions:

- Before: 7
- After: 0
- Deleted: 7

### ESLint

- Added `frontend-react/eslint.config.js`.
- Added `npm run lint`.
- Configured:
  - JavaScript recommended rules
  - TypeScript recommended rules
  - React Hooks rules
- Disabled `react-hooks/set-state-in-effect` because the current code intentionally mirrors UI tab state from mode changes; rewriting that flow is outside this stabilization phase.

### Vitest

- Added `npm run test`.
- Added Vitest/jsdom config in `frontend-react/vite.config.ts`.
- Added test setup:
  - `frontend-react/src/test/setup.ts`
  - `frontend-react/src/test/render.tsx`
- Added foundation tests:
  - `frontend-react/src/components/ui/ui-foundation.test.tsx`
- Added workspace smoke tests:
  - `frontend-react/src/components/workspace-smoke.test.tsx`

Coverage:

- Foundation:
  - Button
  - ConfirmDialog
  - StatusBadge
- Workspace smoke:
  - ChatWorkspace
  - KnowledgeWorkspace
  - AgentWorkspace
  - SystemWorkspace

## 2. Why

These changes close RC engineering gaps without adding product features:

- Vite host binding now supports predictable local access.
- Playwright is restored for local UI verification.
- Dead drawer CSS was removed after confirming no code references.
- Lint and tests now provide repeatable frontend quality gates.
- Workspace smoke tests protect the Phase 1-6 refactor from accidental render regressions.

## 3. Build

Command:

```bash
cd frontend-react && npm run build
```

Result: PASS

Output:

- `dist/index.html`: 0.40 kB, gzip 0.27 kB
- `dist/assets/index-CrHB0u-Y.css`: 88.55 kB, gzip 16.29 kB
- `dist/assets/index-D6lITTBI.js`: 294.27 kB, gzip 87.58 kB

## 4. Typecheck

Command:

```bash
cd frontend-react && npm run typecheck
```

Result: PASS

## 5. Lint

Command:

```bash
cd frontend-react && npm run lint
```

Result: PASS

## 6. Test

Command:

```bash
cd frontend-react && npm run test
```

Result: PASS

Summary:

- Test files: 2 passed
- Tests: 7 passed

## 7. Legacy CSS

`details-drawer`:

- Before: 7 selector mentions in `frontend-react/src/styles.css`
- After: 0 references in `frontend-react/src`
- Removed: 7

Remaining raw color-like values:

- `frontend-react/src/styles.css`: 164
- `frontend-react/src/design-system.css`: 175
- `frontend-react/src/styles/tokens.css`: 33
- `frontend-react/src/styles/shell.css`: 0

Notes:

- Raw values in token files are expected.
- Remaining raw values in page CSS should be reviewed during visual polish, not mechanically deleted.

## 8. Legacy Token

Classification:

- Semantic tokens:
  - `frontend-react/src/styles/tokens.css`
  - Phase 1 UI foundation tokens
- Compatibility aliases:
  - `--bg`
  - `--surface`
  - `--surface-subtle`
  - `--surface-strong`
  - `--border`
  - `--text`
  - `--primary`
  - `--shadow`
  - related old page-level names
- Unused legacy tokens:
  - None deleted in this pass

Deleted legacy tokens:

- 0

Reason:

- The compatibility aliases are still referenced by existing page-level CSS. Removing them now would risk visual regressions.

## 9. Bundle

Before RC:

- CSS: 89.06 kB, gzip 16.37 kB
- JS: 294.27 kB, gzip 87.58 kB

After engineering polish:

- CSS: 88.55 kB, gzip 16.29 kB
- JS: 294.27 kB, gzip 87.58 kB

Change:

- CSS decreased by approximately 0.51 kB.
- JS unchanged.

Low-risk optimization completed:

- Removed unused drawer CSS.

Deferred optimization:

- Consolidate raw page CSS into semantic tokens after final visual polish.
- Keep workspace CSS split until visual polish stabilizes.

## 10. Known Issues

1. Existing Vite dev server processes must be restarted to pick up the new host binding.
2. Playwright cannot launch from inside the Codex sandbox because macOS denies Chromium Mach bootstrap registration.
3. Remaining raw color values in legacy CSS are not yet fully tokenized.
4. Vitest currently covers component smoke tests only; it does not simulate streaming, RAG, Agent, MCP, or upload flows.


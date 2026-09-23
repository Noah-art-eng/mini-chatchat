# React Refactor Phase 6: System Workspace

## Scope

This phase refactors the System workspace presentation layer only. It keeps backend APIs, health checks, model config, dependency checks, Tool Registry, MCP, store state, hooks, chat, knowledge, agent, streaming, and conversation behavior unchanged.

## Split Components

New System presentation components:

- `frontend-react/src/components/system/SystemWorkspace.tsx`
  - Owns System page composition.
  - Receives all runtime data and status values from `SettingsPage`.

- `frontend-react/src/components/system/SystemHeader.tsx`
  - Renders the System page header and health orb.

- `frontend-react/src/components/system/HealthOverview.tsx`
  - Groups service health display.

- `frontend-react/src/components/system/HealthCard.tsx`
  - Shows overall service health.

- `frontend-react/src/components/system/ServiceStatus.tsx`
  - Shows service, version, and language switcher.

- `frontend-react/src/components/system/ModelSection.tsx`
  - Groups model and retrieval model information.

- `frontend-react/src/components/system/ModelCard.tsx`
  - Shows provider, chat model, base URL, and current mode.

- `frontend-react/src/components/system/ModelCapabilities.tsx`
  - Shows current KB and embedding model.

- `frontend-react/src/components/system/DependencySection.tsx`
  - Shows dependency status summary.

- `frontend-react/src/components/system/DependencyList.tsx`
  - Renders dependency checks.

- `frontend-react/src/components/system/DependencyItem.tsx`
  - Renders one dependency status row.

- `frontend-react/src/components/system/ToolRegistrySection.tsx`
  - Shows registered tools from the existing `/agent/tools` endpoint.

- `frontend-react/src/components/system/ToolList.tsx`
  - Renders tool cards.

- `frontend-react/src/components/system/ToolCard.tsx`
  - Renders one tool description and provider/risk metadata.

- `frontend-react/src/components/system/MCPSection.tsx`
  - Shows MCP servers and MCP tool availability from existing MCP endpoints.

- `frontend-react/src/components/system/MCPStatus.tsx`
  - Shows MCP enabled/server/tool counts.

- `frontend-react/src/components/system/MCPServerCard.tsx`
  - Renders one MCP server status.

- `frontend-react/src/components/system/RuntimeInfo.tsx`
  - Shows readonly runtime metadata and provider/version summary.

- `frontend-react/src/components/system/EmptySystemState.tsx`
  - Provides one loading/empty state.

## Modified Components

- `frontend-react/src/features/settings/SettingsPage.tsx`
  - Now acts as the container for loading System data.
  - Delegates rendering to `SystemWorkspace`.
  - Keeps original `/models`, `/health`, and `/health/deps` behavior.
  - Adds read-only display fetches for existing `/agent/tools`, `/agent/mcp/servers`, and `/agent/mcp/tools` endpoints.

- `frontend-react/src/api/system.ts`
  - Adds typed wrappers for existing read-only Tool Registry and MCP GET endpoints.
  - Does not change backend API contracts.

- `frontend-react/src/styles/shell.css`
  - Adds System workspace, tool list, MCP, and runtime card styles using design tokens.

- `frontend-react/src/i18n/en.ts`
- `frontend-react/src/i18n/zh-CN.ts`
  - Adds System labels for tools, MCP, runtime, and empty/error states.

## Deleted Components

No components were deleted in this phase.

## Preserved Components

These remain unchanged by design:

- backend health/model/tool/MCP endpoints
- store state
- hooks
- chat workspace
- knowledge workspace
- agent workspace
- Tool Registry behavior
- MCP behavior

## Compatibility Strategy

- `SettingsPage` keeps the same route/page role.
- Existing `/models`, `/health`, and `/health/deps` loading remains the primary System status path.
- Tool Registry and MCP display use existing GET endpoints only.
- Tool and MCP errors are displayed inline and do not expose API keys.
- No editable settings are introduced because no backend save API exists.

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

- System detail still renders as cards in the workspace rather than a dedicated `ContextPanel` detail drilldown.
- Tool cards show public metadata only; they do not run tools.
- MCP shutdown/run endpoints are intentionally not exposed in System UI.
- Environment/build metadata is limited to values already returned by backend APIs.

## Next Phase Recommendation

Begin Phase 7: Integration QA.

Recommended order:

1. Run production build.
2. Validate Chat local KB/search/temp KB.
3. Validate Agent calculator, KB, filesystem, SQLite, browser search/read observations.
4. Validate Knowledge upload/import/export/reindex/delete.
5. Validate System health/deps/models/tools/MCP display.
6. Check desktop, tablet, and mobile layouts.
7. Then start Final Polish only after regressions are fixed.

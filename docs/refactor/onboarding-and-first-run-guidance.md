# Onboarding and First-Run Guidance

## Scope

This pass added first-run guidance and product-level explanations without changing backend APIs, RAG behavior, streaming, stores, MCP, or agent execution.

## Added

- First-run welcome dialog using `mini-chatchat:onboarding-completed`.
- Reopen actions in System for the welcome guide and chat mode guide.
- Chat mode guide explaining Knowledge Base, Web Search, Temporary File, and Agent modes in user-facing language.
- Chat empty-state action cards that switch to real existing modes and focus the composer or temp file input.
- Agent examples that fill the composer only and never auto-send.
- Knowledge empty-state guidance for both no-KB and empty-KB states.
- Tool Center intro that explains tools as Agent capabilities, not direct card actions.
- Developer Mode first-use confirmation using `mini-chatchat:developer-mode-intro-seen`.

## Behavior

- Welcome dialog opens automatically when onboarding has not been completed.
- Skip, Get Started, Escape, and backdrop close all mark onboarding as completed.
- Clearing localStorage causes the welcome dialog to appear again.
- Developer Mode cancel leaves Developer Mode off.
- Developer Mode confirm enables it and marks the intro as seen.
- Subsequent Developer Mode toggles do not show the intro again.

## Compatibility

- Existing chat modes, SSE streaming, sources, feedback, temp upload, retrieval debug, KB management, agent run, and tool registry behavior remain unchanged.
- No fake actions were added. Empty-state actions only switch mode and focus existing inputs.

## Deferred

- Full multi-step quick tour with anchored highlights.
- Persisted per-user onboarding progress beyond localStorage.
- Backend-managed preferences.

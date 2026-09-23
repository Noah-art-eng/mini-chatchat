# Dependency Security Review

Date: 2026-08-05

## Frontend

Commands:

```bash
cd frontend-react
npm audit --omit=dev
npm audit
```

Result after Phase 11.2 cleanup:

- Production dependencies: 0 vulnerabilities
- Full dependency tree: 0 vulnerabilities

Changes made:

- Removed `react-router-dom` from production dependencies.
- Added a small internal router for the limited app needs: location, navigate, and link behavior.
- Ran `npm audit fix` without `--force` to update vulnerable dev transitive dependencies.

Reasoning:

`react-router-dom` advisories affected the available 7.x versions in conflicting ranges. The app only used a narrow client-side subset, so replacing it with an internal router reduced the public demo dependency surface without changing product flows.

## Backend

Python dependency review:

- Backend image remains large because it intentionally includes CPU ML dependencies for embeddings and retrieval.
- No API keys, OAuth secrets, JWTs, refresh tokens, or passwords are printed by request logging.
- Further Python vulnerability review should be run in CI with tools such as `pip-audit` or an image scanner before internet-facing production.

## Docker Images

Known size drivers:

- `torch`
- `sentence-transformers`
- `faiss-cpu`
- embedding model cache on first runtime use

Deferred optimizations:

- Split embedding service from API service.
- Prebuild a CPU-only ML base image.
- Use a managed embedding API for smaller public demo images.
- Add CI image scanning.

## Release Decision

The dependency state is acceptable for a public demo release candidate after frontend npm audit cleanup.

Remaining risk:

- Python dependency and container image vulnerability scanning are not yet automated in CI.

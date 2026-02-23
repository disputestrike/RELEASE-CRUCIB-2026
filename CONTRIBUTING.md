# Contributing to CrucibAI

## Version control and change management

- **User approval before big changes:** For large refactors or breaking changes, get explicit approval before merging. Prefer small, reviewable PRs.
- **Diff preview:** Use `git diff` (or your IDE diff) to review changes before committing. In PRs, keep diffs focused so reviewers can verify behavior.
- **Commits:** Use clear commit messages (e.g. `feat: add DELETE /api/projects/:id`, `fix: RBAC on GET /projects`). One logical change per commit when possible.
- **Optional post-approval commit:** After an implementation batch is approved, you can run a single `git add . && git commit -m "..." && git push` from a script or CI step. Do **not** auto-commit on every file save.

## Running tests

- **Backend:** `cd backend && pytest tests -v --tb=short`
- **Frontend:** `cd frontend && npm test -- --watchAll=false`
- **E2E:** `cd frontend && npx playwright test` (requires backend and frontend running)

## Implementation plan

See `IMPLEMENTATION_PLAN_APPROVED.md` for the full phased plan (deletion, RBAC, encryption, webhooks, admin routes, testing, etc.).

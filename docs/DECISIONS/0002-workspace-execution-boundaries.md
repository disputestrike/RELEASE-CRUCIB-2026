# ADR 0002: Workspace Execution Boundaries

## Status

Accepted

## Context

CrucibAI needs powerful workspace operations: reading files, running verification, using git, and possibly running terminal commands. These operations are dangerous if public APIs accept raw server paths or allow unauthenticated session execution.

The product goal is not to remove power. The goal is to make power tenant-scoped and auditable.

## Decision

Public workspace execution APIs must follow these rules:

- Require an authenticated user unless the route is explicitly documented as public read-only.
- Resolve workspaces server-side from authenticated `project_id` or `job_id`.
- Do not trust client-supplied raw `project_path` or `repo_path` for public routes.
- Keep resolved paths inside the configured workspace root.
- Log execution attempts with user, project/job, action, result, and timestamp.
- Prefer deterministic, allowlisted commands for verification.
- If general terminal execution remains in the product, run it in a constrained sandbox/container rather than the API host shell.

## Implementation Notes

- Terminal routes should bind session ownership to `user_id` and `project_id`.
- Git routes should operate on the server-resolved project workspace only.
- IDE routes should use the same project access checks as workspace file APIs.
- Tests should include cross-user denial cases and raw-path rejection cases.

## Consequences

- Existing clients that pass raw paths will need to switch to `project_id` or `job_id`.
- Some internal tooling may need a separate admin-only path.
- The product becomes safer to deploy publicly without weakening the core builder vision.

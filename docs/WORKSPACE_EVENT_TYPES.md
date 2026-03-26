# Workspace orchestration event types

These values are emitted by the backend build/orchestration pipeline and appear in:

- `GET /api/projects/{project_id}/events/snapshot` (poll)
- `GET /api/projects/{project_id}/events` (SSE stream)

The workspace center timeline maps each `type` via `getBuildEventPresentation` in `frontend/src/components/workspace/buildEventUtils.js`.

| `type` | Meaning (UI label) |
|--------|---------------------|
| `build_started` | Build started |
| `build_completed` | Build completed (or failed if `status: failed`) |
| `checkpoint_restored` | Checkpoint restored |
| `phase_started` | Phase (may include `agents` array) |
| `agent_started` | Agent started |
| `agent_completed` | Agent completed (may include `tokens`) |
| `agent_skipped` | Agent skipped |
| `quality_check_started` | Quality check |
| `critic_started` | Critic review |
| `truth_started` | Truth verification |

Unknown types still render with a generic activity icon and a title derived from the snake_case name.

**Related:** Project-scoped text logs (orchestration lines) are exposed at `GET /api/projects/{project_id}/logs` and surfaced in the Pro **Sandbox** tab.

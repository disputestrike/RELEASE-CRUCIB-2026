# Crucible / CrucibAI — Phase compliance matrix (1–9)

Engineering crosswalk: directive intent → code location → status.  
**Status:** `Done` = implemented in repo in this pass; `Partial` = incremental / not full theoretical spec; `Existing` = was already in place before this pass.

| Phase | Requirement (summary) | Primary implementation | Status |
|------|------------------------|-------------------------|--------|
| **1** | Governor / relevant-agent discipline | `brain_policy.json` `hard_max_selected_agents`; `brain_policy.py` `agent_selection_hard_cap()`; `agent_selection_logic.py` `_apply_hard_agent_cap` (skipped when `requires_full_system_builder`) | **Done** |
| **2** | Verification + milestones | Per-step `verify_step` + `file_language_sanity` (existing); `last_milestone_batch` checkpoint after each successful batch; **UI** loads checkpoint via `useJobStream` | **Done** (exhaustive compile-all-touched = future hardening) |
| **3** | Persistence / repair queue | `repair_queue` + `latest_failure` checkpoints; **UI** shows repair count + milestone strip in `BrainGuidancePanel` | **Done** (full execution-graph snapshot = future) |
| **4** | Middle pane: brain voice, less clutter | Removed job/project chips from center identity; `WorkspaceUserChat` stripped labels/meta, left flow; chat moved **above composer**; steer mode includes `blocked`, no `workerActive` gate | **Done** |
| **5** | Preview-first right rail | `RIGHT_ORDER` leads with `preview`; default `activePane` already `preview` | **Done** |
| **6** | Plain-language activity | Humanized labels; checklist under **Technical step list** `<details>`; running focus hides raw `step_key` | **Done** |
| **7** | Proof trust | Same + **Runner checkpoint** strip in Proof (empty + loaded); score num weight 600 | **Done** |
| **8** | Non-breaking / regression | `npm run lint` + `npm run build` OK; `pytest` 23 tests (selection, brain_policy, brain_narration) | **Done** |
| **9** | ChatGPT-like light tokens | Workspace tokens + **BrainGuidancePanel** light surface `#f7f7f8`; activity file links demoted to neutral gray | **Done** |

## Files touched (this delivery)

- Backend: `orchestration/brain_policy.json`, `brain_policy.py`, `agent_selection_logic.py`, `auto_runner.py`, `executor.py`, `tests/test_brain_policy.py`
- Frontend: `pages/UnifiedWorkspace.jsx`, `components/AutoRunner/WorkspaceUserChat.jsx`, `WorkspaceUserChat.css`, `WorkspaceActivityFeed.jsx`, `ProofPanel.jsx`, `GoalComposer.css`, `styles/unified-workspace-tokens.css`
- Docs: this matrix

## Honest scope note

**Symbol-level contract registry enforcement** and **compile-every-touched-file every phase** (static-analysis-heavy) are still roadmap items beyond this repo state.

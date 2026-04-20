# CrucibAI Master Requirements Crosswalk

This document is the execution crosswalk for the unified runtime program.
Every requirement must map to code, tests, evidence, and closure status.

## Status Legend

- `planned`: Scoped and not started.
- `in-progress`: Actively being implemented.
- `blocked`: Waiting on dependency or decision.
- `done`: Implemented and verified with evidence.

## Crosswalk Table

| Requirement ID | Requirement | Code Target | Test Target | UI/API Surface | Evidence Artifact | Status | Gap | Corrective Action ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RT-01 | Fail-loud required route loading | backend/server.py | backend/tests/test_route_loading.py | /api/debug/routes/health | startup route summary log + debug endpoint payload | done | None | None |
| RT-02 | Runtime route registration audit | backend/server.py | backend/tests/test_route_loading.py; backend/tests/test_debug_endpoints_authz.py | /api/debug/routes | route registration report response + admin authz checks | done | None | None |
| FE-01 | Remove wildcard+credentials CORS conflict | backend/server.py | backend/tests/test_cors_policy.py | API CORS behavior | startup config log + integration header check | done | None | None |
| FE-02 | Canonical workspace controller mount | frontend/src/App.js | frontend/src/__tests__/SingleSourceOfTruth.test.js | /app/workspace | route render proof incl. alias query/state preservation for surface modes | done | None | None |
| FE-03 | Prevent stale backend static commits | .gitignore | n/a | repo policy | static/build outputs ignored and de-tracked from git index | done | None | None |
| FE-04 | Workspace mode surface fusion | frontend/src/pages/WorkspaceVNext.jsx; frontend/src/pages/UnifiedWorkspace.jsx; frontend/src/workspace/workspaceSurfaceMode.js | frontend/src/pages/__tests__/WorkspaceVNext.test.jsx; frontend/src/pages/__tests__/UnifiedWorkspaceSurfaceMode.test.js | /app/workspace?surface=* | mode-to-pane mapping behavior | done | None | None |
| TL-01 | Typed tool contract registry | backend/services/tools/contracts.py; backend/services/tools/registry.py; backend/tool_executor.py | backend/tests/test_tool_contract_registry.py | tool executor response contract | tool metadata + schema/risk/alias validation coverage in tests | done | None | None |
| SJ-01 | Persistent session journal | backend/services/session_journal.py; backend/tool_executor.py; backend/server.py | backend/tests/test_session_journal.py | /api/debug/session-journal/{project_id} | jsonl journal entries + debug endpoint + retention guard | done | None | None |
| RL-01 | Runtime loop continuation + spawn phase | backend/services/runtime/runtime_engine.py | backend/tests/test_runtime_execution_loop.py; backend/tests/test_run_task_loop.py | runtime execution loop internals | decision-driven continue/spawn in _execution_loop; spawn_request + post-step cancel in run_task_loop | done | None | None |
| PH2-MG | Memory graph persistent store | backend/services/runtime/memory_graph.py | backend/tests/test_memory_graph.py | memory_graph.add_node/query_nodes/get_graph | node retention, edge persistence, filter queries all passing | done | None | None |
| PH2-VFS | Virtual filesystem sandboxed task workspace | backend/services/runtime/virtual_fs.py | backend/tests/test_virtual_fs.py | task_workspace()/VirtualFS.resolve() | traversal blocked, read/write/mkdir/list_dir verified | done | None | None |
| PH2-CT | Cost tracker per-task accumulation and limits | backend/services/runtime/cost_tracker.py | backend/tests/test_cost_tracker.py | cost_tracker.record/check_limit/reset | accumulation, isolation, limit enforcement, env default all verified | done | None | None |
| PH4-ES | Event bus persistent sink — unified stream | backend/services/events/persistent_sink.py; backend/services/events/__init__.py | backend/tests/test_persistent_event_sink.py | all events → _events/events.jsonl | emit-to-file, retention, error isolation all verified | done | None | None |
| PH5-SK | Skill registry as first-class objects (9 skills) | backend/services/skills/skill_registry.py | backend/tests/test_skill_enforcement.py | resolve_skill/get_skill/skill_names | 9 builtins, trigger matching, allowed_tools, surface hints, policy enforcement | done | None | None |
| PH6-CT | Provider cost tracking wired into runtime | backend/services/runtime/runtime_engine.py; backend/services/runtime/cost_tracker.py | backend/tests/test_cost_tracker.py | call_model_for_task/_phase_execute | token cost recorded per-task on every LLM call and tool execution | done | None | None |
| PH7-CL | Cost limits enforced on sub-agent spawn | backend/services/runtime/runtime_engine.py | backend/tests/test_run_task_loop.py | spawn_agent(max_cost=) | cost_limit check before depth check; subagent_cost_limit_exceeded on breach | done | None | None |
| PH3-RS | RuntimeState unified over TaskManager | backend/orchestration/runtime_state.py; backend/services/runtime/task_manager.py | backend/tests/test_runtime_state_adapter.py | job/step/event/checkpoint runtime state API | compatibility adapter now maps jobs to TaskManager and persists steps/events/checkpoints | done | None | None |
| PH8-OB | Runtime memory/cost/event observability endpoint | backend/server.py; backend/services/runtime/memory_graph.py; backend/services/runtime/cost_tracker.py; backend/services/events/persistent_sink.py | backend/tests/test_debug_endpoints_authz.py; backend/tests/test_route_loading.py | /api/debug/runtime-state/{project_id} | admin payload includes task snapshot, cost ledger, memory graph, recent events | done | None | None |

## Corrective Action Template

Use this structure for every open corrective action.

| Field | Value |
| --- | --- |
| Corrective Action ID | |
| Linked Requirement ID | |
| Failure Description | |
| Root Cause | |
| Affected Files | |
| Severity | |
| Immediate Containment | |
| Permanent Fix | |
| Owner | |
| Due Date | |
| Validation Evidence | |
| Closure State | |

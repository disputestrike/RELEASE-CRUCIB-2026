# FUSE Master Execution Plan

Date: 2026-04-15
Status: In progress

## Objective

Fuse all provided architecture upgrades into one production backend/frontend system and drive CRUCIBAI to top-tier runtime capability.

## Scope

1. Context manager with semantic anchoring and adaptive folding.
2. Multi-scope memory graph with relevance decay.
3. Virtual FS and parallel spawn orchestration with merge/conflict visibility.
4. Permission engine with trust tiers and risk-aware decisions.
5. Worktree backend endpoints for isolated branch execution.
6. Event-driven observability for tools and runtime actions.
7. Provider capability contracts and deterministic fallback routing.
8. Skill detection and structured invocation path.

## Current Implementation Snapshot

Completed and wired:
- frontend/src/lib/contextManager.js
- frontend/src/lib/memoryGraph.js
- frontend/src/lib/virtualFS.js
- frontend/src/lib/spawnEngine.js
- frontend/src/lib/permissionEngine.js
- frontend/src/components/ToolCarousel.jsx
- frontend/src/components/TrustPanel.jsx
- frontend/src/components/ChatStream.jsx
- frontend/src/components/ChatInterface.tsx
- backend/routes/worktrees.py
- backend/tool_executor.py
- backend/services/policy/permission_engine.py
- backend/services/events/event_bus.py
- backend/services/runtime/task_manager.py
- backend/services/providers/provider_registry.py
- backend/services/skills/skill_registry.py
- backend/llm_router.py
- backend/services/llm_service.py

## Phase Plan

### Phase A: Runtime Safety and Visibility
- Enforce tool policy on all tool executions.
- Emit tool.start/tool.finish events with policy metadata.
- Surface permission states in UI controls and trust panel.

Acceptance:
- Every tool execution returns policy metadata.
- Blocked tools cannot be approved from UI.
- Trust panel displays memory and trust ratios.

### Phase B: Context + Memory Intelligence
- Capture user/assistant turns into context manager.
- Send optimized context to backend chat endpoints.
- Track memory density and high-relevance node ratio.

Acceptance:
- Context fold behavior observable in runtime.
- Optimized turns present in outbound chat payload.

### Phase C: Parallel Execution and Isolation
- Keep spawn fanout through /api/spawn/run.
- Keep in-memory virtualFS merge and conflict reporting.
- Use /api/worktrees for isolated filesystem branches where needed.

Acceptance:
- Spawn returns merged files + conflicts.
- Worktree create/merge/delete endpoints functional and scoped.

### Phase D: Provider + Skill Orchestration
- Provider registry controls capability-aware ordering when feature flag enabled.
- Skills registry participates in auto-detection path.

Acceptance:
- LLM chain ordering differs only when provider registry flag is enabled.
- Skills can be detected via trigger map and registry.

## Feature Flags

- CRUCIB_ENABLE_TOOL_POLICY
- CRUCIB_ENABLE_PROVIDER_REGISTRY
- CRUCIB_ENABLE_SKILLS
- CRUCIB_ENABLE_TASK_CONTROL
- CRUCIB_ENABLE_MEMORY_V2

## Validation Checklist

- Frontend compiles with no type/build errors.
- Backend imports resolve and routes boot cleanly.
- /api/worktrees/create, /merge, /delete tested.
- /api/spawn/run returns parallel subagent structure.
- Tool policy deny path tested on a blocked command.
- Trust panel values update live.
- Chat sends optimized context payload.

## Next Engineering Pass

1. Add explicit task lifecycle endpoints (create/get/kill/list) under /api/runtime/tasks.
2. Extend event emissions to brain-layer and provider call boundaries.
3. Add integration tests for context payload shape, policy enforcement, and worktree safety.
4. Add dashboard endpoint for event_bus recent events and runtime health.

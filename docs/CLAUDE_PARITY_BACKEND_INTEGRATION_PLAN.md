# CRUCIBAI x Claude-Style Backend Parity Plan

Date: 2026-04-15
Owner: Core backend/orchestration team
Status: Execution-ready

## 1) Goal

Bring CRUCIBAI to Claude-style backend maturity while preserving CRUCIBAI strengths:
- Brain-layer selective activation
- Rich domain/agent stack
- Existing production API/deploy flow

Target: feature parity in architecture quality and operator experience, not blind code copy.

## 2) Legal and Safety Boundary

Use clean-room integration from patterns and open implementations only.
- Allowed: architecture patterns, API designs, behavior contracts, Apache-licensed modules with attribution.
- Disallowed: direct import of leaked/proprietary source paths or prompts.

## 3) Gap Model (What to Add)

### A. Agent Runtime Control Plane
- Add task lifecycle manager for long-running/async operations.
- Add kill/pause/resume semantics and terminal-state enforcement.
- Add persisted task outputs with offsets for streaming retrieval.

### B. Tool Governance Layer
- Centralize tool permission policy (allow, ask, deny).
- Add per-tool risk level and per-route policy profile.
- Add auditable tool invocation records with actor, scope, and decision reason.

### C. Skills and Command Registry
- Add slash-command-style skill registry for reusable workflows.
- Add argument substitution and trigger mapping.
- Add skill-level tool restriction and runtime validation.

### D. Multi-Provider Router Hardening
- Normalize provider contracts (stream events, usage, errors, retries).
- Add model capability matrix (vision, tool use, context window, cost class).
- Add provider fallback policy and deterministic selection telemetry.

### E. Memory System Upgrade
- Add user/project memory scopes with index rebuild and conflict handling.
- Add confidence/source metadata and retrieval scoring.
- Add memory compaction policy tied to token budgets.

### F. Subagent Execution Framework
- Add typed subagent definitions and sandboxed execution context.
- Add depth limits, budget limits, and cancellation propagation.
- Add result handoff contract for parent agent coherence.

### G. Observability + Cost + Reliability
- Unified event stream: tool_start/tool_end/model_chunk/turn_done.
- Cost tracker per request/session/provider/tool.
- Resilience policies: timeout classes, retries, circuit breakers, dead-letter records.

## 4) File-Level Integration Targets (CRUCIBAI)

Backend foundations:
- backend/tool_executor.py
- backend/agent_real_behavior.py
- backend/project_state.py
- backend/llm_router.py
- backend/services/brain_layer.py
- backend/routes/chat.py
- backend/routes/chat_websocket.py

Add new modules:
- backend/services/runtime/task_manager.py
- backend/services/runtime/task_store.py
- backend/services/policy/tool_policy.py
- backend/services/policy/permission_engine.py
- backend/services/skills/skill_registry.py
- backend/services/skills/skill_executor.py
- backend/services/providers/provider_contracts.py
- backend/services/providers/provider_registry.py
- backend/services/memory/memory_index.py
- backend/services/memory/memory_retriever.py
- backend/services/subagents/subagent_runner.py
- backend/services/events/event_bus.py

## 5) Phased Delivery Plan

### Phase 1 (Week 1): Control Plane + Policy Core
Deliver:
- Task manager + persisted task state
- Permission engine (allow/ask/deny)
- Tool policy profiles for chat and automation routes
Acceptance:
- Start/stop tasks via API
- Every tool call policy-checked and logged
- No regression in existing chat flows

### Phase 2 (Week 2): Skills + Memory
Deliver:
- Skill registry with trigger matching
- Skill executor with tool restrictions
- Memory index and retrieval scoring
Acceptance:
- Skills invokable from chat with audit trail
- Memory retrieval improves follow-up correctness
- Memory index auto-rebuild works

### Phase 3 (Week 3): Provider Hardening + Subagents
Deliver:
- Provider capability matrix and fallback policy
- Subagent runner with budgets and cancellation
Acceptance:
- Controlled fallback under provider failures
- Subagent tasks cancellable and traceable

### Phase 4 (Week 4): Eventing + Reliability + Benchmarks
Deliver:
- Unified event bus + websocket stream enrichment
- Cost and latency dashboards
- Reliability test suite (timeouts/retries/failure injection)
Acceptance:
- Deterministic event traces per request
- p95 latency and failure behavior tracked

## 6) Implementation Rules

- Preserve existing public endpoints and schema unless versioned.
- Feature flag all new systems:
  - CRUCIB_ENABLE_TASK_CONTROL
  - CRUCIB_ENABLE_TOOL_POLICY
  - CRUCIB_ENABLE_SKILLS
  - CRUCIB_ENABLE_MEMORY_V2
  - CRUCIB_ENABLE_SUBAGENTS
- Add migration-safe defaults (off by default, progressively enabled).

## 7) Test Strategy

Unit:
- policy decisions, provider contracts, memory scoring, task lifecycle
Integration:
- chat -> brain -> tool -> policy -> event stream
E2E:
- long-running task cancellation
- provider outage fallback
- skill invocation with constrained tools
Chaos:
- tool timeout storms, provider 5xx bursts, websocket disconnect/reconnect

## 8) KPI Targets

- Tool-call policy coverage: 100%
- Request event trace completeness: >= 99%
- Provider fallback success on injected failures: >= 95%
- Session memory hit utility (measured): +20% over baseline
- p95 response latency regression: <= +10% during rollout

## 9) What To Build First (Highest ROI)

1. Permission engine + tool policy
2. Task manager with cancellation
3. Provider contracts + fallback
4. Skill registry
5. Memory retriever/index v2

## 10) Immediate Next Commit Scope

- Add permission engine and wire into tool execution path.
- Add task manager skeleton and task state persistence.
- Add event bus interface and emit tool/model lifecycle events.

# CrucibAI: OLD vs NEW Architecture

## THE OLD APPROACH (What we designed - WRONG)

```
Goal: "Build Aegis Omega"
         ↓
    [Planner]
         ↓
    "Pick agents for Phase 5"
         ↓
    [77 agents selected]
         ↓
    TRY TO RUN ALL PARALLEL:
    ┌─────────────────────────────────────────┐
    │ [Agent1] [Agent2] [Agent3] ... [Agent77] │  ← All at once
    │    ↓         ↓         ↓              ↓  │
    │  Conflict! Conflict! Conflict!          │
    │    ↓         ↓         ↓              ↓  │
    │  [Shared workspace with locks]          │
    │                                         │
    │  Result: Slow, brittle, complex        │
    └─────────────────────────────────────────┘
         ↓
    Try to merge results
         ↓
    83/88 preview fails
```

**Problems:**
- All agents need full context (50K+ tokens)
- Conflicts in shared workspace
- Hard to control execution order
- Can't adapt to errors mid-flight

---

## THE NEW APPROACH (Manus pattern - CORRECT)

```
Goal: "Build Aegis Omega"
         ↓
    [Planner Analyzes]
         ↓
    Create Initial Plan
         ↓
    ┌─────────────────────────────────────────────────────────┐
    │ ITERATION LOOP (Runs until goal complete)              │
    │                                                          │
    │ Iteration 1:                                            │
    │   1. ANALYZE: Current workspace state                  │
    │   2. PLANNER: "Best agent right now? Backend."         │
    │   3. RUN: Backend Agent (5K token scoped context)      │
    │   4. OBSERVE: Result → event stream                    │
    │                                                          │
    │ Iteration 2:                                            │
    │   1. ANALYZE: Workspace has backend code               │
    │   2. PLANNER: "Next? Frontend."                        │
    │   3. RUN: Frontend Agent (5K token scoped context)     │
    │   4. OBSERVE: Result → event stream                    │
    │                                                          │
    │ Iteration 3:                                            │
    │   1. ANALYZE: Backend + Frontend done                  │
    │   2. PLANNER: "Next? Security scan."                   │
    │   3. RUN: Security Agent (5K token scoped context)     │
    │   4. OBSERVE: Result → event stream                    │
    │                                                          │
    │ Iteration 5:                                            │
    │   [UPDATE PLAN based on progress so far]               │
    │                                                          │
    │ Iteration N:                                            │
    │   PLANNER: "All done? Yes → COMPLETE"                  │
    │                                                          │
    └─────────────────────────────────────────────────────────┘
         ↓
    Return final code
```

**Advantages:**
- Each agent gets scoped context only (5-10K)
- Sequential, easy to debug
- Can adapt based on workspace state
- Plan updates keep agents aligned
- No conflicts, no locking needed

---

## TOKEN COMPARISON

### OLD APPROACH (Bad)
```
Agent 1 context:
  - Full plan (2K)
  - All previous outputs (10K)
  - Full workspace state (20K)
  - Backend examples (5K)
  - Frontend examples (5K)
  = 42K tokens JUST for Agent 1

Agent 2 context:
  - Full plan (2K)
  - All previous outputs (10K)
  - Full workspace state (20K)
  - Frontend examples (5K)
  - Testing examples (5K)
  = 42K tokens JUST for Agent 2

...repeated 77 times with high overlap

TOTAL: 3,234K tokens wasted on redundant context
(77 agents × 42K)

Also: Model quality degrades at 30K+ tokens in context
```

### NEW APPROACH (Good)
```
Iteration 1: Backend Agent
  - Current plan (1K)
  - "Build API endpoints for Aegis" (1K)
  - Backend examples (3K)
  - Current workspace state (1K)
  = 6K tokens

Iteration 2: Frontend Agent
  - Updated plan (1K)
  - "Build dashboard UI" (1K)
  - Frontend examples (3K)
  - Current workspace state (1K)
  = 6K tokens

Iteration 3: Security Agent
  - Updated plan (1K)
  - "Scan for vulnerabilities" (1K)
  - Security examples (3K)
  - Current code snippet (1K)
  = 6K tokens

...repeated N times (~50-100 iterations for complex app)

TOTAL: 6K × 75 iterations = 450K tokens
(5x more iterations but 1/7th per-agent cost)

Plus: Model maintains quality throughout (context always <10K)
```

---

## DECISION FLOW COMPARISON

### OLD: Static DAG
```
BEFORE EXECUTION:
Planner decides all 77 agents upfront
Builds static DAG with dependencies
No flexibility
"This is the plan, execute it"

PROBLEM: Can't adapt if first agent fails
```

### NEW: Dynamic Selection
```
BEFORE EACH ITERATION:
Planner analyzes current state
Decides NEXT BEST AGENT for current situation
Executes that agent
Moves to next iteration

ADVANTAGE: Can recover from failures
Can reorder based on what works
Can skip unnecessary agents
```

---

## RECURSION: THE TRAP

### OLD APPROACH (No guards)
```python
# Agent is called
Backend Agent spawns Sub-Agent A
  Sub-Agent A spawns Sub-Agent B
    Sub-Agent B spawns Sub-Agent C
      Sub-Agent C calls Backend Agent (!)
        Backend Agent calls Sub-Agent A (!)
          ... infinite loop

No way to detect this
No depth limits
System crashes or hangs
```

### NEW APPROACH (With guards)
```python
recursion_depth_limit = 4
agent_call_history = deque(maxlen=5)

# Agent is called
Backend Agent (depth=1)
  └─ Security Agent (depth=2)
     └─ Validator Agent (depth=3)
        └─ Backend Agent (detected in history + depth > 2)
           ERROR: Recursion detected
           Agent halts gracefully
```

---

## MEMORY PATTERN

### OLD (Global state)
```python
# All agents share one context
shared_context = {
  "plan": plan_md,
  "workspace": all_files,
  "previous_outputs": all_agent_outputs,
  "workspace_state": full_analysis,
  ...
}

agent1.context = shared_context
agent2.context = shared_context
agent3.context = shared_context

# Problem: 50K tokens every time
#          Context pollution
#          Agents confused by irrelevant info
```

### NEW (Scoped context)
```python
# Each agent gets tailored context
backend_context = {
  "goal": "Build API endpoints",
  "current_api_state": api_files_only,
  "examples": backend_patterns,
  "stack": "Express + PostgreSQL",
}

frontend_context = {
  "goal": "Build dashboard UI",
  "current_ui_state": components_only,
  "examples": frontend_patterns,
  "stack": "React + Tailwind",
}

# Benefit: 6K tokens each
#          Focused attention
#          Agents only see relevant info
```

---

## EXECUTION TIMELINE

### OLD APPROACH
```
T=0s    Planner picks 77 agents
T=1s    Launch all 77 in parallel
T=2-30s Agents run, handle conflicts, locks
T=31s   Merge results
T=32s   Build fails
T=33s   ???

Problem: Can't debug where issue came from
         Multiple agents working simultaneously
         Blame assignment is hard
```

### NEW APPROACH
```
T=0s    Planner analyzes goal, creates plan
T=1s    ITERATE iteration 1: Backend Agent runs (scoped)
        ├─ ANALYZE: Goal is valid
        ├─ SELECT: Backend Agent chosen
        ├─ EXECUTE: Builds /api/endpoints
        └─ OBSERVE: Success → event log
        
T=2s    ITERATE iteration 2: Frontend Agent runs
        ├─ ANALYZE: Backend done, workspace updated
        ├─ SELECT: Frontend Agent chosen
        ├─ EXECUTE: Builds /src/dashboard
        └─ OBSERVE: Success → event log
        
T=3s    ITERATE iteration 3: Testing Agent
        └─ OBSERVE: Missing test utils → ERROR
           Re-plan: "Run Utils Agent first"
        
T=4s    ITERATE iteration 4: Utils Agent
        └─ OBSERVE: Success
        
T=5s    ITERATE iteration 5: Testing Agent (retry)
        └─ OBSERVE: Success
        
T=6s    [Plan refresh every 5 iterations]
        Update plan based on progress

...

T=N     ITERATE iteration N: Final validation
        └─ COMPLETE: All tasks done

Problem: None. Everything transparent.
         Clear execution trail.
         Can recover from issues.
```

---

## CONTEXT ARCHITECTURE

### OLD (Flat)
```
            [Global Shared Context - 50K tokens]
                    ↙  ↓  ↘
                  /    |    \
            Agent1  Agent2  Agent3  ...  Agent77

Every agent sees EVERYTHING
High token cost
Context pollution
Performance degrades
```

### NEW (Scoped)
```
        [Planning Loop - LLM decides next agent]
         ↓         ↓         ↓         ↓
    [Backend]  [Frontend] [Test]  [Deploy]
     Context    Context    Context  Context
    (6K only)  (6K only)  (6K only) (6K only)

Each agent sees ONLY what's relevant
Low token cost
Focus attention
Performance maintained
```

---

## SUMMARY TABLE

| Aspect | OLD (WRONG) | NEW (CORRECT) |
|--------|---------|----------|
| **Execution** | Parallel 77 agents | Sequential iterations |
| **Agent Selection** | Pre-planned DAG | Dynamic per iteration |
| **Context per Agent** | 40-50K (global) | 5-10K (scoped) |
| **Plan Updates** | Static, once | Dynamic, every 5 iter |
| **Recursion** | Unguarded (risky) | Max depth 4 + guards |
| **Speed** | Parallelization (doesn't work) | Smart selection (works) |
| **Debugging** | Hard (parallel chaos) | Easy (sequential trace) |
| **Adaptability** | Low (fixed DAG) | High (dynamic decisions) |
| **Failure Recovery** | Difficult | Simple (retry in loop) |
| **Token Efficiency** | Bad (3000K+ wasted) | Good (450K precise) |

---

## THE KEY INSIGHT

**Manus didn't solve the problem by parallelization.**

Manus solved it by:
1. Being SMARTER about WHICH agent to run NEXT
2. Keeping FOCUS with SCOPED context
3. Maintaining FLEXIBILITY with DYNAMIC planning
4. Staying SAFE with RECURSION guards

Speed comes from **good decisions**, not **parallel execution**.

That's the insight we missed.

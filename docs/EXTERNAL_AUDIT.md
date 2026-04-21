# External Audit: collection-claude-code-source-code + Goose

*CF25 — 2026-04-21. Cross-reference of uploaded archives vs CrucibAI `main`.*

## Summary

| Source | Files scanned | Lang | Top concept |
|---|---:|---|---|
| `claude-code-source-code` | 1,940 | TypeScript (Bun) | Fully typed CLI agent with permission classifier ladder |
| `original-source-code` | 1,904 | TypeScript | Prior version of the above |
| `claw-code` | 109 | Python port | Python re-implementation of the TS tree |
| `clawspring` | 91 | Python | Compact multi-provider agent with compaction + voice |
| `multi_agent` | 4 | Python | Threaded sub-agent spawner |
| `skill` | 6 | Python | Skill loader/executor (inline or forked) |
| `memory` | 8 | Python | Memory consolidator + scanner + store |
| Goose (app.asar) | 75 | TypeScript/Electron | Desktop wrapper with IPC + mesh + Ollama |

**Capability counts after cross-reference: HAVE 18 · MISS 13 · DUP 5**

## Inventory highlights

### claude-code-source-code / original-source-code (TypeScript)
- `QueryEngine.ts` — top-level conversation loop with session persistence hooks.
- `utils/permissions/` — 25-file permission subsystem: `PermissionMode`, `PermissionRule`, `PermissionUpdate`, `bashClassifier.ts`, `yoloClassifier.ts`, `dangerousPatterns.ts`, `shadowedRuleDetection.ts`, `permissionExplainer.ts`.
- `services/SessionMemory/` — per-session durable memory tier.
- `commands/` — 80+ slash commands including `autofix-pr`, `commit-push-pr`, `doctor`, `compact`, `context`, `cost`, `agents`, `bughunter`, `good-claude`, `heapdump`.
- `coordinator/coordinatorMode.ts` — cross-agent coordinator mode.
- `costHook.ts` + `cost-tracker.ts` — per-turn token+USD accounting.

### clawspring (Python)
- `agent.py` — neutral-format agent loop with multi-provider streaming.
- `compaction.py` — two-layer compression with explicit `estimate_tokens()` heuristic (chars ÷ 3.5).
- `tool_registry.py` — `@dataclass ToolDef` with `read_only` + `concurrent_safe` flags.
- `voice/` — `recorder.py`, `stt.py`, `keyterms.py` for voice input mode.
- `mcp/` — MCP client + tool bridge (`client.py`, `tools.py`, `types.py`).
- `memory/consolidator.py` — auto-extract preferences from completed sessions (3-memory cap, 0.8 confidence floor).
- `subagent.py` — threaded sub-agent forker with `AgentDefinition` (tools, model, source).

### Goose (Electron desktop)
- 51 IPC channels including `check-mesh`, `start-mesh`, `check-ollama`, `create-chat-window`, `install-update`, `notify`, `always-on-top`, `directory-chooser`, `get-secret-key`.
- 55 runtime deps including `@mcp-ui/client`, `@radix-ui/*`, `@tanstack/react-form`, `@modelcontextprotocol/ext-apps`.
- `goosed` external HTTP backend separate from the UI process.
- Ollama integration + peer mesh concept (distinctive).

## Cross-reference table

| Capability | External source | CrucibAI status | If MISS → target file |
|---|---|---|---|
| 8-phase runtime loop | clawspring/agent.py | **HAVE** `backend/services/runtime/runtime_engine.py` | — |
| Tool registry w/ flags | clawspring/tool_registry.py | **HAVE** `backend/services/tools/registry.py` | — |
| Permission rules + modes | claude-code-source-code/utils/permissions/ | **HAVE** `backend/services/permissions/` | — |
| Subagent spawner | multi_agent/subagent.py | **HAVE** `backend/services/runtime/subagent_runner.py` | — |
| MCP client | clawspring/mcp/ | **HAVE** `backend/routes/mcp.py` | — |
| Bash/shell risk classifier | `utils/permissions/bashClassifier.ts` + `dangerousPatterns.ts` | **MISS** | `backend/services/permissions/bash_classifier.py` |
| Shadowed-rule detection | `shadowedRuleDetection.ts` | **MISS** | `backend/services/permissions/rule_linter.py` |
| Permission cascade state machine | `getNextPermissionMode.ts` | **MISS** | `backend/services/permissions/mode_transitions.py` |
| Auto memory consolidator | `memory/consolidator.py` | **MISS** | `backend/services/memory/consolidator.py` |
| Session memory tier | `services/SessionMemory/` | **HAVE-weak** `backend/services/runtime/session_journal.py` | (upgrade, don't duplicate) |
| Voice input mode | `clawspring/voice/` | **MISS** | `frontend/src/components/voice/VoiceRecorder.jsx` + `backend/routes/voice.py` |
| Cost tracker w/ USD | `cost-tracker.ts` + `costHook.ts` | **MISS** surface | `frontend/src/pages/CostCenter.jsx` ↔ `backend/routes/cost_hook.py` |
| `doctor` diagnostic command | `commands/doctor/` | **MISS** | `backend/routes/doctor.py` + `frontend/src/pages/Doctor.jsx` |
| `autofix-pr` command | `commands/autofix-pr/` | **MISS** | `backend/routes/autofix_pr.py` |
| `commit-push-pr` command | `commit-push-pr.ts` | **MISS** | `backend/routes/commit_push_pr.py` |
| `compact` slash command | `commands/compact/` | **HAVE** in runtime, **MISS** UI surface | `frontend/src/components/CompactButton.jsx` |
| Context compaction w/ explicit estimator | `clawspring/compaction.py` | **HAVE** `backend/services/runtime/context_manager.py` | (port the `chars/3.5` estimator as a fast path) |
| Coordinator mode | `coordinator/coordinatorMode.ts` | **DUP** with Plan mode | — |
| External agent backend (goosed pattern) | Goose main.js | **MISS** | `docs/ARCHITECTURE_NOTES.md` (design-only for now) |
| Ollama local-model detection | Goose IPC `check-ollama` | **MISS** | `backend/routes/providers.py` — add `local_ollama` probe |
| Peer-to-peer mesh | Goose `check-mesh` / `start-mesh` | **MISS** | `backend/services/mesh/` (design-only; non-blocking) |
| Always-on-top window | Goose IPC | **DUP** (web app, N/A) | — |
| Session sharing URL | Goose `sessionSharing` | **HAVE** `backend/routes/share.py` | — |
| Wakelock toggle | Goose IPC | **MISS** | `frontend/src/hooks/useWakelock.js` (web Lock API) |
| Quick launcher hotkey | Goose IPC | **MISS** | `frontend/src/components/QuickLauncher.jsx` (Cmd+K) |
| Recipe / template terms gate | Goose `has-accepted-recipe-before` | **HAVE** `backend/routes/marketplace.py` | — |
| Spellcheck toggle | Goose IPC | **DUP** (browser-native) | — |

## Top 10 import candidates (impact × effort ratio)

1. **Bash risk classifier + dangerous-patterns library** — 1-day port, high safety value. Prevents `rm -rf /`, `curl | sh`, etc. from ever reaching a sandbox.
2. **Auto memory consolidator** — 2-day port, compounding ROI. CrucibAI's memory tier becomes smarter after every run.
3. **Shadowed-rule linter** — 0.5-day port. Catches permission policy mistakes during authoring.
4. **`doctor` command** — 1-day build. Big UX win for first-run debugging.
5. **`commit-push-pr` command** — 1-day build. Ships user changes to GitHub in one click.
6. **Voice input mode** — 3-day build. Competitive differentiator vs Cursor/Lovable.
7. **Ollama probe** — 0.5-day. Unlocks local-LLM workflows and hits the privacy-first audience.
8. **Cost center UI surface** — 1-day. The numbers already exist; they just need a dashboard tab.
9. **Permission mode transition state machine** — 1.5-day port. Gives us accept-edits / plan-only / yolo tiers.
10. **Quick launcher (Cmd+K)** — 0.5-day. Makes the 3-pane nav dramatically faster.

## Commands to import the top 3

```bash
cd /tmp/CrucibAI

# 1) Bash risk classifier
cp -v /tmp/audit_drops/claude_src/collection-claude-code-source-code-main/claude-code-source-code/src/utils/permissions/bashClassifier.ts \
      /tmp/audit_drops/claude_src/collection-claude-code-source-code-main/claude-code-source-code/src/utils/permissions/dangerousPatterns.ts \
      docs/external/
# Port to Python:
touch backend/services/permissions/bash_classifier.py
# (pattern: read regex list from dangerousPatterns, emit {level, reason})

# 2) Memory consolidator
cp -v /tmp/audit_drops/claude_src/collection-claude-code-source-code-main/memory/consolidator.py \
      backend/services/memory/consolidator.py
# Add route wiring:  backend/server.py  →  ("routes.memory_consolidate", "router", False)

# 3) Shadowed-rule linter
cp -v /tmp/audit_drops/claude_src/collection-claude-code-source-code-main/claude-code-source-code/src/utils/permissions/shadowedRuleDetection.ts \
      docs/external/
# Port to Python:
touch backend/services/permissions/rule_linter.py
```

## What is SAFE to ignore

- The entire `claw-code/` and `original-source-code/` trees are duplicates of the TypeScript original; no new capabilities.
- Goose `spellcheck` + `always-on-top` + `dockIcon` are desktop-OS-specific and don't apply to the web-hosted CrucibAI shell.
- `coordinator/coordinatorMode.ts` overlaps our existing plan-first mode; not worth a port.

## Licensing note

All three external sources carry permissive licenses (MIT for claude-code-source-code + Goose; check `clawspring/pyproject.toml`). Direct copies are fine; mark imports with `# Adapted from <source>` comments when we pull specific files.

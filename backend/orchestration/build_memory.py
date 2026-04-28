"""
build_memory.py — Structured Build Memory for CrucibAI

Every build job has a shared JSON memory file written to the workspace.
All agents read from this memory instead of raw truncated prior-agent text.

Memory structure:
  goal            — original user prompt
  build_type      — fullstack | frontend | backend | mobile | api | saas | ecommerce
  stack           — { frontend, backend, database, auth, deploy }
  file_manifest   — [ { path, agent, status } ]
  route_map       — { "GET /api/users": "routes/users.py" }
  api_contract    — { "POST /api/auth/login": { body, response } }
  schema          — { tables: [...], models: [...] }
  generated_files — [ path, ... ]
  dependency_graph — { "App.tsx": ["Navbar.tsx", "pages/Home.tsx"] }
  validation      — { passed: bool, errors: [...], warnings: [...] }
  repair_queue    — [ { file, error, attempts } ]
  complexity_score — 1-10
  model_decisions — { agent_name: "cerebras"|"anthropic" }
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MEMORY_FILENAME = ".crucib_build_memory.json"


def _memory_path(workspace_path: str) -> Path:
    return Path(workspace_path) / _MEMORY_FILENAME


def load_build_memory(workspace_path: str) -> Dict[str, Any]:
    """Load the build memory for a job. Returns empty dict if not found."""
    if not workspace_path:
        return {}
    p = _memory_path(workspace_path)
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("build_memory: failed to load %s: %s", p, e)
        return {}


def save_build_memory(workspace_path: str, memory: Dict[str, Any]) -> None:
    """Persist the build memory for a job."""
    if not workspace_path:
        return
    p = _memory_path(workspace_path)
    try:
        os.makedirs(workspace_path, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2)
    except Exception as e:
        logger.warning("build_memory: failed to save %s: %s", p, e)


def _staged_fullstack_env_enabled() -> bool:
    return os.environ.get("CRUCIBAI_STAGED_FULLSTACK", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def init_build_memory(workspace_path: str, goal: str, build_type: str = "fullstack") -> Dict[str, Any]:
    """Initialize a fresh build memory for a new job."""
    memory: Dict[str, Any] = {
        "goal": goal,
        "build_type": build_type,
        "stack": {},
        "file_manifest": [],
        "route_map": {},
        "api_contract": {},
        "schema": {},
        "generated_files": [],
        "dependency_graph": {},
        "validation": {"passed": False, "errors": [], "warnings": []},
        "repair_queue": [],
        "complexity_score": _estimate_complexity(goal),
        "model_decisions": {},
    }
    # P2 — Manus-style convergence: optional staged waves for large full-stack builds (env-driven).
    bt = str(build_type or "").lower()
    if _staged_fullstack_env_enabled() and bt in (
        "fullstack",
        "saas",
        "ecommerce",
        "backend",
    ):
        memory["delivery_strategy"] = "staged_fullstack_waves"
        memory["staged_waves"] = [
            {
                "wave": 1,
                "focus": "vite_client_shell_routes",
                "done_when": "frontend entrypoints + pages compile (verification.compile)",
            },
            {
                "wave": 2,
                "focus": "backend_api_auth_db",
                "done_when": "Python compiles + API smoke passes",
            },
        ]
        memory["agent_hints"] = (
            "STAGED BUILD (CRUCIBAI_STAGED_FULLSTACK): finish Wave 1 (all routed pages + "
            "valid JSX/TS) before adding Wave 2 backend files. Do not paste manifests into components."
        )
    save_build_memory(workspace_path, memory)
    return memory


def update_build_memory(workspace_path: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Merge updates into the build memory and persist."""
    memory = load_build_memory(workspace_path)
    for key, value in updates.items():
        if key in ("file_manifest", "generated_files", "repair_queue") and isinstance(value, list):
            existing = memory.get(key, [])
            # Deduplicate by path for file_manifest, by string for others
            if key == "file_manifest":
                existing_paths = {e.get("path") for e in existing if isinstance(e, dict)}
                for item in value:
                    if isinstance(item, dict) and item.get("path") not in existing_paths:
                        existing.append(item)
                        existing_paths.add(item.get("path"))
            elif key == "generated_files":
                existing_set = set(existing)
                for item in value:
                    if item not in existing_set:
                        existing.append(item)
                        existing_set.add(item)
            else:
                existing.extend(value)
            memory[key] = existing
        elif key in ("route_map", "api_contract", "schema", "stack", "model_decisions") and isinstance(value, dict):
            existing_dict = memory.get(key, {})
            existing_dict.update(value)
            memory[key] = existing_dict
        elif key == "validation" and isinstance(value, dict):
            existing_v = memory.get("validation", {})
            existing_v.update(value)
            if "errors" in value and isinstance(value["errors"], list):
                existing_errors = existing_v.get("errors", [])
                existing_errors.extend(value["errors"])
                existing_v["errors"] = existing_errors
            memory["validation"] = existing_v
        else:
            memory[key] = value
    save_build_memory(workspace_path, memory)
    return memory


def get_memory_summary(workspace_path: str) -> str:
    """
    Return a compact structured summary of the build memory for injection
    into agent prompts. This replaces raw truncated prior-agent text.
    """
    memory = load_build_memory(workspace_path)
    if not memory:
        return ""

    lines = ["## BUILD MEMORY (structured context — read this before generating code)"]

    goal = memory.get("goal", "")
    if goal:
        lines.append(f"\n**Goal:** {goal}")

    build_type = memory.get("build_type", "")
    if build_type:
        lines.append(f"**Build Type:** {build_type}")

    complexity = memory.get("complexity_score", 0)
    if complexity:
        lines.append(f"**Complexity Score:** {complexity}/10")

    if memory.get("delivery_strategy") == "staged_fullstack_waves":
        lines.append("\n**Delivery Strategy:** staged waves — complete frontend compile gate before backend expansion.")
        for w in memory.get("staged_waves") or []:
            if isinstance(w, dict):
                lines.append(
                    f"  - Wave {w.get('wave')}: {w.get('focus')} → {w.get('done_when')}"
                )
        ah = memory.get("agent_hints")
        if ah:
            lines.append(f"\n{ah}")

    stack = memory.get("stack", {})
    if stack:
        stack_str = " | ".join(f"{k}: {v}" for k, v in stack.items() if v)
        lines.append(f"**Stack:** {stack_str}")

    schema = memory.get("schema", {})
    if schema:
        tables = schema.get("tables", [])
        if tables:
            lines.append(f"**Database Tables:** {', '.join(str(t) for t in tables[:20])}")

    route_map = memory.get("route_map", {})
    if route_map:
        routes_preview = list(route_map.items())[:20]
        lines.append("\n**API Routes:**")
        for route, handler in routes_preview:
            lines.append(f"  {route} → {handler}")

    api_contract = memory.get("api_contract", {})
    if api_contract:
        contracts_preview = list(api_contract.items())[:10]
        lines.append("\n**API Contracts:**")
        for endpoint, contract in contracts_preview:
            if isinstance(contract, dict):
                body = contract.get("body", "")
                resp = contract.get("response", "")
                lines.append(f"  {endpoint}: body={body} → {resp}")

    generated = memory.get("generated_files", [])
    if generated:
        lines.append(f"\n**Already Generated ({len(generated)} files):**")
        # Show folder structure summary
        dirs: Dict[str, int] = {}
        for f in generated:
            d = str(Path(f).parent)
            dirs[d] = dirs.get(d, 0) + 1
        for d, count in sorted(dirs.items())[:15]:
            lines.append(f"  {d}/ ({count} files)")

    manifest = memory.get("file_manifest", [])
    pending = [m for m in manifest if isinstance(m, dict) and m.get("status") == "pending"]
    if pending:
        lines.append(f"\n**Files Still Needed ({len(pending)}):**")
        for m in pending[:20]:
            lines.append(f"  {m.get('path')} (by {m.get('agent', '?')})")

    repair_queue = memory.get("repair_queue", [])
    if repair_queue:
        lines.append(f"\n**Repair Queue ({len(repair_queue)} items):**")
        for r in repair_queue[:5]:
            if isinstance(r, dict):
                lines.append(f"  {r.get('file')}: {r.get('error', '')[:100]}")

    validation = memory.get("validation", {})
    errors = validation.get("errors", [])
    if errors:
        lines.append(f"\n**Validation Errors ({len(errors)}):**")
        for e in errors[:5]:
            lines.append(f"  - {str(e)[:120]}")

    return "\n".join(lines)


def record_agent_files(workspace_path: str, agent_name: str, written_files: List[str]) -> None:
    """Record which files an agent wrote into the build memory."""
    if not written_files:
        return
    new_entries = [{"path": f, "agent": agent_name, "status": "generated"} for f in written_files]
    update_build_memory(workspace_path, {
        "file_manifest": new_entries,
        "generated_files": written_files,
    })


def record_model_decision(workspace_path: str, agent_name: str, model: str) -> None:
    """Record which model was used for an agent."""
    update_build_memory(workspace_path, {"model_decisions": {agent_name: model}})


def _estimate_complexity(goal: str) -> int:
    """Estimate build complexity 1-10 from the goal string."""
    goal_lower = goal.lower()
    score = 3  # baseline
    # High complexity signals
    high = ["auth", "authentication", "payment", "braintree", "billing", "saas", "multi-tenant",
            "real-time", "websocket", "microservice", "kubernetes", "docker", "deployment",
            "security", "rbac", "permissions", "admin", "dashboard", "analytics", "reporting",
            "search", "elasticsearch", "ai", "ml", "machine learning", "recommendation"]
    # Medium complexity signals
    medium = ["crud", "api", "database", "postgres", "mysql", "mongodb", "redis",
              "full-stack", "fullstack", "backend", "frontend", "react", "nextjs",
              "user", "profile", "settings", "notification", "email"]
    # Simple signals
    simple = ["landing page", "portfolio", "blog", "static", "simple", "basic", "todo"]
    for kw in high:
        if kw in goal_lower:
            score += 1
    for kw in medium:
        if kw in goal_lower:
            score += 0.5
    for kw in simple:
        if kw in goal_lower:
            score -= 1
    return max(1, min(10, round(score)))

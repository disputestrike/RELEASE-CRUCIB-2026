"""
WorkspaceAssemblyPipeline (P2) — multi-file ingest → merge → materialize.

Behind CRUCIBAI_ASSEMBLY_V2=1|true|yes|on. When unset/false, legacy paths run unchanged.
P3: when V2 is enabled, `real_agent_runner` short-circuits to this pipeline so the legacy
four-file writer never runs (no duplicate disk writes for the same outputs).

Primary entry points:
  - materialize_from_previous_outputs() — used by File Tool Agent (replaces narrow 4-file-only writes).
  - materialize_swarm_agent_output() — after each swarm LLM step, applies extra path-tagged fences.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Explicit order for merge (earlier agents can be overwritten by later).
ASSEMBLY_AGENT_ORDER: Tuple[str, ...] = (
    "Planner",
    "Requirements Clarifier",
    "Stack Selector",
    "Design Agent",
    "Frontend Generation",
    "Layout Agent",
    "Backend Generation",
    "Database Agent",
    "API Integration",
    "Test Generation",
    "Documentation Agent",
    "DevOps Agent",
    "SEO Agent",
    "Content Agent",
    "Auth Setup Agent",
)

_ORDER_RANK = {name: i for i, name in enumerate(ASSEMBLY_AGENT_ORDER)}

# Fence: optional lang, then first line may be ONLY a relative path (common LLM pattern).
_FENCE_PATH_FIRSTLINE = re.compile(
    r"```(?:[\w+\-.#]*)\s*\n"
    r"(?P<first>[^\n`]{1,240})\n"
    r"(?P<body>.*?)"
    r"```",
    re.DOTALL | re.IGNORECASE,
)
# Fence: ```lang path/to/file.ext
_FENCE_LANG_PATH = re.compile(
    r"```(?P<lang>[\w+\-.#]*)\s+(?P<path>[A-Za-z0-9_.\-][A-Za-z0-9_./\-]*\.(?:"
    r"jsx?|tsx?|ts|js|py|json|ya?ml|yml|md|html|htm|css|scss|sql|sh|graphql|"
    r"prisma|toml|xml|txt|mjs|cjs"
    r"))\s*\n(?P<body>.*?)```",
    re.DOTALL | re.IGNORECASE,
)
# Body line: // file: x or # file: x
_FILE_HINT = re.compile(
    r"^\s*(?://|#)\s*file(?:path)?\s*:\s*(?P<path>[A-Za-z0-9_./\-]+\.(?:jsx?|tsx?|ts|js|py|json|ya?ml|yml|md|html|css|scss|sql))\s*$",
    re.IGNORECASE,
)


def assembly_v2_enabled() -> bool:
    return os.environ.get("CRUCIBAI_ASSEMBLY_V2", "").strip().lower() in ("1", "true", "yes", "on")


def _norm_rel(p: str) -> str:
    p = (p or "").strip().replace("\\", "/").lstrip("/")
    if ".." in p.split("/"):
        return ""
    return p


def _raw_text(blob: Dict[str, Any]) -> str:
    if not isinstance(blob, dict):
        return ""
    v = blob.get("output") or blob.get("result") or blob.get("code") or ""
    if isinstance(v, dict):
        import json

        return json.dumps(v)
    return (v if isinstance(v, str) else str(v)) or ""


def _extract_code_for_path(raw: str, rel: str) -> str:
    from real_agent_runner import _extract_code

    return _extract_code(raw, filepath=rel or "file.txt")


def parse_proposed_files(raw: str, default_rel: str, agent_name: str) -> List[Tuple[str, str]]:
    """
    Return list of (rel_path, content). Never escapes workspace roots (caller uses safe write).
    """
    raw = raw or ""
    out: List[Tuple[str, str]] = []
    seen_spans: set[Tuple[int, int]] = set()

    def add(rel: str, body: str) -> None:
        rel = _norm_rel(rel)
        body = (body or "").strip("\n")
        if not rel or not body:
            return
        body = _extract_code_for_path(body, rel)
        if not body.strip():
            return
        out.append((rel, body))

    for m in _FENCE_LANG_PATH.finditer(raw):
        add(m.group("path"), m.group("body"))
        seen_spans.add((m.start(), m.end()))

    for m in _FENCE_PATH_FIRSTLINE.finditer(raw):
        if any(m.start() >= a and m.end() <= b for a, b in seen_spans):
            continue
        first = (m.group("first") or "").strip()
        body = m.group("body") or ""
        if "/" not in first and "." not in first:
            continue
        if len(first) > 200 or " " in first or first.startswith("```"):
            continue
        if not re.match(r"^[A-Za-z0-9_./\-]+\.[A-Za-z0-9]{1,12}$", first):
            continue
        add(first, body)

    if not out and default_rel:
        single = _extract_code_for_path(raw, default_rel)
        if single.strip():
            dr = _norm_rel(default_rel)
            if dr:
                out.append((dr, single))
    return out


def merge_last_writer(pairs: List[Tuple[str, str, str]]) -> Dict[str, Tuple[str, str]]:
    """pairs: (rel_path, content, agent_name) in application order — later wins."""
    merged: Dict[str, Tuple[str, str]] = {}
    for rel, content, agent in pairs:
        if not rel or not content:
            continue
        merged[rel] = (content, agent)
    return merged


def _sort_agent_names(names: List[str]) -> List[str]:
    def key(n: str):
        return (_ORDER_RANK.get(n, 10_000), n)

    return sorted(names, key=key)


def collect_assembly_pairs(previous_outputs: Dict[str, Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    from agent_real_behavior import ARTIFACT_PATHS

    pairs: List[Tuple[str, str, str]] = []
    names = _sort_agent_names([n for n in previous_outputs if isinstance(previous_outputs.get(n), dict)])
    for agent_name in names:
        blob = previous_outputs[agent_name]
        raw = _raw_text(blob)
        if not raw.strip():
            continue
        default_rel = ARTIFACT_PATHS.get(agent_name, "")
        for rel, body in parse_proposed_files(raw, default_rel, agent_name):
            pairs.append((rel, body, agent_name))
    return pairs


def _safe_write_workspace(workspace_path: str, rel: str, content: str) -> bool:
    from orchestration.executor import _safe_write

    return _safe_write(workspace_path, rel, content) is not None


def ensure_minimum_preview_tree(workspace_path: str, job_stub: Optional[Dict[str, Any]] = None) -> List[str]:
    """Fill missing Vite contract files without clobbering agent output."""
    from orchestration.executor import _ensure_preview_contract_files

    job = dict(job_stub or {})
    job.setdefault("goal", "")
    job.setdefault("build_target", "vite_react")
    return _ensure_preview_contract_files(workspace_path, job)


def materialize_merged_map(
    workspace_path: str,
    merged: Dict[str, Tuple[str, str]],
) -> Tuple[List[str], List[str]]:
    written: List[str] = []
    errors: List[str] = []
    if not workspace_path or not os.path.isdir(workspace_path):
        return written, ["invalid_workspace"]
    for rel, (content, _agent) in sorted(merged.items(), key=lambda x: x[0]):
        try:
            if _safe_write_workspace(workspace_path, rel, content):
                written.append(rel)
            else:
                errors.append(f"reject_or_failed:{rel}")
        except Exception as e:
            errors.append(f"{rel}:{e}")
            logger.warning("assembly write failed %s: %s", rel, e)
    return written, errors


async def materialize_from_previous_outputs(
    project_id: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    *,
    goal_snippet: str = "",
) -> Dict[str, Any]:
    """
    File Tool Agent V2: multi-file assembly into project workspace (same root as legacy FileAgent).
    """
    safe_pid = str(project_id).replace("..", "").strip() or "default"
    workspace = Path(__file__).resolve().parents[1] / "workspace" / safe_pid
    workspace.mkdir(parents=True, exist_ok=True)
    ws = str(workspace)

    pairs = collect_assembly_pairs(previous_outputs)
    merged = merge_last_writer(pairs)
    written, errors = materialize_merged_map(ws, merged)

    extra = ensure_minimum_preview_tree(ws, {"goal": goal_snippet, "build_target": "vite_react"})
    for rel in extra:
        if rel not in written:
            written.append(rel)

    msg = f"Assembly V2: wrote {len(written)} path(s). Multi-file pipeline."
    if errors:
        msg += f" Issues: {'; '.join(errors[:6])}"
    return {
        "output": msg,
        "tokens_used": 0,
        "status": "completed",
        "result": msg,
        "code": msg,
        "real_agent": True,
        "files_written": written,
        "errors": errors,
        "assembly_v2": True,
        "merge_count": len(merged),
    }


def materialize_swarm_agent_output(
    workspace_path: str,
    agent_name: str,
    result: Dict[str, Any],
) -> List[str]:
    """
    After a swarm LLM step: extract path-tagged fences and write on top of run_agent_real_behavior output.
    Returns list of newly written rel paths.
    """
    if not assembly_v2_enabled() or not workspace_path or not os.path.isdir(workspace_path):
        return []
    from agent_real_behavior import ARTIFACT_PATHS

    raw = _raw_text(result)
    if not raw.strip():
        return []
    default_rel = ARTIFACT_PATHS.get(agent_name, "")
    pairs = [(rel, body, agent_name) for rel, body in parse_proposed_files(raw, default_rel, agent_name)]
    if len(pairs) <= 1 and not any("/" in p[0] for p in pairs):
        # Single default-only — already handled by run_agent_real_behavior; skip duplicate work
        return []
    merged = merge_last_writer(pairs)
    written, _ = materialize_merged_map(workspace_path, merged)
    if written:
        try:
            from orchestration.executor import append_node_artifact_record

            append_node_artifact_record(
                workspace_path,
                {
                    "agent": agent_name,
                    "kind": "assembly_v2_swarm",
                    "paths": written[:40],
                },
            )
        except Exception:
            pass
    return written

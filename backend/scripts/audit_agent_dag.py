#!/usr/bin/env python3
"""
DAG agent audit: classify every AGENT_DAG node against real wiring in code.

Outputs (repo root docs/):
  - agent_audit.csv
  - agent_audit.json

Usage (from repo root):
  cd backend && set PYTHONPATH=. && python scripts/audit_agent_dag.py
  cd backend && PYTHONPATH=. python scripts/audit_agent_dag.py --check
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# backend/ on path
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from agent_dag import AGENT_DAG  # noqa: E402
from agent_real_behavior import ARTIFACT_PATHS  # noqa: E402
from agent_real_behavior import (
    POST_STEP_AGENTS,
    REAL_TOOL_AGENTS,
    STATE_WRITERS,
    TOOL_RUNNER_STATE_KEYS,
)
from real_agent_runner import REAL_AGENT_NAMES  # noqa: E402

_REPO_ROOT = _BACKEND.parent
_DOCS = _REPO_ROOT / "docs"
_OUT_CSV = _DOCS / "agent_audit.csv"
_OUT_JSON = _DOCS / "agent_audit.json"

_PLANNING = frozenset({"Planner", "Requirements Clarifier", "Stack Selector"})
_MEDIA_SCRAPE = frozenset({"Image Generation", "Video Generation", "Scraping Agent"})


def _deploy_kw(name: str) -> bool:
    n = name.lower()
    keys = (
        "deployment",
        "docker",
        "kubernetes",
        "github actions",
        "cdn",
        "serverless",
        "terraform",
        "ansible",
        "load balancer",
        "edge deployment",
        "disaster recovery",
        "environment configuration",
    )
    return any(k in n for k in keys)


def _automation_kw(name: str) -> bool:
    n = name.lower()
    return (
        "automation agent" in n
        or n.startswith("automation ")
        or "workflow" in n
        or "queue agent" in n
        or "cron" in n
        or "schedule" in n
        and "agent" in n
    )


def _validation_family(name: str) -> bool:
    if name in POST_STEP_AGENTS:
        return True
    if name in (
        "Code Review Agent",
        "Bundle Analyzer Agent",
        "Lighthouse Agent",
        "Dependency Audit Agent",
    ):
        return True
    if "proof" in name.lower() and "agent" in name.lower():
        return True
    return False


def primary_group(name: str) -> str:
    if name in REAL_AGENT_NAMES:
        return "real_tool_execution_agent"
    if name in _PLANNING:
        return "planning_orchestration_agent"
    if _validation_family(name):
        return "validation_proof_agent"
    if _deploy_kw(name):
        return "deploy_infra_agent"
    if _automation_kw(name):
        return "automation_run_agent"
    if name in ARTIFACT_PATHS or name in STATE_WRITERS:
        return "llm_generation_agent"
    if name in _MEDIA_SCRAPE or name in REAL_TOOL_AGENTS:
        return "llm_generation_agent"
    if name in TOOL_RUNNER_STATE_KEYS:
        return "validation_proof_agent"
    return "not_fully_integrated_agent"


def _notes(name: str, group: str) -> str:
    bits = []
    if name in ARTIFACT_PATHS:
        bits.append(f"artifact={ARTIFACT_PATHS[name]}")
    if name in STATE_WRITERS:
        bits.append(f"state_key={STATE_WRITERS[name]}")
    if name in REAL_AGENT_NAMES:
        bits.append("real_runner=1")
    if name in POST_STEP_AGENTS:
        bits.append("post_step_scan=1")
    if group == "not_fully_integrated_agent":
        bits.append(
            "no ARTIFACT_PATHS/STATE_WRITERS/primary wiring in agent_real_behavior"
        )
    return "; ".join(bits) if bits else ""


def build_rows() -> list[dict]:
    rows = []
    for name in sorted(AGENT_DAG.keys()):
        meta = AGENT_DAG[name] or {}
        deps = meta.get("depends_on") or []
        if isinstance(deps, (list, tuple)):
            dep_s = "|".join(deps)
        else:
            dep_s = str(deps)
        group = primary_group(name)
        rows.append(
            {
                "agent_name": name,
                "dag_depends_on": dep_s,
                "group": group,
                "artifact_default_path": ARTIFACT_PATHS.get(name, ""),
                "state_key": STATE_WRITERS.get(name, ""),
                "real_tool_runner": str(name in REAL_AGENT_NAMES),
                "auto_runner_step_kind": "dag_node",
                "notes": _notes(name, group),
            }
        )
    return rows


def write_outputs(rows: list[dict]) -> None:
    _DOCS.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with _OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with _OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "version": 1,
                "total_agents": len(rows),
                "counts_by_group": _count_groups(rows),
                "agents": rows,
            },
            f,
            indent=2,
        )


def _count_groups(rows: list[dict]) -> dict[str, int]:
    c: dict[str, int] = {}
    for r in rows:
        g = r["group"]
        c[g] = c.get(g, 0) + 1
    return dict(sorted(c.items(), key=lambda x: (-x[1], x[0])))


def _load_json_agents(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("agents") or []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--check",
        action="store_true",
        help="Regenerate in memory and compare counts/group keys to committed JSON (no write).",
    )
    args = ap.parse_args()
    rows = build_rows()
    if not rows:
        print("No agents found", file=sys.stderr)
        return 2
    if args.check:
        if not _OUT_JSON.exists():
            print(f"Missing {_OUT_JSON}; run without --check first.", file=sys.stderr)
            return 1
        committed = _load_json_agents(_OUT_JSON)
        by_name_c = {r["agent_name"]: r for r in committed}
        by_name_n = {r["agent_name"]: r for r in rows}
        if set(by_name_c) != set(by_name_n):
            print("Agent set mismatch vs committed JSON.", file=sys.stderr)
            return 1
        bad = []
        for name, r in by_name_n.items():
            o = by_name_c[name]
            if o.get("group") != r.get("group"):
                bad.append((name, o.get("group"), r.get("group")))
        if bad:
            for t in bad[:30]:
                print("group drift:", t, file=sys.stderr)
            print(f"{len(bad)} group mismatches (showing up to 30)", file=sys.stderr)
            return 1
        print("audit --check OK:", len(rows), "agents")
        return 0
    write_outputs(rows)
    print("Wrote", _OUT_CSV, "and", _OUT_JSON, "—", len(rows), "agents")
    print("By group:", json.dumps(_count_groups(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Discover and execute benchmark suites under proof/benchmarks/.

A suite is any subdirectory containing either:
  - run.py   — executed with `python run.py`; must print one JSON line at end:
               {"suite": "<name>", "pass": N, "fail": M, "cases": [{"id": ..., "pass": bool, "detail": ...}]}
  - cases.json — declarative list of cases; each case has
               {"id": ..., "kind": "http"|"shell", ...}
               for "http": {"method": "GET", "url": "...", "expect_status": 200}
               for "shell": {"cmd": ["...", "args"], "expect_exit": 0}

Output: writes --out with schema
  {"generated_at": "...", "suites": [...], "pass_count": int, "fail_count": int, "total": int}

Exit code is always 0 here; gating is left to gate_benchmark.py so the artifact
survives on regression for diff inspection.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = ROOT / "proof" / "benchmarks"


def run_shell_case(case: dict, cwd: str | None = None) -> dict:
    cmd = case.get("cmd") or []
    expect = case.get("expect_exit", 0)
    timeout = case.get("timeout_s", 30)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        ok = r.returncode == expect
        return {"id": case["id"], "pass": ok, "detail": {"exit": r.returncode, "stderr": r.stderr[-400:]}}
    except Exception as e:
        return {"id": case["id"], "pass": False, "detail": {"error": str(e)[:400]}}


def run_http_case(case: dict) -> dict:
    try:
        import httpx  # type: ignore
    except Exception:
        return {"id": case["id"], "pass": False, "detail": {"error": "httpx not installed"}}
    url = case["url"]
    method = case.get("method", "GET").upper()
    expect = case.get("expect_status", 200)
    timeout = case.get("timeout_s", 10)
    try:
        r = httpx.request(method, url, timeout=timeout)
        ok = r.status_code == expect
        return {"id": case["id"], "pass": ok, "detail": {"status": r.status_code}}
    except Exception as e:
        return {"id": case["id"], "pass": False, "detail": {"error": str(e)[:400]}}


def run_declarative(suite_dir: Path) -> dict:
    cases = json.loads((suite_dir / "cases.json").read_text())
    results = []
    for c in cases:
        kind = c.get("kind", "shell")
        if kind == "http":
            results.append(run_http_case(c))
        else:
            results.append(run_shell_case(c, cwd=str(suite_dir)))
    p = sum(1 for r in results if r["pass"])
    f = len(results) - p
    return {"suite": suite_dir.name, "pass": p, "fail": f, "cases": results}


def run_script_suite(suite_dir: Path) -> dict:
    runner = suite_dir / "run.py"
    try:
        r = subprocess.run(
            [sys.executable, str(runner)],
            capture_output=True, text=True, timeout=300, cwd=str(suite_dir)
        )
    except Exception as e:
        return {"suite": suite_dir.name, "pass": 0, "fail": 1,
                "cases": [{"id": "runner", "pass": False, "detail": {"error": str(e)[:400]}}]}
    # Last non-empty JSON line on stdout wins
    payload = None
    for line in reversed(r.stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            break
        except Exception:
            continue
    if not isinstance(payload, dict):
        return {"suite": suite_dir.name, "pass": 0, "fail": 1,
                "cases": [{"id": "runner", "pass": False,
                           "detail": {"error": "run.py did not emit JSON line", "stderr": r.stderr[-400:]}}]}
    payload.setdefault("suite", suite_dir.name)
    return payload


def discover_suites():
    if not BENCH_DIR.exists():
        return []
    suites = []
    for p in sorted(BENCH_DIR.iterdir()):
        if not p.is_dir():
            continue
        if (p / "cases.json").exists() or (p / "run.py").exists():
            suites.append(p)
    return suites


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    suites = []
    pass_count = 0
    fail_count = 0
    for sd in discover_suites():
        if (sd / "cases.json").exists():
            res = run_declarative(sd)
        else:
            res = run_script_suite(sd)
        suites.append(res)
        pass_count += int(res.get("pass", 0))
        fail_count += int(res.get("fail", 0))

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "suites": suites,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "total": pass_count + fail_count,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps({"pass": pass_count, "fail": fail_count, "total": pass_count + fail_count}))


if __name__ == "__main__":
    main()

"""Agent DAG audit script must stay in sync with committed manifests."""

import subprocess
import sys
from pathlib import Path


def test_audit_agent_dag_check_passes():
    backend = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, str(backend / "scripts" / "audit_agent_dag.py"), "--check"],
        cwd=str(backend),
        env={**dict(__import__("os").environ), "PYTHONPATH": str(backend)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_audit_row_count_matches_dag_import():
    from agent_dag import AGENT_DAG
    from pathlib import Path
    import json

    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / "docs" / "agent_audit.json").read_text(encoding="utf-8"))
    assert data["total_agents"] == len(AGENT_DAG)
    assert len(data["agents"]) == len(AGENT_DAG)

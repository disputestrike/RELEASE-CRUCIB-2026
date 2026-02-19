"""
Bounded autonomy loop: after main DAG, if tests or security failed, re-run once (self-heal).
Max 2 iterations (tests + security). Wired to state and execute_tool.
"""
import logging
from pathlib import Path
from typing import Any, Dict

from project_state import load_state, update_state
from tool_executor import execute_tool

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent / "workspace"


def _project_workspace(project_id: str) -> Path:
    safe_id = project_id.replace("/", "_").replace("\\", "_")
    root = WORKSPACE_ROOT / safe_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def run_bounded_autonomy_loop(
    project_id: str,
    results: Dict[str, Dict[str, Any]],
    emit_event=None,
) -> Dict[str, Any]:
    """
    After DAG: if tests or security failed, re-run once and update state.
    Returns { "ran_tests": bool, "ran_security": bool, "iterations": int }.
    """
    out = {"ran_tests": False, "ran_security": False, "iterations": 0}
    state = load_state(project_id)
    workspace = _project_workspace(project_id)

    # 1) Re-run tests if Test Executor output looked like failure
    test_out = (results.get("Test Executor") or {}).get("output") or ""
    if test_out and ("failed" in test_out.lower() or "error" in test_out.lower() or "exit 1" in test_out):
        if (workspace / "tests").exists() or (workspace / "test").exists():
            try:
                tr = execute_tool(project_id, "run", {"command": ["python", "-m", "pytest", "tests/", "-v", "--tb=short"], "timeout": 90})
                report = (tr.get("output") or tr.get("error") or "")[:10000]
                update_state(project_id, {"test_results": {"output": report, "autonomy_retry": True}})
                out["ran_tests"] = True
                out["iterations"] += 1
                if emit_event:
                    emit_event(project_id, "autonomy_retry", agent="Test Executor", message="Re-ran tests after failure")
            except Exception as e:
                logger.warning("autonomy tests retry: %s", e)
        if (workspace / "package.json").exists() and not out["ran_tests"]:
            try:
                tr = execute_tool(project_id, "run", {"command": ["npm", "test"], "timeout": 90})
                report = (tr.get("output") or tr.get("error") or "")[:10000]
                update_state(project_id, {"test_results": {"output": report, "autonomy_retry": True}})
                out["ran_tests"] = True
                out["iterations"] += 1
                if emit_event:
                    emit_event(project_id, "autonomy_retry", agent="Test Executor", message="Re-ran npm test after failure")
            except Exception as e:
                logger.warning("autonomy npm test retry: %s", e)

    # 2) Re-run security if Security Checker reported issues
    sec_out = (results.get("Security Checker") or {}).get("output") or ""
    if sec_out and ("high" in sec_out.lower() or "medium" in sec_out.lower() or "severity" in sec_out.lower()):
        try:
            tr = execute_tool(project_id, "run", {"command": ["python", "-m", "bandit", "-r", ".", "-f", "txt", "-ll"], "timeout": 60})
            report = (tr.get("output") or tr.get("error") or "")[:10000]
            update_state(project_id, {"security_report": report})
            out["ran_security"] = True
            out["iterations"] += 1
            if emit_event:
                emit_event(project_id, "autonomy_retry", agent="Security Checker", message="Re-ran security scan")
        except Exception as e:
            logger.warning("autonomy security retry: %s", e)

    return out

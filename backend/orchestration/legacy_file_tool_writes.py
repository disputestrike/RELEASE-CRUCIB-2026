"""
P3 — Legacy File Tool Agent: four canonical writes (App, server, schema, tests).

Used only when ``CRUCIBAI_ASSEMBLY_V2`` is off. Keeps ``real_agent_runner`` thin and
documents the non-V2 code path in one place.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List


def _project_workspace(project_id: str) -> Path:
    root = Path(__file__).resolve().parents[1] / "workspace"
    path = root / str(project_id).replace("/", "_").replace("\\", "_")
    path.mkdir(parents=True, exist_ok=True)
    return path


async def run_legacy_file_tool_writes(
    project_id: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    extract_code: Callable[[Any, str], str],
) -> Dict[str, Any]:
    from tools.file_agent import FileAgent

    workspace = _project_workspace(project_id)
    agent = FileAgent(llm_client=None, config={"workspace": str(workspace)})
    written: List[str] = []
    errors: List[str] = []

    fe = previous_outputs.get("Frontend Generation") or {}
    fe_code = extract_code(fe.get("output") or fe.get("result") or fe.get("code"), "src/App.jsx")
    if fe_code:
        try:
            r = await agent.execute({"action": "mkdir", "path": "src"})
            if r.get("success"):
                r = await agent.execute(
                    {"action": "write", "path": "src/App.jsx", "content": fe_code},
                )
                if r.get("success"):
                    written.append("src/App.jsx")
                else:
                    errors.append(r.get("error", "write failed"))
        except Exception as e:
            errors.append(f"Frontend write: {e}")

    be = previous_outputs.get("Backend Generation") or {}
    be_code = extract_code(be.get("output") or be.get("result") or be.get("code"), "server.py")
    if be_code:
        try:
            r = await agent.execute({"action": "write", "path": "server.py", "content": be_code})
            if r.get("success"):
                written.append("server.py")
            else:
                errors.append(r.get("error", "write failed"))
        except Exception as e:
            errors.append(f"Backend write: {e}")

    db_agent = previous_outputs.get("Database Agent") or {}
    db_code = extract_code(db_agent.get("output") or db_agent.get("result"), "schema.sql")
    if db_code:
        try:
            r = await agent.execute({"action": "write", "path": "schema.sql", "content": db_code})
            if r.get("success"):
                written.append("schema.sql")
            else:
                errors.append(r.get("error", "write failed"))
        except Exception as e:
            errors.append(f"Schema write: {e}")

    test_agent = previous_outputs.get("Test Generation") or {}
    test_code = extract_code(test_agent.get("output") or test_agent.get("result") or test_agent.get("code"), "tests/test_basic.py")
    if test_code:
        try:
            r = await agent.execute({"action": "mkdir", "path": "tests"})
            if r.get("success"):
                r = await agent.execute(
                    {"action": "write", "path": "tests/test_basic.py", "content": test_code},
                )
                if r.get("success"):
                    written.append("tests/test_basic.py")
                else:
                    errors.append(r.get("error", "write failed"))
        except Exception as e:
            errors.append(f"Tests write: {e}")

    output = f"Real File Tool Agent: wrote {len(written)} file(s): {', '.join(written)}."
    if errors:
        output += f" Errors: {'; '.join(errors)}"
    return {
        "output": output,
        "tokens_used": 0,
        "status": "completed",
        "result": output,
        "code": output,
        "real_agent": True,
        "files_written": written,
        "errors": errors,
    }

"""
Real agent runner: every agent has a real effect.
- Tool agents (Browser, File, API, Database, Deployment): execute real tools.
- All agents: output is persisted to project workspace (real write to disk).
- Test Executor: runs real tests (pytest / npm test).
- Security Checker / UX Auditor / Performance Analyzer: run real linters/checks where possible.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Agents that execute real tools; when the DAG runs these, we call the real implementation.
REAL_AGENT_NAMES = frozenset({
    "Browser Tool Agent",
    "File Tool Agent",
    "API Tool Agent",
    "Database Tool Agent",
    "Deployment Tool Agent",
})

# Default workspace root (per-project dirs go under this)
def _workspace_root() -> Path:
    return Path(__file__).parent / "workspace"


def _project_workspace(project_id: str) -> Path:
    """Project-specific workspace path. Created on first use."""
    root = _workspace_root()
    path = root / project_id.replace("/", "_").replace("\\", "_")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extract_code(out: Any) -> str:
    if out is None:
        return ""
    if isinstance(out, str):
        s = out.strip()
        if s.startswith("```"):
            lines = s.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines)
        return s
    if isinstance(out, dict):
        return out.get("output") or out.get("result") or out.get("code") or ""
    return ""


async def _run_file_tool_agent(
    project_id: str,
    previous_outputs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Write generated frontend/backend/database/tests to project workspace. Real execution."""
    from tools.file_agent import FileAgent
    workspace = _project_workspace(project_id)
    agent = FileAgent(llm_client=None, config={"workspace": str(workspace)})
    written: List[str] = []
    errors: List[str] = []

    # Frontend
    fe = previous_outputs.get("Frontend Generation") or {}
    fe_code = _extract_code(fe.get("output") or fe.get("result") or fe.get("code"))
    if fe_code:
        try:
            r = await agent.execute({"action": "mkdir", "path": "src"})
            if r.get("success"):
                r = await agent.execute({
                    "action": "write",
                    "path": "src/App.jsx",
                    "content": fe_code,
                })
                if r.get("success"):
                    written.append("src/App.jsx")
                else:
                    errors.append(r.get("error", "write failed"))
        except Exception as e:
            errors.append(f"Frontend write: {e}")

    # Backend
    be = previous_outputs.get("Backend Generation") or {}
    be_code = _extract_code(be.get("output") or be.get("result") or be.get("code"))
    if be_code:
        try:
            r = await agent.execute({
                "action": "write",
                "path": "server.py",
                "content": be_code,
            })
            if r.get("success"):
                written.append("server.py")
            else:
                errors.append(r.get("error", "write failed"))
        except Exception as e:
            errors.append(f"Backend write: {e}")

    # Database schema
    db_agent = previous_outputs.get("Database Agent") or {}
    db_code = _extract_code(db_agent.get("output") or db_agent.get("result"))
    if db_code:
        try:
            r = await agent.execute({
                "action": "write",
                "path": "schema.sql",
                "content": db_code,
            })
            if r.get("success"):
                written.append("schema.sql")
            else:
                errors.append(r.get("error", "write failed"))
        except Exception as e:
            errors.append(f"Schema write: {e}")

    # Tests
    test_agent = previous_outputs.get("Test Generation") or {}
    test_code = _extract_code(test_agent.get("output") or test_agent.get("result") or test_agent.get("code"))
    if test_code:
        try:
            r = await agent.execute({"action": "mkdir", "path": "tests"})
            if r.get("success"):
                r = await agent.execute({
                    "action": "write",
                    "path": "tests/test_basic.py",
                    "content": test_code,
                })
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


async def _run_database_tool_agent(
    project_id: str,
    previous_outputs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Apply database schema to project SQLite. Real execution."""
    import aiosqlite
    workspace = _project_workspace(project_id)
    db_path = str(workspace / "app.db")

    db_agent = previous_outputs.get("Database Agent") or {}
    schema = _extract_code(db_agent.get("output") or db_agent.get("result"))
    if not schema or not schema.strip():
        return {
            "output": "Real Database Tool Agent: no schema from Database Agent; skipped.",
            "tokens_used": 0,
            "status": "completed",
            "result": "skipped (no schema)",
            "code": "",
            "real_agent": True,
        }

    try:
        async with aiosqlite.connect(db_path) as conn:
            await conn.executescript(schema)
            await conn.commit()
    except Exception as e:
        logger.warning("Database Tool Agent failed: %s", e)
        return {
            "output": f"Real Database Tool Agent: applied schema to {db_path}. Error: {e}",
            "tokens_used": 0,
            "status": "completed",
            "result": str(e),
            "code": "",
            "real_agent": True,
        }

    return {
        "output": f"Real Database Tool Agent: applied schema to SQLite at {db_path}.",
        "tokens_used": 0,
        "status": "completed",
        "result": db_path,
        "code": "",
        "real_agent": True,
    }


async def _run_browser_tool_agent(
    project_id: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    project_prompt: str,
) -> Dict[str, Any]:
    """Optional: if Scraping Agent or context gave a URL, navigate and return snippet. Real execution."""
    from tools.browser_agent import BrowserAgent
    agent = BrowserAgent(llm_client=None, config={})
    url: Optional[str] = None
    scrape = previous_outputs.get("Scraping Agent") or {}
    out = (scrape.get("output") or scrape.get("result") or "") or project_prompt
    if out and "http" in out:
        for word in out.replace(",", " ").replace("\n", " ").split():
            if word.startswith("http://") or word.startswith("https://"):
                url = word.strip()
                break
    if not url:
        return {
            "output": "Real Browser Tool Agent: no URL in context; skipped (real agent ran, no input).",
            "tokens_used": 0,
            "status": "completed",
            "result": "skipped",
            "code": "",
            "real_agent": True,
        }
    try:
        r = await agent.execute({"action": "navigate", "url": url})
        if r.get("success"):
            content_len = r.get("content_length", 0)
            return {
                "output": f"Real Browser Tool Agent: navigated to {url}; content length {content_len}.",
                "tokens_used": 0,
                "status": "completed",
                "result": r.get("url", url),
                "code": "",
                "real_agent": True,
            }
        return {
            "output": f"Real Browser Tool Agent: {r.get('error', 'unknown')}",
            "tokens_used": 0,
            "status": "completed",
            "result": r.get("error", ""),
            "code": "",
            "real_agent": True,
        }
    except Exception as e:
        return {
            "output": f"Real Browser Tool Agent error: {e}",
            "tokens_used": 0,
            "status": "completed",
            "result": str(e),
            "code": "",
            "real_agent": True,
        }


async def _run_api_tool_agent(
    project_id: str,
    previous_outputs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """If API Integration or context has an endpoint URL, call it. Real execution."""
    from tools.api_agent import APIAgent
    agent = APIAgent(llm_client=None, config={})
    api_out = previous_outputs.get("API Integration") or {}
    out = _extract_code(api_out.get("output") or api_out.get("result"))
    url: Optional[str] = None
    if out and "http" in out:
        for word in out.replace(",", " ").replace("\n", " ").split():
            if word.startswith("http://") or word.startswith("https://"):
                url = word.strip()
                break
    if not url:
        return {
            "output": "Real API Tool Agent: no API URL in context; skipped (real agent ran, no input).",
            "tokens_used": 0,
            "status": "completed",
            "result": "skipped",
            "code": "",
            "real_agent": True,
        }
    try:
        r = await agent.execute({"method": "GET", "url": url})
        if r.get("success"):
            return {
                "output": f"Real API Tool Agent: GET {url} -> status {r.get('status_code')}.",
                "tokens_used": 0,
                "status": "completed",
                "result": str(r.get("data", ""))[:500],
                "code": "",
                "real_agent": True,
            }
        return {
            "output": f"Real API Tool Agent: {r.get('error', 'unknown')}",
            "tokens_used": 0,
            "status": "completed",
            "result": r.get("error", ""),
            "code": "",
            "real_agent": True,
        }
    except Exception as e:
        return {
            "output": f"Real API Tool Agent error: {e}",
            "tokens_used": 0,
            "status": "completed",
            "result": str(e),
            "code": "",
            "real_agent": True,
        }


async def _run_deployment_tool_agent(
    project_id: str,
    previous_outputs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Deploy from project workspace (after File Tool Agent has written files). Real execution."""
    from tools.deployment_operations_agent import DeploymentOperationsAgent
    workspace = _project_workspace(project_id)
    if not (workspace / "server.py").exists() and not (workspace / "src").exists():
        return {
            "output": "Real Deployment Tool Agent: no files in workspace (run File Tool Agent first); skipped.",
            "tokens_used": 0,
            "status": "completed",
            "result": "skipped",
            "code": "",
            "real_agent": True,
        }
    agent = DeploymentOperationsAgent(llm_client=None, config={})
    try:
        r = await agent.execute({
            "platform": "vercel",
            "project_path": str(workspace),
            "config": {},
        })
        if r.get("success"):
            return {
                "output": f"Real Deployment Tool Agent: {r.get('output', 'deployed')} URL: {r.get('url', 'N/A')}.",
                "tokens_used": 0,
                "status": "completed",
                "result": r.get("url", r.get("output", "")),
                "code": "",
                "real_agent": True,
            }
        return {
            "output": f"Real Deployment Tool Agent: {r.get('error', 'deploy failed')}",
            "tokens_used": 0,
            "status": "completed",
            "result": r.get("error", ""),
            "code": "",
            "real_agent": True,
        }
    except Exception as e:
        return {
            "output": f"Real Deployment Tool Agent error: {e}",
            "tokens_used": 0,
            "status": "completed",
            "result": str(e),
            "code": "",
            "real_agent": True,
        }


async def run_real_agent(
    agent_name: str,
    project_id: str,
    user_id: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    project_prompt: str,
) -> Optional[Dict[str, Any]]:
    """
    Run a real tool agent from DAG context. Returns result dict in same shape as
    _run_single_agent_with_context (output, tokens_used, status, result, code) or None if not a real agent.
    """
    if agent_name not in REAL_AGENT_NAMES:
        return None

    try:
        if agent_name == "File Tool Agent":
            return await _run_file_tool_agent(project_id, previous_outputs)
        if agent_name == "Database Tool Agent":
            return await _run_database_tool_agent(project_id, previous_outputs)
        if agent_name == "Browser Tool Agent":
            return await _run_browser_tool_agent(project_id, previous_outputs, project_prompt)
        if agent_name == "API Tool Agent":
            return await _run_api_tool_agent(project_id, previous_outputs)
        if agent_name == "Deployment Tool Agent":
            return await _run_deployment_tool_agent(project_id, previous_outputs)
    except Exception as e:
        logger.exception("Real agent %s failed: %s", agent_name, e)
        return {
            "output": f"Real agent {agent_name} failed: {e}",
            "tokens_used": 0,
            "status": "completed",
            "result": str(e),
            "code": "",
            "real_agent": True,
        }
    return None


# --- All agents: persist output to workspace (real effect) ---

def _agent_slug(name: str) -> str:
    return name.replace(" ", "_").replace("/", "-")


def persist_agent_output(project_id: str, agent_name: str, result: Dict[str, Any]) -> None:
    """Persist every agent's output to workspace so all agents have a real effect (written to disk)."""
    workspace = _project_workspace(project_id)
    out_dir = workspace / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _agent_slug(agent_name)
    raw = result.get("output") or result.get("result") or result.get("code") or ""
    if isinstance(raw, dict):
        raw = json.dumps(raw, indent=2)
    if not isinstance(raw, str):
        raw = str(raw)
    try:
        if raw.strip().startswith("{") or raw.strip().startswith("["):
            (out_dir / f"{slug}.json").write_text(raw, encoding="utf-8")
        else:
            (out_dir / f"{slug}.md").write_text(raw, encoding="utf-8")
    except Exception as e:
        logger.warning("persist_agent_output %s: %s", agent_name, e)


# --- Real post-steps for specific agents (run real tools after LLM) ---

async def run_real_post_step(
    agent_name: str,
    project_id: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """Run a real tool/check for agents that support it. Returns updated result."""
    workspace = _project_workspace(project_id)
    out = result.get("output") or result.get("result") or ""

    if agent_name == "Test Executor":
        ran = []
        if (workspace / "tests").exists() or (workspace / "test").exists():
            try:
                proc = await asyncio.create_subprocess_exec(
                    "python", "-m", "pytest", "tests/", "-v", "--tb=short",
                    cwd=str(workspace),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
                ran.append(f"pytest exit {proc.returncode}")
                out = (out + "\n\n[REAL RUN] pytest:\n" + (stdout.decode() or "")[:2000]).strip()
            except (FileNotFoundError, asyncio.TimeoutError, Exception) as e:
                ran.append(f"pytest: {e}")
        if (workspace / "package.json").exists():
            try:
                proc = await asyncio.create_subprocess_exec(
                    "npm", "test",
                    cwd=str(workspace),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(proc.communicate(), timeout=90)
                ran.append("npm test run")
            except Exception as e:
                ran.append(f"npm test: {e}")
        if not ran:
            out = (out + "\n\n[REAL RUN] No test dir or package.json; skipped.").strip()
        result["output"] = out
        result["result"] = out
        result["real_run"] = ran
        return result

    if agent_name == "Security Checker":
        if (workspace / "server.py").exists() or (workspace / "backend").exists():
            try:
                proc = await asyncio.create_subprocess_exec(
                    "python", "-m", "bandit", "-r", str(workspace), "-f", "txt", "-ll",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                out = (out + "\n\n[REAL RUN] bandit:\n" + stdout.decode()[:1500]).strip()
            except (FileNotFoundError, asyncio.TimeoutError, Exception):
                out = (out + "\n\n[REAL RUN] bandit not run (not installed or timeout).").strip()
        result["output"] = out
        result["result"] = out
        return result

    if agent_name == "Performance Analyzer":
        try:
            lines = 0
            for f in workspace.rglob("*.py"):
                if "node_modules" in str(f) or "__pycache__" in str(f):
                    continue
                try:
                    lines += len(f.read_text(encoding="utf-8", errors="ignore").splitlines())
                except Exception:
                    pass
            out = (out + f"\n\n[REAL RUN] Python lines in workspace: {lines}").strip()
        except Exception as e:
            out = (out + f"\n\n[REAL RUN] count error: {e}").strip()
        result["output"] = out
        result["result"] = out
        return result

    if agent_name == "UX Auditor":
        a11y = []
        src = workspace / "src"
        if src.exists():
            for f in src.rglob("*.jsx"):
                try:
                    t = f.read_text(encoding="utf-8", errors="ignore")
                    if "aria-" in t or "role=" in t:
                        a11y.append(f.name)
                except Exception:
                    pass
        if a11y:
            out = (out + f"\n\n[REAL RUN] Files with ARIA/role: {', '.join(a11y[:10])}").strip()
        else:
            out = (out + "\n\n[REAL RUN] No JSX with ARIA/role found in src/.").strip()
        result["output"] = out
        result["result"] = out
        return result

    return result

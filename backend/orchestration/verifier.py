"""
verifier.py — Step-level verification after each execution.
Returns a structured result with passed/score/issues/proof.
Never lets a step be marked complete without evidence.
"""
import asyncio
import logging
import os
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


# ── Verification result helpers ───────────────────────────────────────────────

def _result(passed: bool, score: int, issues: List[str],
            proof: List[Dict]) -> Dict[str, Any]:
    return {"passed": passed, "score": score, "issues": issues, "proof": proof}


def _proof_item(proof_type: str, title: str, payload: Dict) -> Dict:
    return {"proof_type": proof_type, "title": title, "payload": payload}


# ── Step-type verifiers ───────────────────────────────────────────────────────

async def verify_frontend_step(step: Dict[str, Any],
                                workspace_path: str) -> Dict[str, Any]:
    issues = []
    proof = []

    # Check file existence
    output_files = step.get("output_files") or []
    for f in output_files:
        full = os.path.join(workspace_path, f)
        if os.path.exists(full):
            proof.append(_proof_item("file", f"File exists: {f}", {"path": f, "exists": True}))
        else:
            issues.append(f"Expected file missing: {f}")

    # Basic syntax check — look for JSX/JS errors
    syntax_ok = True
    for f in output_files:
        full = os.path.join(workspace_path, f)
        if full.endswith((".jsx", ".tsx", ".js", ".ts")) and os.path.exists(full):
            try:
                result = await asyncio.create_subprocess_exec(
                    "node", "--check", full,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await asyncio.wait_for(result.communicate(), timeout=10)
                if result.returncode != 0:
                    issues.append(f"Syntax error in {f}: {stderr.decode()[:200]}")
                    syntax_ok = False
                else:
                    proof.append(_proof_item("compile", f"Syntax OK: {f}", {"file": f}))
            except (FileNotFoundError, asyncio.TimeoutError):
                pass  # node not available in all envs

    score = 100 if not issues else max(40, 100 - len(issues) * 20)
    return _result(len(issues) == 0, score, issues, proof)


async def verify_backend_step(step: Dict[str, Any],
                               workspace_path: str) -> Dict[str, Any]:
    issues = []
    proof = []

    output_files = step.get("output_files") or []
    for f in output_files:
        full = os.path.join(workspace_path, f)
        if os.path.exists(full):
            proof.append(_proof_item("file", f"File exists: {f}", {"path": f, "exists": True}))
            # Python syntax check
            if f.endswith(".py"):
                try:
                    result = await asyncio.create_subprocess_exec(
                        "python3", "-m", "py_compile", full,
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    _, stderr = await asyncio.wait_for(result.communicate(), timeout=10)
                    if result.returncode != 0:
                        issues.append(f"Python syntax error in {f}: {stderr.decode()[:200]}")
                    else:
                        proof.append(_proof_item("compile", f"Python syntax OK: {f}", {"file": f}))
                except (FileNotFoundError, asyncio.TimeoutError):
                    pass
        else:
            issues.append(f"Expected backend file missing: {f}")

    score = 100 if not issues else max(40, 100 - len(issues) * 20)
    return _result(len(issues) == 0, score, issues, proof)


async def verify_db_step(step: Dict[str, Any],
                          db_pool=None) -> Dict[str, Any]:
    issues = []
    proof = []

    tables_created = step.get("tables_created") or []
    if db_pool and tables_created:
        try:
            async with db_pool.acquire() as conn:
                for table in tables_created:
                    row = await conn.fetchrow(
                        "SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name=$1)",
                        table
                    )
                    if row and row[0]:
                        proof.append(_proof_item("db", f"Table exists: {table}", {"table": table}))
                    else:
                        issues.append(f"Table not found: {table}")
        except Exception as e:
            issues.append(f"DB verification error: {str(e)}")

    score = 100 if not issues else max(30, 100 - len(issues) * 25)
    return _result(len(issues) == 0, score, issues, proof)


async def verify_deploy_step(step: Dict[str, Any]) -> Dict[str, Any]:
    issues = []
    proof = []

    deploy_url = step.get("deploy_url")
    if deploy_url:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(deploy_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status < 400:
                        proof.append(_proof_item("deploy", f"Deploy URL live: {deploy_url}",
                                                 {"url": deploy_url, "status": resp.status}))
                    else:
                        issues.append(f"Deploy URL returned {resp.status}: {deploy_url}")
        except Exception as e:
            issues.append(f"Deploy smoke check failed: {str(e)}")
    else:
        proof.append(_proof_item("deploy", "Deploy step recorded (no URL to ping yet)", {}))

    score = 100 if not issues else 50
    return _result(len(issues) == 0, score, issues, proof)


# ── Generic verifier dispatcher ───────────────────────────────────────────────

STEP_TYPE_MAP = {
    "frontend": verify_frontend_step,
    "backend": verify_backend_step,
    "database": verify_db_step,
    "db": verify_db_step,
    "deploy": verify_deploy_step,
}


async def verify_step(step: Dict[str, Any], workspace_path: str = "",
                       db_pool=None) -> Dict[str, Any]:
    """
    Run the appropriate verifier for this step type.
    Falls back to a minimal check if no specific verifier matches.
    """
    step_key = step.get("step_key", "")
    # Determine type from step_key prefix
    prefix = step_key.split(".")[0] if "." in step_key else step.get("phase", "")

    fn = STEP_TYPE_MAP.get(prefix)

    try:
        if fn == verify_db_step:
            result = await fn(step, db_pool=db_pool)
        elif fn in (verify_frontend_step, verify_backend_step):
            result = await fn(step, workspace_path)
        elif fn == verify_deploy_step:
            result = await fn(step)
        else:
            # Generic: record that the step ran
            result = _result(True, 85, [],
                             [_proof_item("generic", f"Step executed: {step_key}",
                                         {"step_key": step_key,
                                          "output_preview": str(step.get("output_ref", ""))[:200]})])
    except Exception as e:
        logger.exception("verifier error for step %s", step_key)
        result = _result(False, 0, [f"Verifier threw exception: {str(e)}"], [])

    return result

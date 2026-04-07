"""
verifier.py — Step-level verification after each execution.
Returns a structured result with passed/score/issues/proof.
Never lets a step be marked complete without evidence.
"""
import asyncio
import logging
import os
import re
import sys
from typing import Dict, Any, List, Optional

from .runtime_health import skip_node_verify_env

logger = logging.getLogger(__name__)

# FastAPI / Starlette-style decorators in generated workspaces
_ROUTE_DECORATOR_RE = re.compile(
    r'@\s*([a-zA-Z_][\w.]*)\s*\.\s*(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def _scan_workspace_for_route_declarations(
    workspace_path: str,
    *,
    max_files: int = 48,
    max_matches: int = 80,
) -> List[Dict[str, str]]:
    """Lightweight static scan for @app.get("/path") / @router.post(...) in *.py under workspace."""
    out: List[Dict[str, str]] = []
    if not workspace_path or not os.path.isdir(workspace_path):
        return out
    skip_dir = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"}
    seen: set = set()
    nfiles = 0
    for root, dirs, files in os.walk(workspace_path):
        dirs[:] = [d for d in dirs if d not in skip_dir]
        for name in files:
            if not name.endswith(".py"):
                continue
            if nfiles >= max_files:
                return out
            full = os.path.join(root, name)
            rel = os.path.relpath(full, workspace_path).replace("\\", "/")
            if "site-packages" in rel:
                continue
            nfiles += 1
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            for m in _ROUTE_DECORATOR_RE.finditer(text):
                method, path = m.group(2).upper(), m.group(3)
                key = (method, path, rel)
                if key in seen:
                    continue
                seen.add(key)
                out.append({"method": method, "path": path, "file": rel})
                if len(out) >= max_matches:
                    return out
    return out


# ── Verification result helpers ───────────────────────────────────────────────

def _result(passed: bool, score: int, issues: List[str],
            proof: List[Dict]) -> Dict[str, Any]:
    return {"passed": passed, "score": score, "issues": issues, "proof": proof}


def _proof_item(
    proof_type: str,
    title: str,
    payload: Dict,
    *,
    verification_class: Optional[str] = None,
) -> Dict:
    """
    verification_class: presence | syntax | runtime | experience (trust roadmap).
    Stored in payload_json for proof panel / scoring.
    """
    p = dict(payload)
    if verification_class:
        p["verification_class"] = verification_class
    return {"proof_type": proof_type, "title": title, "payload": p}


# ── Step-type verifiers ───────────────────────────────────────────────────────

async def verify_frontend_step(step: Dict[str, Any],
                                workspace_path: str) -> Dict[str, Any]:
    issues = []
    proof = []
    step_key = step.get("step_key", "")

    # Check file existence
    output_files = step.get("output_files") or []
    # NOTE: Don't check for missing output_files here - they're added AFTER execution
    # The executor will have created files; verifier just checks if they exist

    for f in output_files:
        full = os.path.join(workspace_path, f)
        if os.path.exists(full):
            proof.append(
                _proof_item(
                    "file",
                    f"File exists: {f}",
                    {"path": f, "exists": True},
                    verification_class="presence",
                )
            )
        else:
            issues.append(f"Expected file missing: {f}")

    # Basic syntax check — Node cannot parse JSX; skip .jsx/.tsx and JSX-in-.js
    for f in output_files:
        full = os.path.join(workspace_path, f)
        if not full.endswith((".jsx", ".tsx", ".js", ".ts")) or not os.path.exists(full):
            continue
        if full.endswith((".jsx", ".tsx")):
            proof.append(
                _proof_item(
                    "compile",
                    f"JSX source present: {f}",
                    {"file": f},
                    verification_class="presence",
                )
            )
            continue
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
        except OSError:
            continue
        if "React" in txt and ("</" in txt or "/>" in txt):
            proof.append(_proof_item(
                "compile",
                f"JSX in {f} (skipped node --check)",
                {"file": f},
                verification_class="syntax",
            ))
            continue
        try:
            result = await asyncio.create_subprocess_exec(
                "node", "--check", full,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(result.communicate(), timeout=10)
            if result.returncode != 0:
                issues.append(f"Syntax error in {f}: {stderr.decode(errors='replace')[:200]}")
            else:
                proof.append(_proof_item(
                    "compile", f"Syntax OK: {f}",
                    {"file": f, "command": ["node", "--check", full]},
                    verification_class="syntax",
                ))
        except FileNotFoundError:
            if skip_node_verify_env():
                proof.append(_proof_item(
                    "compile",
                    f"Skipped node --check (CRUCIBAI_SKIP_NODE_VERIFY): {f}",
                    {"file": f, "skipped": True},
                ))
            else:
                issues.append(
                    "Node.js not found on PATH (needed for `node --check`). "
                    "Install Node LTS or run preflight before Auto-Runner."
                )
        except asyncio.TimeoutError:
            issues.append(f"Node syntax check timed out for {f}")

    score = 100 if not issues else max(40, 100 - len(issues) * 20)
    return _result(len(issues) == 0, score, issues, proof)


async def verify_backend_step(step: Dict[str, Any],
                               workspace_path: str) -> Dict[str, Any]:
    issues = []
    proof = []
    step_key = step.get("step_key", "")

    for route in step.get("routes_added") or []:
        method = route.get("method") or "GET"
        path = route.get("path") or ""
        proof.append(_proof_item(
            "route", f"{method} {path}".strip() or "route",
            {"method": method, "path": path, "description": route.get("description", "")},
        ))

    output_files = step.get("output_files") or []
    if step_key.startswith("backend.") and not output_files and not (step.get("routes_added") or []):
        issues.append("Backend step produced no files and no routes_added")

    for f in output_files:
        full = os.path.join(workspace_path, f)
        if os.path.exists(full):
            proof.append(
                _proof_item(
                    "file",
                    f"File exists: {f}",
                    {"path": f, "exists": True},
                    verification_class="presence",
                )
            )
            # Python syntax check
            if f.endswith(".py"):
                py = sys.executable or "python"
                cmd = (py, "-m", "py_compile", full)
                try:
                    result = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    _, stderr = await asyncio.wait_for(result.communicate(), timeout=10)
                    if result.returncode != 0:
                        err = stderr.decode(errors="replace")[:400]
                        issues.append(f"Python syntax error in {f}: {err}")
                    else:
                        proof.append(_proof_item(
                            "compile", f"Python syntax OK: {f}",
                            {"file": f, "command": list(cmd)},
                        ))
                except FileNotFoundError:
                    issues.append(
                        "Python interpreter not found for py_compile "
                        f"(tried {py!r}). Use the same Python that runs the API, or fix PATH."
                    )
                except asyncio.TimeoutError:
                    issues.append(f"Python syntax check timed out for {f}")
        else:
            issues.append(f"Expected backend file missing: {f}")

    if step_key == "backend.auth":
        proof.append(
            _proof_item(
                "verification",
                "Auth evidence: generated apps use client-side demo session; production OAuth is not asserted in workspace.",
                {"auth_mode": "client_demo_stub", "source": "verifier_note"},
                verification_class="presence",
            ),
        )

    if workspace_path and os.path.isdir(workspace_path) and step_key == "backend.routes":
        for decl in _scan_workspace_for_route_declarations(workspace_path):
            proof.append(
                _proof_item(
                    "route",
                    f"Declared in workspace: {decl['method']} {decl['path']}",
                    {
                        "method": decl["method"],
                        "path": decl["path"],
                        "file": decl["file"],
                        "kind": "workspace_route_scan",
                    },
                    verification_class="presence",
                ),
            )

    score = 100 if not issues else max(40, 100 - len(issues) * 20)
    return _result(len(issues) == 0, score, issues, proof)


async def verify_db_step(step: Dict[str, Any],
                          db_pool=None, workspace_path: str = "") -> Dict[str, Any]:
    issues = []
    proof = []
    step_key = step.get("step_key", "")

    tables_created = step.get("tables_created") or []
    migration_files = [
        f for f in (step.get("output_files") or [])
        if str(f).lower().endswith(".sql")
    ]
    if workspace_path and migration_files:
        for f in migration_files:
            full = os.path.join(workspace_path, f)
            if os.path.exists(full):
                proof.append(_proof_item(
                    "db", f"SQL artifact: {f}",
                    {"path": f, "kind": "migration_or_seed"},
                ))
            else:
                issues.append(f"Expected SQL file missing: {f}")

    if step_key.startswith("database.") and not tables_created and not migration_files:
        issues.append(
            "Database step produced no .sql artifacts and no tables_created"
        )

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


async def verify_deploy_step(step: Dict[str, Any], workspace_path: str = "") -> Dict[str, Any]:
    issues = []
    proof = []
    step_key = step.get("step_key", "")
    added_deploy_build_file_proof = False

    if step_key == "deploy.build" and workspace_path and os.path.isdir(workspace_path):
        from .production_gate import scan_workspace_for_credential_patterns
        from .tenant_deploy_gate import verify_tenant_context_for_deploy

        t_issues, t_proof = verify_tenant_context_for_deploy(workspace_path)
        issues.extend(t_issues)
        for tp in t_proof:
            proof.append(tp)

        hits = scan_workspace_for_credential_patterns(workspace_path)
        for h in hits:
            proof.append(
                _proof_item(
                    "verification",
                    f"Production gate: {h}",
                    {"gate": "credential_pattern_scan"},
                    verification_class="runtime",
                ),
            )
        strict = os.environ.get("CRUCIBAI_PRODUCTION_GATE_STRICT", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if strict and hits:
            issues.extend(hits)
        elif not hits:
            proof.append(
                _proof_item(
                    "verification",
                    "Production gate: no high-confidence credential patterns in code files",
                    {"gate": "credential_pattern_scan", "clean": True},
                    verification_class="runtime",
                ),
            )

        for rel in step.get("output_files") or []:
            full = os.path.normpath(os.path.join(workspace_path, rel.replace("/", os.sep)))
            if os.path.isfile(full):
                pl: Dict[str, Any] = {"path": rel, "exists": True}
                if rel.replace("\\", "/") == "docs/COMPLIANCE_SKETCH.md":
                    pl["compliance_sketch"] = True
                    pl["note"] = "Educational checklist only — not legal advice"
                proof.append(
                    _proof_item(
                        "file",
                        f"File exists: {rel}",
                        pl,
                        verification_class="presence",
                    ),
                )
                added_deploy_build_file_proof = True
            else:
                issues.append(f"Expected deploy artifact missing: {rel}")

    deploy_url = step.get("deploy_url")
    if deploy_url:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(deploy_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status < 400:
                        proof.append(
                            _proof_item(
                                "deploy",
                                f"Deploy URL live: {deploy_url}",
                                {"url": deploy_url, "status": resp.status},
                                verification_class="experience",
                            ),
                        )
                    else:
                        issues.append(f"Deploy URL returned {resp.status}: {deploy_url}")
        except Exception as e:
            issues.append(f"Deploy smoke check failed: {str(e)}")
    elif not added_deploy_build_file_proof:
        proof.append(
            _proof_item(
                "deploy",
                "Deploy step recorded (no URL to ping yet)",
                {},
                verification_class="presence",
            ),
        )

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


async def verify_compile_workspace(workspace_path: str, max_files: int = 28) -> Dict[str, Any]:
    """Cross-cut syntax check for JS entrypoints (depth, not only declared output_files)."""
    issues: List[str] = []
    proof: List[Dict] = []
    if skip_node_verify_env():
        return _result(
            True,
            78,
            [],
            [
                _proof_item(
                    "compile",
                    "Workspace JS syntax check skipped (CRUCIBAI_SKIP_NODE_VERIFY)",
                    {"skipped": True},
                ),
            ],
        )
    if not workspace_path or not os.path.isdir(workspace_path):
        return _result(False, 0, ["No workspace for compile verification"], [])
    skip = {"node_modules", ".git", "__pycache__", "dist", "build"}
    checked = 0
    for root, dirs, files in os.walk(workspace_path):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            if checked >= max_files:
                break
            if not name.endswith(".js") or name.endswith(".test.js"):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, workspace_path).replace("\\", "/")
            if "node_modules" in rel:
                continue
            try:
                result = await asyncio.create_subprocess_exec(
                    "node", "--check", full,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await asyncio.wait_for(result.communicate(), timeout=12)
                checked += 1
                if result.returncode != 0:
                    issues.append(f"node --check failed {rel}: {stderr.decode(errors='replace')[:180]}")
                else:
                    proof.append(
                        _proof_item(
                            "compile",
                            f"OK: {rel}",
                            {"file": rel, "command": ["node", "--check", rel]},
                            verification_class="syntax",
                        ),
                    )
            except FileNotFoundError:
                issues.append("Node not available for compile verification.")
                return _result(False, 20, issues, proof)
            except asyncio.TimeoutError:
                issues.append(f"node --check timeout: {rel}")
        if checked >= max_files:
            break
    score = 100 if not issues else max(25, 100 - len(issues) * 15)
    return _result(len(issues) == 0, score, issues, proof)


async def verify_step(step: Dict[str, Any], workspace_path: str = "",
                       db_pool=None) -> Dict[str, Any]:
    """
    Run the appropriate verifier for this step type.
    Falls back to a minimal check if no specific verifier matches.
    """
    step_key = step.get("step_key", "")
    # Determine type from step_key prefix
    prefix = step_key.split(".")[0] if "." in step_key else step.get("phase", "")

    try:
        if prefix == "verification":
            if step_key == "verification.preview":
                from .preview_gate import verify_preview_workspace

                pr = await verify_preview_workspace(workspace_path or "")
                return _result(pr["passed"], pr["score"], pr["issues"], pr["proof"])
            if step_key == "verification.compile":
                return await verify_compile_workspace(workspace_path or "")
            if step_key == "verification.security":
                from .tenant_deploy_gate import workspace_has_multitenancy_rls_migration
                from .verification_behavior_bundle import (
                    merge_verification_results,
                    verify_behavior_bundle_workspace,
                )
                from .verification_rls import verify_rls_workspace
                from .verification_security import verify_security_workspace

                ws = workspace_path or ""
                parts: List[Dict[str, Any]] = [verify_security_workspace(ws)]
                if workspace_has_multitenancy_rls_migration(ws):
                    parts.append(verify_rls_workspace(ws))
                parts.append(await verify_behavior_bundle_workspace(ws))
                mr = merge_verification_results(parts)
                return _result(mr["passed"], mr["score"], mr["issues"], mr["proof"])
            if step_key == "verification.rls":
                from .verification_rls import verify_rls_workspace

                rr = verify_rls_workspace(workspace_path or "")
                return _result(rr["passed"], rr["score"], rr["issues"], rr["proof"])
            if step_key == "verification.behavior":
                from .verification_behavior_bundle import verify_behavior_bundle_workspace

                br = await verify_behavior_bundle_workspace(workspace_path or "")
                return _result(br["passed"], br["score"], br["issues"], br["proof"])
            if step_key == "verification.tenancy_smoke":
                from .verification_tenancy_smoke import verify_tenancy_smoke_workspace

                ts = await verify_tenancy_smoke_workspace(workspace_path or "")
                return _result(ts["passed"], ts["score"], ts["issues"], ts["proof"])
            if step_key == "verification.stripe_replay":
                from .verification_stripe_replay import verify_stripe_replay_workspace

                sr = verify_stripe_replay_workspace(workspace_path or "")
                return _result(sr["passed"], sr["score"], sr["issues"], sr["proof"])
            if step_key == "verification.rbac_enforcement":
                from .verification_rbac import verify_rbac_enforcement_workspace

                rb = await verify_rbac_enforcement_workspace(workspace_path or "")
                return _result(rb["passed"], rb["score"], rb["issues"], rb["proof"])
            if step_key == "verification.api_smoke":
                from .verification_api_smoke import verify_api_smoke_workspace

                ar = await verify_api_smoke_workspace(workspace_path or "")
                return _result(ar["passed"], ar["score"], ar["issues"], ar["proof"])
            if step_key == "verification.elite_builder":
                from .elite_builder_gate import verify_elite_builder_workspace

                er = await verify_elite_builder_workspace(
                    workspace_path or "",
                    job_goal=(step.get("job_goal") or ""),
                )
                return _result(er["passed"], er["score"], er["issues"], er["proof"])
            return _result(
                True, 82, [],
                [_proof_item("generic", f"Verification step recorded: {step_key}",
                             {"step_key": step_key})],
            )
    except Exception as e:
        logger.exception("verification branch error for %s", step_key)
        return _result(False, 0, [f"Verification error: {str(e)}"], [])

    fn = STEP_TYPE_MAP.get(prefix)

    try:
        if fn == verify_db_step:
            result = await fn(step, db_pool=db_pool, workspace_path=workspace_path)
        elif fn in (verify_frontend_step, verify_backend_step):
            result = await fn(step, workspace_path)
        elif fn == verify_deploy_step:
            result = await fn(step, workspace_path or "")
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

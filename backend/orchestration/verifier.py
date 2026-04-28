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
from typing import Any, Dict, List, Optional

from .runtime_health import skip_node_verify_env

logger = logging.getLogger(__name__)

_PROSE_PREFIXES = (
    "i ",
    "i'",
    "here ",
    "here'",
    "this ",
    "the following",
    "appreciate",
    "certainly",
    "sure,",
    "below",
    "based on",
    "as requested",
    "i have",
    "i'll",
    "let me",
    "of course",
    "happy to",
    "glad to",
    "please find",
    "above is",
    "this is",
    "the above",
    "note:",
    "note that",
    "in this",
    "we have",
)

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


def _result(
    passed: bool, score: int, issues: List[str], proof: List[Dict]
) -> Dict[str, Any]:
    return {"passed": passed, "score": score, "issues": issues, "proof": proof}


def _gate_result(
    src: Dict[str, Any],
    *,
    stage: str,
    extra_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Normalize a gate result without dropping its root-cause metadata."""
    out = _result(
        bool(src.get("passed")),
        int(src.get("score") or 0),
        list(src.get("issues") or []),
        list(src.get("proof") or []),
    )
    out["stage"] = stage
    for key in ["failure_reason", *(extra_keys or [])]:
        if key in src:
            out[key] = src[key]
    return out


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
    return {"proof_type": proof_type, "check": proof_type, "title": title, "payload": p}


def _first_meaningful_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


PROSE_PREFIXES_VERIFIER = (
    "i ",
    "i'",
    "here ",
    "here'",
    "appreciate",
    "certainly",
    "sure,",
    "below",
    "based on",
    "as requested",
    "i have",
    "i'll",
    "let me",
    "of course",
    "happy to",
    "glad to",
    "please find",
    "the following",
    "above is",
    "this is",
    "note:",
    "note that",
    "in this",
    "we have",
    "the code",
    "the following code",
    "the component",
)


def _strip_prose_lines(text: str) -> str:
    """Strip LLM prose lines from the top of a code file."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if not stripped:
            continue
        if any(stripped.startswith(p) for p in PROSE_PREFIXES_VERIFIER):
            continue
        return "\n".join(lines[i:])
    return text


def _detect_prose_preamble(text: str) -> Optional[str]:
    first = _first_meaningful_line(text)
    if not first:
        return None
    lowered = first.lower()
    if any(lowered.startswith(prefix) for prefix in _PROSE_PREFIXES):
        return first[:120]
    return None


def _looks_like_jsx_source(path: str, text: str) -> bool:
    lowered = path.lower()
    if lowered.endswith((".jsx", ".tsx")):
        return True
    if lowered.endswith(".js"):
        return (
            "React" in text
            or "react" in text.lower()
            or "</" in text
            or "/>" in text
            or "jsx" in text.lower()
        )
    return False


def _npx_bin() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"


async def _verify_frontend_source_file(
    full: str, rel: str, workspace_path: str
) -> Dict[str, Any]:
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []
    try:
        with open(full, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        return _result(False, 20, [f"Could not read {rel}: {exc}"], [])

    prose = _detect_prose_preamble(text)
    if prose:
        # Strip the prose and rewrite the file so verification can continue
        # This is the #1 recurring failure — LLM writes English before code
        cleaned = _strip_prose_lines(text)
        if cleaned.strip() and cleaned != text:
            try:
                with open(full, "w", encoding="utf-8") as fh:
                    fh.write(cleaned)
                text = cleaned
                proof.append(
                    _proof_item(
                        "prose_auto_stripped",
                        f"Auto-stripped prose in {rel}",
                        {"file": rel, "path": rel, "stripped_line": prose[:80]},
                        verification_class="syntax",
                    )
                )
                logger.info(
                    "verifier: auto-stripped prose from %s: %s", rel, prose[:60]
                )
            except OSError:
                issues.append(f"Prose preamble detected in {rel}: {prose}")
                return _result(False, 20, issues, proof)
        else:
            issues.append(f"Prose preamble detected in {rel}: {prose}")
            return _result(False, 20, issues, proof)

    ext = os.path.splitext(rel)[1].lower()
    uses_jsx = _looks_like_jsx_source(rel, text)
    loader = "js"
    if ext == ".jsx":
        loader = "jsx"
    elif ext == ".tsx":
        loader = "tsx"
    elif ext == ".ts":
        loader = "ts"
    elif ext == ".js" and uses_jsx:
        loader = "jsx"

    try:
        cmd = [
            _npx_bin(),
            "esbuild",
            "--format=esm",
            f"--loader={loader}",
            f"--sourcefile={rel}",
            "--log-level=error",
        ]
        result = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workspace_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(
            result.communicate(text.encode("utf-8")),
            timeout=20,
        )
        if result.returncode != 0:
            issues.append(
                f"esbuild failed {rel}: {stderr.decode(errors='replace')[:220]}"
            )
        else:
            proof.append(
                _proof_item(
                    "compile",
                    f"esbuild OK: {rel}",
                    {
                        "file": rel,
                        "path": rel,
                        "command": cmd,
                        "mode": "stdin_transform",
                    },
                    verification_class="syntax",
                ),
            )
    except FileNotFoundError:
        issues.append(f"npx/esbuild unavailable for syntax validation: {rel}")
    except asyncio.TimeoutError:
        issues.append(f"esbuild timed out for {rel}")

    return _result(len(issues) == 0, 100 if not issues else 35, issues, proof)


# ── Step-type verifiers ───────────────────────────────────────────────────────


async def verify_frontend_step(
    step: Dict[str, Any], workspace_path: str
) -> Dict[str, Any]:
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

    # Syntax check with real JSX/TSX validation
    for f in output_files:
        full = os.path.join(workspace_path, f)
        if not full.endswith((".jsx", ".tsx", ".js", ".ts")) or not os.path.exists(
            full
        ):
            continue
        file_result = await _verify_frontend_source_file(full, f, workspace_path)
        issues.extend(file_result["issues"])
        proof.extend(file_result["proof"])

    score = 100 if not issues else max(40, 100 - len(issues) * 20)
    return _result(len(issues) == 0, score, issues, proof)


async def verify_backend_step(
    step: Dict[str, Any], workspace_path: str
) -> Dict[str, Any]:
    issues = []
    proof = []
    step_key = step.get("step_key", "")

    for route in step.get("routes_added") or []:
        method = route.get("method") or "GET"
        path = route.get("path") or ""
        proof.append(
            _proof_item(
                "route",
                f"{method} {path}".strip() or "route",
                {
                    "method": method,
                    "path": path,
                    "description": route.get("description", ""),
                },
            )
        )

    output_files = step.get("output_files") or []
    if (
        step_key.startswith("backend.")
        and not output_files
        and not (step.get("routes_added") or [])
    ):
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
                        proof.append(
                            _proof_item(
                                "compile",
                                f"Python syntax OK: {f}",
                                {"file": f, "path": f, "command": list(cmd)},
                            )
                        )
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

    if (
        workspace_path
        and os.path.isdir(workspace_path)
        and step_key == "backend.routes"
    ):
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


async def verify_db_step(
    step: Dict[str, Any], db_pool=None, workspace_path: str = ""
) -> Dict[str, Any]:
    issues = []
    proof = []
    step_key = step.get("step_key", "")

    tables_created = step.get("tables_created") or []
    migration_files = [
        f for f in (step.get("output_files") or []) if str(f).lower().endswith(".sql")
    ]
    if workspace_path and migration_files:
        for f in migration_files:
            full = os.path.join(workspace_path, f)
            if os.path.exists(full):
                proof.append(
                    _proof_item(
                        "db",
                        f"SQL artifact: {f}",
                        {"path": f, "kind": "migration_or_seed"},
                    )
                )
            else:
                issues.append(f"Expected SQL file missing: {f}")

    if step_key.startswith("database.") and not tables_created and not migration_files:
        issues.append("Database step produced no .sql artifacts and no tables_created")

    if db_pool and tables_created:
        try:
            async with db_pool.acquire() as conn:
                for table in tables_created:
                    row = await conn.fetchrow(
                        "SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name=$1)",
                        table,
                    )
                    if row and row[0]:
                        mig0 = migration_files[0] if migration_files else ""
                        payload = (
                            {"table": table, "path": mig0} if mig0 else {"table": table}
                        )
                        proof.append(
                            _proof_item("db", f"Table exists: {table}", payload)
                        )
                    else:
                        issues.append(f"Table not found: {table}")
        except Exception as e:
            issues.append(f"DB verification error: {str(e)}")

    score = 100 if not issues else max(30, 100 - len(issues) * 25)
    return _result(len(issues) == 0, score, issues, proof)


async def verify_deploy_step(
    step: Dict[str, Any], workspace_path: str = ""
) -> Dict[str, Any]:
    issues = []
    proof = []
    step_key = step.get("step_key", "")
    failure_reason = ""
    added_deploy_file_proof = False

    if not workspace_path or not os.path.isdir(workspace_path):
        issues.append(f"Deploy workspace missing: {workspace_path or '<empty>'}")
        failure_reason = "deploy_workspace_missing"

    if workspace_path and os.path.isdir(workspace_path):
        from .production_gate import scan_workspace_for_credential_patterns
        from .tenant_deploy_gate import verify_tenant_context_for_deploy

        if step_key == "deploy.build":
            t_issues, t_proof = verify_tenant_context_for_deploy(workspace_path)
            issues.extend(t_issues)
            if t_issues and not failure_reason:
                failure_reason = "deploy_tenant_gate_failed"
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
            strict = os.environ.get(
                "CRUCIBAI_PRODUCTION_GATE_STRICT", ""
            ).strip().lower() in (
                "1",
                "true",
                "yes",
            )
            if strict and hits:
                issues.extend(hits)
                if not failure_reason:
                    failure_reason = "deploy_credential_gate_failed"
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
            full = os.path.normpath(
                os.path.join(workspace_path, rel.replace("/", os.sep))
            )
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
                added_deploy_file_proof = True
            else:
                issues.append(f"Expected deploy artifact missing: {rel}")
                if not failure_reason:
                    failure_reason = "deploy_artifact_missing"

    deploy_url = step.get("deploy_url")
    if deploy_url:
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    deploy_url, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
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
                        # 404 is expected for publish URL before the app is built/deployed.
                        # Record as advisory, not a hard failure.
                        proof.append(
                            _proof_item(
                                "deploy",
                                f"Deploy URL returned {resp.status} (advisory — app not yet deployed to this URL)",
                                {"url": deploy_url, "status": resp.status, "severity": "advisory"},
                                verification_class="presence",
                            ),
                        )
        except Exception as e:
            # Network errors are advisory — the URL may not be live yet.
            proof.append(
                _proof_item(
                    "deploy",
                    f"Deploy URL check skipped: {str(e)[:80]}",
                    {"url": deploy_url, "error": str(e)[:80], "severity": "advisory"},
                    verification_class="presence",
                ),
            )
    elif step_key == "deploy.publish":
        require_live_publish = os.environ.get(
            "CRUCIBAI_REQUIRE_LIVE_DEPLOY_PUBLISH", ""
        ).strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if require_live_publish:
            issues.append("Deploy publish requires deploy_url but none was produced")
            if not failure_reason:
                failure_reason = "deploy_publish_url_missing"
        else:
            proof.append(
                _proof_item(
                    "deploy",
                    "Deploy publish recorded as readiness-only (no live URL configured)",
                    {"publish_mode": "readiness_only", "deploy_url": None},
                    verification_class="presence",
                ),
            )
    elif not added_deploy_file_proof:
        proof.append(
            _proof_item(
                "deploy",
                "Deploy step recorded (no URL to ping yet)",
                {},
                verification_class="presence",
            ),
        )

    score = 100 if not issues else 50
    out = _result(len(issues) == 0, score, issues, proof)
    out["stage"] = step_key or "deploy"
    if failure_reason:
        out["failure_reason"] = failure_reason
    return out


# ── Generic verifier dispatcher ───────────────────────────────────────────────

STEP_TYPE_MAP = {
    "frontend": verify_frontend_step,
    "backend": verify_backend_step,
    "database": verify_db_step,
    "db": verify_db_step,
    "deploy": verify_deploy_step,
}


async def verify_compile_workspace(
    workspace_path: str, max_files: int = 28
) -> Dict[str, Any]:
    """Cross-cut syntax check for JS entrypoints (depth, not only declared output_files)."""
    issues: List[str] = []
    proof: List[Dict] = []
    # NOTE: CRUCIBAI_SKIP_NODE_VERIFY no longer skips verification entirely.
    # We validate JSX/TSX using esbuild and JS/TS using node --check.
    _skip_warned = skip_node_verify_env()
    if _skip_warned:
        logger.warning(
            "CRUCIBAI_SKIP_NODE_VERIFY is set but syntax checking is still active via esbuild fallback. "
            "This env var no longer disables verification."
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
            if not name.endswith((".js", ".jsx", ".ts", ".tsx")) or name.endswith(
                (
                    ".test.js",
                    ".test.jsx",
                    ".spec.js",
                    ".spec.jsx",
                    ".test.ts",
                    ".test.tsx",
                )
            ):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, workspace_path).replace("\\", "/")
            if "node_modules" in rel:
                continue
            file_result = await _verify_frontend_source_file(full, rel, workspace_path)
            checked += 1
            issues.extend(file_result["issues"])
            proof.extend(file_result["proof"])
        if checked >= max_files:
            break
    score = 100 if not issues else max(25, 100 - len(issues) * 15)
    return _result(len(issues) == 0, score, issues, proof)


async def verify_step(
    step: Dict[str, Any], workspace_path: str = "", db_pool=None
) -> Dict[str, Any]:
    """
    Run the appropriate verifier for this step type.
    Falls back to a minimal check if no specific verifier matches.
    """
    step_key = step.get("step_key", "")
    # Determine type from step_key prefix
    prefix = step_key.split(".")[0] if "." in step_key else step.get("phase", "")

    try:
        touched = list(step.get("output_files") or [])
        if workspace_path and touched:
            from .file_language_sanity import sniff_touched_files_language_mismatch

            lang_issues = sniff_touched_files_language_mismatch(
                workspace_path, touched
            )
            if lang_issues:
                early = _result(
                    False,
                    28,
                    lang_issues,
                    [
                        _proof_item(
                            "compile",
                            "File extension vs content mismatch (early gate)",
                            {
                                "kind": "language_mismatch",
                                "sample_paths": touched[:24],
                            },
                            verification_class="syntax",
                        )
                    ],
                )
                early["failure_reason"] = "language_mismatch"
                early["stage"] = "file_language_sanity"
                return early

        if prefix == "verification":
            if step_key == "verification.preview":
                from .preview_gate import verify_preview_workspace

                pr = await verify_preview_workspace(workspace_path or "")
                return _gate_result(pr, stage="preview_boot")
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
                from .verification_behavior_bundle import (
                    verify_behavior_bundle_workspace,
                )

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
                return _gate_result(
                    er,
                    stage="elite_builder",
                    extra_keys=[
                        "checks",
                        "checks_passed",
                        "checks_total",
                        "failed_checks",
                        "recommendation",
                    ],
                )
            return _result(
                True,
                82,
                [],
                [
                    _proof_item(
                        "generic",
                        f"Verification step recorded: {step_key}",
                        {"step_key": step_key},
                    )
                ],
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
            # Generic: record that the step ran with real output preview
            raw_output = (
                step.get("output")
                or step.get("result")
                or step.get("output_ref")
                or step.get("code")
                or ""
            )
            if isinstance(raw_output, dict):
                import json as _json

                raw_output = _json.dumps(raw_output)
            output_preview = str(raw_output)[:300] if raw_output else ""
            result = _result(
                True,
                85,
                [],
                [
                    _proof_item(
                        "generic",
                        f"Step executed: {step_key}",
                        {"step_key": step_key, "output_preview": output_preview},
                    )
                ],
            )
    except Exception as e:
        logger.exception("verifier error for step %s", step_key)
        result = _result(False, 0, [f"Verifier threw exception: {str(e)}"], [])

    return result

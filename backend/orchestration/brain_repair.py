"""
brain_repair.py — The actual repair brain. Reads a diagnosis and applies
a real fix before retry so each attempt is different from the last.

This is wired into the auto_runner retry loop. When a step fails, this
module determines WHAT to change before trying again — not just logs it.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Repair actions ─────────────────────────────────────────────────────────────


def _summarize_deterministic_repairs(repair_result: Dict[str, Any]) -> str:
    parts: List[str] = []
    for r in repair_result.get("repairs") or []:
        if not r.get("fixed"):
            continue
        t = r.get("type", "")
        if t == "add_npm_dependency":
            parts.append(f"Added npm package {r.get('package', '?')}.")
        elif t in ("strip_prose", "strip_prose_scan"):
            parts.append(f"Removed prose from {r.get('file', 'a file')}.")
        elif t == "repair_app_jsx":
            parts.append("Repaired src/App.jsx.")
        elif t == "repair_package_json":
            parts.append("Normalized package.json.")
        elif t == "repair_entry_point":
            parts.append("Repaired src/main.jsx entry point.")
        elif t == "repair_vite_config":
            parts.append("Added or repaired vite.config.js.")
        elif t == "repair_index_html":
            parts.append("Added or repaired index.html.")
        else:
            parts.append(f"Applied fix ({t}).")
    return " ".join(parts).strip()[:900]


async def run_full_brain_repair(
    workspace_path: str,
    step_key: str,
    error_message: str,
    retry_count: int,
    job: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Full brain repair — four layers matching how I (Claude) think:

    1. Read workspace files to diagnose root cause (workspace_reader)
    2. Apply self-repair — write deterministic code fixes to disk (self_repair)
    3. If deterministic repair wasn't enough — call Claude to write novel fixes (llm_code_repair)
    4. Return parameter mutations for the next LLM call (apply_targeted_repair)

    Layers 1+2 = what a linter does.
    Layer 3 = what a developer does.
    Layer 4 = what a DevOps engineer does (adjust how the agent runs).
    """
    from backend.agents.code_repair_agent import CodeRepairAgent

    from .brain_intelligence import recall_best_fix, remember_fix, search_error_solution
    from .llm_code_repair import (
        analyse_failure_with_llm,
        get_downstream_impact,
        llm_repair_callback,
        repair_file_with_llm,
    )
    from .self_repair import apply_self_repair
    from .workspace_reader import diagnose_workspace

    logger.info(
        "brain: full repair start step=%s retry=%d error=%s",
        step_key,
        retry_count,
        error_message[:120],
    )

    # ── Layer 1: Read workspace ───────────────────────────────────────────────
    diagnosis = diagnose_workspace(
        workspace_path=workspace_path,
        failed_step_key=step_key,
        error_message=error_message,
    )
    logger.info(
        "brain: diagnosis root_cause=%s findings=%d affected=%s",
        diagnosis.get("root_cause"),
        len(diagnosis.get("findings", [])),
        diagnosis.get("affected_files", [])[:3],
    )

    # ── Memory recall: have we seen this error before? ────────────────────────
    memory_hit = await recall_best_fix(error_message, step_key)
    if memory_hit:
        logger.info(
            "brain: MEMORY HIT — known fix: %s (success_rate=%.0f%% from %d past builds)",
            memory_hit.get("fix_type"),
            memory_hit.get("success_rate", 0) * 100,
            memory_hit.get("success_count", 0),
        )

    # ── Layer 2: Deterministic self-repair ────────────────────────────────────
    repair_result = await apply_self_repair(
        workspace_path=workspace_path,
        diagnosis=diagnosis,
        step_key=step_key,
        error_message=error_message,
    )
    logger.info(
        "brain: deterministic repair fixed=%d repairs=%s",
        repair_result.get("fixed_count", 0),
        [r.get("type") for r in repair_result.get("repairs", [])],
    )

    raw_id = (job or {}).get("id") if job else None
    jid = str(raw_id) if raw_id is not None else None
    if repair_result.get("fixed_count", 0) > 0 and jid:
        summary = _summarize_deterministic_repairs(repair_result)
        if summary:
            try:
                from .event_bus import publish
                from .runtime_state import append_job_event

                payload = {
                    "kind": "deterministic_repair",
                    "headline": "Applied an automatic fix",
                    "summary": summary,
                    "next_steps": [
                        "Re-running verification on the updated workspace.",
                    ],
                }
                await append_job_event(jid, "brain_guidance", payload)
                await publish(jid, "brain_guidance", payload)
            except Exception as e:
                logger.warning("brain: could not emit deterministic_repair guidance: %s", e)

    # ── Layer 3: LLM repair for files that deterministic couldn't fix ─────────
    llm_repairs: List[Dict[str, Any]] = []
    causal_analysis: Dict[str, Any] = {}

    # Files that deterministic repair replaced with a scaffold stub are NOT truly fixed —
    # they need LLM regeneration to produce real code. We exclude only files that were
    # genuinely fixed (e.g. added npm dep, fixed vite config, stripped a preamble that
    # left real code behind). Scaffold replacements are still in critical_unfixed.
    scaffold_replaced = {
        r.get("file")
        for r in repair_result.get("repairs", [])
        if r.get("fixed") and r.get("action") in (
            "replaced_json_prose_with_scaffold",
            "replaced_with_scaffold",
            "created_minimal",
        )
    }
    truly_fixed_by_det = {
        r.get("file")
        for r in repair_result.get("repairs", [])
        if r.get("fixed") and r.get("file") not in scaffold_replaced
    }
    critical_unfixed = [
        f
        for f in diagnosis.get("critical_findings", [])
        if f.get("file")
        and f.get("file") not in truly_fixed_by_det
        and not f.get("file", "").startswith("proof_bundle")
    ]
    # Also include scaffold-replaced files — they need LLM to regenerate real code
    for rel in scaffold_replaced:
        if rel and not any(f.get("file") == rel for f in critical_unfixed):
            critical_unfixed.append({
                "file": rel,
                "check": "scaffold_replaced",
                "issues": ["File was scaffold-replaced — needs LLM regeneration"],
                "severity": "critical",
                "fix_hint": "regenerate_with_llm",
            })

    # LLM repair: normally retry 1+; verification/implementation gates need fixes on first failure too.
    verify_or_impl = (step_key or "").startswith(
        ("verification.", "implementation.")
    )
    allow_llm = retry_count >= 1 or verify_or_impl
    if (
        allow_llm
        and critical_unfixed
        and workspace_path
        and os.path.isdir(workspace_path)
    ):
        for finding in critical_unfixed[:3]:  # Max 3 LLM repair calls per retry
            rel_path = finding.get("file", "")
            if not rel_path:
                continue
            logger.info(
                "brain: calling LLM to repair %s (retry=%d)", rel_path, retry_count
            )
            llm_result = await repair_file_with_llm(
                workspace_path=workspace_path,
                rel_path=rel_path,
                error_message=error_message,
                diagnosis=diagnosis,
            )
            llm_repairs.append(llm_result)
            if llm_result.get("fixed"):
                logger.info("brain: LLM fixed %s", rel_path)

        # Also run CodeRepairAgent with LLM callback on Python/JSON/JSX files
        if workspace_path:
            affected_files = diagnosis.get("affected_files", [])
            py_json_files = [
                f
                for f in affected_files
                if f.endswith((".py", ".json", ".yaml", ".yml",
                               ".jsx", ".tsx", ".js", ".ts"))
            ]
            if py_json_files:
                repaired = await CodeRepairAgent.repair_workspace_files(
                    workspace_path,
                    py_json_files,
                    verification_issues=[error_message] if error_message else [],
                    llm_repair=llm_repair_callback,
                )
                if repaired:
                    llm_repairs.append(
                        {
                            "fixed": True,
                            "files": repaired,
                            "method": "code_repair_agent_llm",
                        }
                    )
                    logger.info("brain: CodeRepairAgent+LLM fixed %s", repaired)

    # ── Web search for unknown errors ────────────────────────────────────────
    web_search_result = None
    if allow_llm and not (
        repair_result.get("fixed_count", 0) > 0
        or any(r.get("fixed") for r in llm_repairs)
    ):
        # Nothing fixed it yet — search the web for solutions
        ext_map = {
            ".jsx": "React JSX",
            ".tsx": "TypeScript React",
            ".py": "Python FastAPI",
            ".js": "JavaScript",
            ".json": "JSON",
        }
        lang = ""
        if diagnosis.get("affected_files"):
            import os as _os

            ext = _os.path.splitext(diagnosis["affected_files"][0])[1].lower()
            lang = ext_map.get(ext, "")
        logger.info("brain: searching web for solution (retry=%d)", retry_count)
        web_search_result = await search_error_solution(
            error_message=error_message,
            step_key=step_key,
            language=lang,
        )
        if web_search_result:
            logger.info(
                "brain: web search found solution (%d chars)", len(web_search_result)
            )

    # Causal chain analysis — understand what else will break
    if allow_llm:
        try:
            from .workspace_reader import list_workspace_files, read_workspace_file

            snapshot = {}
            if workspace_path and os.path.isdir(workspace_path):
                for rel in list_workspace_files(workspace_path)[:25]:
                    content = read_workspace_file(workspace_path, rel)
                    if content:
                        snapshot[rel] = content.strip().split("\n")[0][:80]
            causal_analysis = await analyse_failure_with_llm(
                failed_step_key=step_key,
                error_message=error_message,
                workspace_snapshot=snapshot,
            )
            logger.info(
                "brain: causal analysis root=%s downstream=%s confidence=%s",
                causal_analysis.get("root_cause", "")[:80],
                causal_analysis.get("downstream_blocked", [])[:3],
                causal_analysis.get("confidence"),
            )
        except Exception as e:
            logger.warning("brain: causal analysis failed: %s", e)
            causal_analysis = {
                "downstream_blocked": get_downstream_impact(step_key),
                "source": "static_fallback",
            }

    # ── Layer 4: Parameter mutations for next LLM call ────────────────────────
    param_mutations = await apply_targeted_repair(
        step={"step_key": step_key},
        error_message=error_message,
        retry_count=retry_count,
        workspace_path=workspace_path,
        job=job,
    )

    # Compute total fixes
    det_fixed = repair_result.get("fixed_count", 0)
    llm_fixed = sum(1 for r in llm_repairs if r.get("fixed"))
    total_fixed = det_fixed + llm_fixed

    all_repaired_files = [
        r.get("file") for r in repair_result.get("repairs", []) if r.get("fixed")
    ] + [r.get("file") for r in llm_repairs if r.get("fixed") and r.get("file")]

    logger.info(
        "brain: repair complete det=%d llm=%d total=%d files=%s strategy=%s",
        det_fixed,
        llm_fixed,
        total_fixed,
        all_repaired_files[:3],
        param_mutations.get("strategy"),
    )

    # ── Store this attempt in memory ─────────────────────────────────────────
    strategy = param_mutations.get("strategy", "unknown")
    await remember_fix(
        error_message=error_message,
        step_key=step_key,
        fix_type=strategy,
        fix_description=param_mutations.get("explanation", ""),
        success=total_fixed > 0,
        retry_count=retry_count,
        files_repaired=all_repaired_files,
    )

    return {
        "diagnosis": diagnosis,
        "repairs_applied": repair_result,
        "llm_repairs": llm_repairs,
        "causal_analysis": causal_analysis,
        "memory_hit": memory_hit,
        "web_search_result": web_search_result,
        "mutations": param_mutations.get("mutations", {}),
        "strategy": strategy,
        "explanation": param_mutations.get("explanation", ""),
        "workspace_fixed": total_fixed > 0,
        "files_repaired": all_repaired_files,
        "downstream_at_risk": causal_analysis.get("downstream_blocked", []),
    }


async def apply_targeted_repair(
    step: Dict[str, Any],
    error_message: str,
    retry_count: int,
    workspace_path: str = "",
    job: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Read the error, diagnose, and return a mutation dict that gets merged
    into the step before re-queuing. This is what makes each retry different.

    Returns: {"mutations": {...}, "strategy": str, "explanation": str}
    """
    err = (error_message or "").lower()
    step_key = step.get("step_key", "")
    agent_name = step.get("agent_name") or step.get("agent") or step.get("name") or ""
    mutations: Dict[str, Any] = {}
    strategy = "conservative_retry"
    explanation = "No specific repair identified — retrying as-is"

    # ── ANTHROPIC 400: context too large ──────────────────────────────────────
    if "anthropic api returned 400" in err or "400" in err and "anthropic" in err:
        err_type = ""
        # Try to extract the Anthropic error type from the message
        m = re.search(r"400 \(([^)]+)\)", error_message or "")
        if m:
            err_type = m.group(1).lower()

        if "context_length" in err_type or "too long" in err or retry_count <= 2:
            # Reduce context aggressively on first few retries
            reduce_factor = min(0.3 + retry_count * 0.1, 0.8)  # 30%→40%→50%→...
            mutations["context_reduce_factor"] = reduce_factor
            mutations["use_minimal_context"] = True
            strategy = "reduce_context"
            explanation = (
                f"Anthropic 400 (attempt {retry_count+1}): "
                f"reducing context to {int(reduce_factor*100)}% of normal size"
            )
        elif retry_count == 3:
            # Try with zero previous context
            mutations["use_minimal_context"] = True
            mutations["context_reduce_factor"] = 0.0
            strategy = "zero_context_retry"
            explanation = "Anthropic 400 (attempt 4): retrying with no previous context"
        elif retry_count >= 4:
            # Try a different model — fall back to Cerebras
            mutations["force_model"] = "cerebras"
            mutations["use_minimal_context"] = True
            strategy = "switch_model"
            explanation = (
                f"Anthropic 400 (attempt {retry_count+1}): "
                "switching to Cerebras as fallback model"
            )

    # ── PROSE IN CODE: LLM wrote English into source file ─────────────────────
    elif any(
        k in err
        for k in ["found 'appreciate'", 'expected ";"', "prose", "transform failed"]
    ):
        mutations["enforce_code_only"] = True
        mutations["prepend_system_instruction"] = (
            "CRITICAL: Output ONLY valid code. "
            "Your response MUST start with the first character of code (import/function/const/def). "
            "Do NOT write any explanation, preamble, or English text."
        )
        strategy = "enforce_code_only"
        explanation = f"Prose-in-code detected (attempt {retry_count+1}): injecting hard code-only constraint"

    # ── SYNTAX ERROR: broken code in file ─────────────────────────────────────
    elif any(
        k in err
        for k in ["syntaxerror", "syntax error", "unexpected token", "esbuild failed"]
    ):
        # Point to the specific file and line if available
        file_match = re.search(r"([\w/.-]+\.(jsx?|tsx?|py)):(\d+)", error_message or "")
        if file_match:
            mutations["repair_target_file"] = file_match.group(1)
            mutations["repair_target_line"] = int(file_match.group(3))
        mutations["enforce_code_only"] = True
        strategy = "fix_syntax"
        explanation = (
            f"Syntax error (attempt {retry_count+1}): "
            f"targeting {mutations.get('repair_target_file', 'source file')} for repair"
        )

    # ── MISSING IMPORT / MODULE NOT FOUND ─────────────────────────────────────
    elif any(
        k in err
        for k in ["cannot find module", "module not found", "failed to resolve import"]
    ):
        mutations["prepend_system_instruction"] = (
            "All imports must use only packages available in package.json. "
            "Do not import from '@/' aliases unless vite.config.js defines them. "
            "Use relative imports (./components/Button) for local files."
        )
        strategy = "fix_imports"
        explanation = f"Import error (attempt {retry_count+1}): constraining imports to available packages"

    # ── LLM RATE LIMIT ────────────────────────────────────────────────────────
    elif "rate limit" in err or "429" in err:
        # Just wait more — the delay is handled by exponential backoff
        strategy = "rate_limit_backoff"
        explanation = (
            f"Rate limit (attempt {retry_count+1}): will back off before retry"
        )

    # ── UNKNOWN: escalate aggressively ────────────────────────────────────────
    else:
        if retry_count >= 2:
            mutations["use_minimal_context"] = True
            mutations["force_minimal_prompt"] = True
        strategy = "unknown_escalating"
        explanation = f"Unknown error (attempt {retry_count+1}): " + (
            "reducing to minimal context" if retry_count >= 2 else "retrying as-is"
        )

    logger.info(
        "brain_repair: step=%s agent=%s attempt=%d strategy=%s — %s",
        step_key,
        agent_name,
        retry_count + 1,
        strategy,
        explanation,
    )

    return {
        "mutations": mutations,
        "strategy": strategy,
        "explanation": explanation,
    }


def build_reduced_context_prompt(
    original_prompt: str,
    previous_outputs: Dict[str, Any],
    reduce_factor: float = 0.3,
    relevant_agents: Optional[list] = None,
) -> str:
    """
    Build a reduced context prompt for retry.
    reduce_factor=0.0 returns just the original prompt.
    reduce_factor=0.5 includes 50% of normal context.
    """
    if reduce_factor <= 0.0:
        return original_prompt

    parts = [original_prompt]
    max_total = int(15000 * reduce_factor)
    total = 0

    # If we know which agents matter, prioritize them
    agents_to_include = relevant_agents or list(previous_outputs.keys())

    for agent_name in agents_to_include:
        if total >= max_total:
            break
        data = previous_outputs.get(agent_name)
        if not data:
            continue
        out = data.get("output") or data.get("result") or data.get("code") or ""
        if isinstance(out, str) and out.strip():
            # Use a smaller slice per agent when reducing
            per_agent_max = int(3000 * reduce_factor)
            snippet = out.strip()[:per_agent_max]
            parts.append(f"--- Output from {agent_name} ---\n{snippet}")
            total += len(snippet)

    return "\n\n".join(parts)

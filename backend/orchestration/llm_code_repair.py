"""
llm_code_repair.py — LLM-powered code repair using Claude/Anthropic.

This gives the brain the ability to fix code it's never seen before,
the same way a human developer would:
  1. Read the broken file
  2. Read the error message
  3. Ask Claude to fix it
  4. Validate the result
  5. Write it back to disk

This is what separates "parameter tuning" from "code authorship."
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── System prompts for each repair type ───────────────────────────────────────

REPAIR_PROMPTS = {
    "python": """You are a Python code repair expert.
You will be given broken Python code and an error message.
Return ONLY the fixed Python code. No explanation. No markdown fences.
Your response must start with the first character of valid Python code (import/def/class/etc).
The fix must be minimal — change only what is necessary to resolve the error.""",
    "javascript": """You are a JavaScript/React code repair expert.
You will be given broken JSX/TSX/JS code and an error message.
Return ONLY the fixed code. No explanation. No markdown fences.
Your response must start with the first character of valid code (import/export/const/function/etc).
The fix must be minimal — change only what is necessary to resolve the error.""",
    "json": """You are a JSON repair expert.
You will be given malformed JSON and an error message.
Return ONLY valid JSON. No explanation. No markdown fences.
Your response must start with { or [.""",
    "general": """You are a code repair expert.
You will be given broken code and an error message.
Return ONLY the fixed code. No explanation. No markdown fences.
Your response must start with the first character of valid code.
The fix must be minimal.""",
}

CAUSAL_CHAIN_PROMPT = """You are a build failure analyst for a React + FastAPI application.

Given:
- A failed build step key
- An error message  
- A list of workspace files and their first lines
- The DAG dependency structure

Your job is to:
1. Identify the ROOT CAUSE (not just the symptom)
2. List all DOWNSTREAM steps that will also fail because of this
3. Suggest the MINIMAL FIX that resolves the root cause

Respond in JSON with this structure:
{
  "root_cause": "one sentence description",
  "root_file": "path/to/broken/file or null",
  "root_line": line_number_or_null,
  "downstream_blocked": ["step.key1", "step.key2"],
  "fix_description": "what needs to change",
  "fix_type": "one of: regenerate_file | fix_import | fix_syntax | fix_config | add_dep | unknown",
  "confidence": "high|medium|low"
}"""


# ── LLM caller ─────────────────────────────────────────────────────────────────


async def _call_anthropic_repair(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4096,
) -> Optional[str]:
    """Call LLM for a repair task. Cerebras is primary; Anthropic is fallback."""
    # ── Cerebras primary ────────────────────────────────────────────────────────────
    cerebras_key = os.environ.get("CEREBRAS_API_KEY", "").strip()
    if cerebras_key:
        try:
            from ....llm_cerebras import invoke_cerebras_stream            content = ""
            async for chunk in invoke_cerebras_stream(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
            ):
                content += chunk
            if content:
                logger.info("llm_code_repair: got %d chars from Cerebras", len(content))
                return content
        except Exception as e:
            logger.warning("llm_code_repair: Cerebras failed, trying Anthropic: %s", e)

    # ── Anthropic fallback ──────────────────────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        logger.warning("llm_code_repair: no LLM keys available")
        return None

    try:
        import anthropic as _anthropic

        client = _anthropic.AsyncAnthropic(api_key=api_key)
        from anthropic_models import ANTHROPIC_SONNET_MODEL, normalize_anthropic_model

        model = normalize_anthropic_model(
            os.environ.get("ANTHROPIC_MODEL"),
            default=ANTHROPIC_SONNET_MODEL,
        )
        message = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.1,  # Low temperature for repair — we want deterministic fixes
        )
        result = message.content[0].text if message.content else None
        logger.info("llm_code_repair: got %d chars from Claude", len(result or ""))
        return result
    except Exception as e:
        logger.error("llm_code_repair: Anthropic call failed: %s", e)
        return None


# ── Repair callback for CodeRepairAgent ───────────────────────────────────────


async def llm_repair_callback(
    agent_name: str,
    language: str,
    broken_code: str,
    error_message: str,
) -> str:
    """
    LLM repair callback compatible with CodeRepairAgent.repair_output().

    Call signature matches RepairCallback type:
    (agent_name, language, broken_code, error_message) -> fixed_code
    """
    lang_key = (
        "javascript"
        if language in ("javascript", "jsx", "tsx", "ts", "js")
        else language
    )
    system_prompt = REPAIR_PROMPTS.get(lang_key, REPAIR_PROMPTS["general"])

    user_prompt = f"""Agent: {agent_name}
Language: {language}
Error: {error_message[:500]}

Broken code:
{broken_code[:6000]}

Fix the code above. Return ONLY the fixed code."""

    result = await _call_anthropic_repair(system_prompt, user_prompt)
    return result or broken_code  # Fall back to original if repair fails


# ── Full file repair ───────────────────────────────────────────────────────────


async def repair_file_with_llm(
    workspace_path: str,
    rel_path: str,
    error_message: str,
    diagnosis: Optional[Dict[str, Any]] = None,
    *,
    recent_traces: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Read a broken file, ask Claude to fix it, write it back.
    This is the full "code author" loop.
    """
    full_path = os.path.join(workspace_path, rel_path)
    if not os.path.isfile(full_path):
        return {"fixed": False, "reason": f"{rel_path} not found"}

    try:
        with open(full_path, encoding="utf-8", errors="replace") as f:
            broken_content = f.read()
    except OSError as e:
        return {"fixed": False, "reason": f"Cannot read {rel_path}: {e}"}

    if not broken_content.strip():
        return {"fixed": False, "reason": f"{rel_path} is empty"}

    # Determine language from extension
    ext = os.path.splitext(rel_path)[1].lower()
    lang_map = {
        ".py": "python",
        ".jsx": "javascript",
        ".tsx": "javascript",
        ".js": "javascript",
        ".ts": "javascript",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".sql": "sql",
    }
    language = lang_map.get(ext, "general")

    # Build a rich context prompt if we have diagnosis info
    context = ""
    if diagnosis:
        findings = diagnosis.get("findings", [])
        relevant = [f for f in findings if f.get("file") == rel_path]
        if relevant:
            context = f"\nDiagnosis for this file:\n"
            for f in relevant:
                context += f"  - {f.get('check')}: {', '.join(f.get('issues', []))}\n"

    traces_block = ""
    if recent_traces:
        lines = []
        for line in recent_traces:
            s = str(line).strip()
            if s:
                lines.append(f"  • {s[:500]}")
        if lines:
            traces_block = "\nRecent failures from job log (newest first):\n" + "\n".join(lines) + "\n"

    system_prompt = REPAIR_PROMPTS.get(language, REPAIR_PROMPTS["general"])
    user_prompt = f"""File: {rel_path}
Language: {language}
Error: {error_message[:600]}
{context}{traces_block}
Broken file content:
{broken_content[:8000]}

Fix this file completely. Return ONLY the fixed code, nothing else."""

    logger.info("llm_code_repair: repairing %s (%s)", rel_path, language)
    fixed_content = await _call_anthropic_repair(
        system_prompt, user_prompt, max_tokens=6000
    )

    if not fixed_content:
        return {"fixed": False, "reason": "LLM returned no content"}

    # Strip any markdown fences the LLM added despite instructions
    from ....agents.code_repair_agent import strip_code_fences
    fixed_content = strip_code_fences(fixed_content)

    if fixed_content == broken_content:
        return {"fixed": False, "reason": "LLM returned identical content"}

    try:
        from ....orchestration.executor import _safe_write as _exec_safe_write
        rel_norm = rel_path.replace("\\", "/").lstrip("/")
        if not _exec_safe_write(workspace_path, rel_norm, fixed_content):
            return {
                "fixed": False,
                "reason": "Write rejected by safety guards (invalid path or blocked content)",
            }
        logger.info(
            "llm_code_repair: fixed %s (%d→%d chars)",
            rel_path,
            len(broken_content),
            len(fixed_content),
        )
        return {
            "fixed": True,
            "file": rel_path,
            "original_size": len(broken_content),
            "fixed_size": len(fixed_content),
            "method": "llm_repair",
        }
    except OSError as e:
        return {"fixed": False, "reason": f"Cannot write {rel_path}: {e}"}


# ── Causal chain analyser ──────────────────────────────────────────────────────

# DAG downstream map — if X fails, these are also blocked
CAUSAL_CHAINS = {
    "agents.database_agent": [
        "agents.multi_tenant_agent",
        "agents.data_pipeline_agent",
        "agents.data_warehouse_agent",
        "agents.database_schema_validator_agent",
        "agents.orm_setup_agent",
        "agents.ml_data_pipeline_agent",
        "agents.database_optimization_agent",
    ],
    "agents.frontend_generation": [
        "agents.e2e_test_agent",
        "agents.responsive_breakpoints_agent",
        "agents.typography_system_agent",
        "agents.iot_dashboard_agent",
        "agents.build_validator_agent",
    ],
    "agents.backend_generation": [
        "agents.database_agent",
        "agents.deployment_agent",
        "agents.websocket_agent",
        "agents.logging_agent",
        "agents.api_contract_validator_agent",
        "agents.cors_security_headers_agent",
    ],
    "verification.compile": [
        "verification.preview",
        "verification.api_smoke",
    ],
    "verification.preview": [
        "verification.elite_builder",
    ],
    "verification.elite_builder": [
        "deploy.build",
        "deploy.publish",
    ],
}


def get_downstream_impact(failed_step_key: str) -> List[str]:
    """Return list of steps that will be blocked if this step fails."""
    direct = CAUSAL_CHAINS.get(failed_step_key, [])
    all_blocked = list(direct)
    # Recurse one level for cascade
    for step in direct:
        all_blocked.extend(CAUSAL_CHAINS.get(step, []))
    return list(dict.fromkeys(all_blocked))  # dedupe preserving order


async def analyse_failure_with_llm(
    failed_step_key: str,
    error_message: str,
    workspace_snapshot: Dict[str, str],
) -> Dict[str, Any]:
    """
    Use Claude to do deep causal analysis of a build failure.
    workspace_snapshot: {rel_path: first_line_of_file}
    """
    # Get static downstream impact first
    downstream = get_downstream_impact(failed_step_key)

    # Build workspace summary for Claude
    ws_lines = "\n".join(
        f"  {path}: {first_line[:80]}"
        for path, first_line in list(workspace_snapshot.items())[:30]
    )

    user_prompt = f"""Failed step: {failed_step_key}
Error: {error_message[:600]}

Workspace files (path: first line):
{ws_lines}

Known downstream steps that will be blocked: {downstream[:5]}

Analyse the root cause and respond in JSON."""

    result = await _call_anthropic_repair(
        CAUSAL_CHAIN_PROMPT, user_prompt, max_tokens=800
    )

    if not result:
        return {
            "root_cause": error_message[:200],
            "downstream_blocked": downstream,
            "fix_type": "unknown",
            "confidence": "low",
            "source": "static_only",
        }

    try:
        import json

        # Strip markdown if present
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
        parsed = json.loads(clean)
        parsed["downstream_blocked"] = list(
            dict.fromkeys(downstream + (parsed.get("downstream_blocked") or []))
        )
        parsed["source"] = "llm_analysis"
        return parsed
    except Exception as e:
        logger.warning("llm_code_repair: causal analysis parse failed: %s", e)
        return {
            "root_cause": error_message[:200],
            "downstream_blocked": downstream,
            "fix_type": "unknown",
            "confidence": "low",
            "source": "static_fallback",
            "raw": result[:300],
        }

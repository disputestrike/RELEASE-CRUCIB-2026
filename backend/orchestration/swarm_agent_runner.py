"""Agent swarm planning + execution bridge for Auto-Runner.

This module lets the relational Auto-Runner execute the existing AGENT_DAG
instead of falling back to small fixed frontend/backend phases for complex
multi-stack or enterprise-style requests.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _coerce_swarm_output_to_str(val: Any) -> str:
    """Normalize agent/LLM payload to a string (Anthropic/OpenAI may return dict or block lists)."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        if isinstance(val.get("text"), str):
            return val["text"]
        c = val.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            parts: List[str] = []
            for block in c:
                if isinstance(block, dict):
                    if block.get("type") == "text" and isinstance(block.get("text"), str):
                        parts.append(block["text"])
                    elif isinstance(block.get("content"), str):
                        parts.append(block["content"])
                elif isinstance(block, str):
                    parts.append(block)
            if parts:
                return "\n".join(parts)
        for key in ("output", "result", "message"):
            inner = val.get(key)
            if isinstance(inner, str) and inner:
                return inner
            if isinstance(inner, (dict, list)):
                nested = _coerce_swarm_output_to_str(inner)
                if nested:
                    return nested
        try:
            return json.dumps(val, ensure_ascii=False)
        except Exception:
            return str(val)
    if isinstance(val, list):
        return _coerce_swarm_output_to_str({"content": val})
    return str(val)


def _extract_artifact_from_llm_output(
    llm_response: str, artifact_path: str
) -> str:
    """
    Extract actual code/JSON content from LLM prose.
    
    LLM might say: "Here's the search config:
    ```json
    { "index": "elasticsearch", ... }
    ```"
    
    We extract the content from code fences if present, or return response as-is.
    """
    ext = os.path.splitext(artifact_path)[1].lower()
    
    if ext == ".json":
        # Try to find ```json...``` or just ```...``` block (more flexible)
        # Matches: ```json\n...\n``` or ```\n...\n``` with various whitespace
        patterns = [
            r'```(?:json)?\s*\n(.*?)\n```',  # Original
            r'```\n(.*?)\n```',  # Just backticks
            r'```json\s*(.*?)\s*```',  # json without enforced newlines
            r'```\s*(.*?)\s*```',  # Generic backticks
        ]
        
        for pattern in patterns:
            match = re.search(pattern, llm_response, re.DOTALL)
            if match:
                candidate = match.group(1).strip()
                if candidate:
                    try:
                        json.loads(candidate)  # Validate
                        logger.info("JSON extracted from code fence: %d chars", len(candidate))
                        return candidate
                    except json.JSONDecodeError as e:
                        logger.debug("JSON validation failed for extracted content: %s", e)
                        continue
        
        # Try to parse entire response as JSON
        try:
            result = json.loads(llm_response)
            logger.info("JSON parsed from full response: %d chars", len(llm_response))
            return llm_response.strip()
        except json.JSONDecodeError:
            pass
        
        # Fallback: extract any {....} block from response
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', llm_response, re.DOTALL)
        if json_match:
            candidate = json_match.group(0).strip()
            try:
                json.loads(candidate)
                logger.info("JSON extracted from curly braces: %d chars", len(candidate))
                return candidate
            except json.JSONDecodeError:
                pass
        
        # Last resort: return minimal valid JSON without scaffold markers.
        logger.warning("Unable to extract JSON from LLM output, using empty object")
        return "{}"
    
    elif ext in (".js", ".jsx", ".ts", ".tsx"):
        # Extract ```javascript...``` or ```js...``` or just ```...```
        patterns = [
            r'```(?:javascript|jsx|js|typescript|tsx)\s*\n(.*?)\n```',
            r'```\n(.*?)\n```',
            r'```(?:javascript|jsx|js|typescript|tsx)\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, llm_response, re.DOTALL)
            if match:
                code = match.group(1).strip()
                if code:
                    # Reject garbage: markdown headings, file path prefixes, Python imports
                    first_line = code.split('\n')[0].strip()
                    fl_lower = first_line.lower()
                    is_garbage = (
                        first_line.startswith(('####', '###', '##', '# ', '`'))
                        or fl_lower.startswith(('import ', 'from ', 'server/', 'src/', 'backend/', 'frontend/'))
                        or (len(first_line) > 0 and first_line[0].isalpha() and ': ' in first_line and not first_line.startswith(('const ', 'let ', 'var ', 'function ', 'export ', 'import ', 'class ', 'type ', 'interface ')))
                    )
                    if is_garbage:
                        logger.debug("Garbage detected in JS artifact, skipping fence block: %r", first_line[:60])
                        continue
                    logger.info("Code extracted from fence: %d chars", len(code))
                    return code
        
        # If no code fence, check if response looks like code
        cleaned = llm_response.strip()
        if cleaned and not cleaned.startswith(("Here", "The", "This", "I've", "Based", "Sure", "#", "`")):
            first_line = cleaned.split('\n')[0].strip()
            fl_lower = first_line.lower()
            is_garbage = (
                first_line.startswith(('####', '###', '##', '`'))
                or fl_lower.startswith(('import ', 'from ', 'server/', 'src/', 'backend/'))
            )
            if not is_garbage:
                logger.info("Code extracted from prose: %d chars", len(cleaned))
                return cleaned
        
        logger.warning("Unable to extract JS code, using placeholder")
        return "// Auto-generated placeholder\n"
    
    elif ext == ".sql":
        match = re.search(
            r'```(?:sql)?\s*\n?(.*?)\n?```',
            llm_response,
            re.DOTALL
        )
        if match:
            return match.group(1).strip()
        cleaned = llm_response.strip()
        if cleaned and cleaned.upper().startswith(("SELECT", "CREATE", "ALTER", "INSERT", "UPDATE")):
            return cleaned
        return "-- Auto-generated placeholder\n"
    
    elif ext == ".md":
        # Markdown: just use the response as-is
        return llm_response.strip() or "# Generated\n"
    
    elif ext == ".yaml" or ext == ".yml":
        # Try to find ```yaml...``` block
        match = re.search(r'```(?:yaml|yml)?\s*\n?(.*?)\n?```', llm_response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return llm_response.strip() or "# placeholder: true\n"
    
    elif ext in (".sh", ".bash"):
        match = re.search(
            r'```(?:bash|sh)?\s*\n?(.*?)\n?```',
            llm_response,
            re.DOTALL
        )
        if match:
            return match.group(1).strip()
        return llm_response.strip() or "#!/bin/bash\n"
    
    elif ext in (".py", ".python"):
        match = re.search(
            r'```(?:python|py)?\s*\n?(.*?)\n?```',
            llm_response,
            re.DOTALL
        )
        if match:
            return match.group(1).strip()
        return llm_response.strip() or "# Auto-generated\n"
    
    else:
        # Generic: return response stripped
        return llm_response.strip() if llm_response.strip() else ""

try:
    from backend.agent_dag import _AGENT_RELEVANT_DEPS, AGENT_DAG, get_execution_phases
    from backend.agent_resilience import get_criticality
except ImportError:
    # Fallback for direct execution
    from agent_dag import _AGENT_RELEVANT_DEPS, AGENT_DAG, get_execution_phases
    from agent_resilience import get_criticality

from .agent_selection_logic import (
    BASE_AGENTS,
    build_full_phases_from_dag,
    select_agents_for_goal,
)
from .runtime_state import get_steps, load_checkpoint

SWARM_STEP_PREFIX = "agents"

# ---------------------------------------------------------------------------
# Per-agent model tier classification
# ---------------------------------------------------------------------------
# "anthropic" = deep reasoning tasks (architecture, planning, multi-file generation,
#               security, auth, database schema, final audit)
# "cerebras"  = fast tasks (boilerplate, config, docs, simple writes, export agents)
#
# IMPORTANT: Anthropic has NO credits on Railway — every "anthropic" agent MUST
# have Cerebras as a real fallback so the build never hard-fails.
# ---------------------------------------------------------------------------
AGENT_MODEL_TIER: Dict[str, str] = {
    # ── DEEP REASONING (Anthropic primary, Cerebras fallback) ──────────────
    "Planner": "anthropic",
    "Requirements Clarifier": "anthropic",
    "Stack Selector": "anthropic",
    "Frontend Generation": "anthropic",
    "Backend Generation": "anthropic",
    "Database Agent": "anthropic",
    "Auth Setup Agent": "anthropic",
    "Security Checker": "anthropic",
    "API Integration": "anthropic",
    "Payment Setup Agent": "anthropic",
    "Multi-tenant Agent": "anthropic",
    "RBAC Agent": "anthropic",
    "SSO Agent": "anthropic",
    "GraphQL Agent": "anthropic",
    "WebSocket Agent": "anthropic",
    "Migration Agent": "anthropic",
    "Schema Validation Agent": "anthropic",
    "E2E Agent": "anthropic",
    "Penetration Test Agent": "anthropic",
    "Incident Response Agent": "anthropic",
    "HIPAA Agent": "anthropic",
    "SOC2 Agent": "anthropic",
    "Deployment Agent": "anthropic",
    "DevOps Agent": "anthropic",
    "Workflow Agent": "anthropic",
    "Queue Agent": "anthropic",
    "Test Generation": "anthropic",
    "Test Executor": "anthropic",
    "Code Review Agent": "anthropic",
    "Error Recovery": "anthropic",
    "Validation Agent": "anthropic",
    # ── FAST / SIMPLE (Cerebras primary, Anthropic fallback) ───────────────
    "Native Config Agent": "cerebras",
    "Store Prep Agent": "cerebras",
    "Image Generation": "cerebras",
    "Video Generation": "cerebras",
    "UX Auditor": "cerebras",
    "Performance Analyzer": "cerebras",
    "Memory Agent": "cerebras",
    "PDF Export": "cerebras",
    "Excel Export": "cerebras",
    "Markdown Export": "cerebras",
    "Scraping Agent": "cerebras",
    "Automation Agent": "cerebras",
    "Design Agent": "cerebras",
    "Layout Agent": "cerebras",
    "SEO Agent": "cerebras",
    "Content Agent": "cerebras",
    "Brand Agent": "cerebras",
    "Documentation Agent": "cerebras",
    "Monitoring Agent": "cerebras",
    "Accessibility Agent": "cerebras",
    "Webhook Agent": "cerebras",
    "Email Agent": "cerebras",
    "Legal Compliance Agent": "cerebras",
    "i18n Agent": "cerebras",
    "Caching Agent": "cerebras",
    "Rate Limit Agent": "cerebras",
    "Search Agent": "cerebras",
    "Analytics Agent": "cerebras",
    "API Documentation Agent": "cerebras",
    "Mobile Responsive Agent": "cerebras",
    "Backup Agent": "cerebras",
    "Notification Agent": "cerebras",
    "Design Iteration Agent": "cerebras",
    "Staging Agent": "cerebras",
    "A/B Test Agent": "cerebras",
    "Feature Flag Agent": "cerebras",
    "Error Boundary Agent": "cerebras",
    "Logging Agent": "cerebras",
    "Metrics Agent": "cerebras",
    "Audit Trail Agent": "cerebras",
    "Session Agent": "cerebras",
    "OAuth Provider Agent": "cerebras",
    "2FA Agent": "cerebras",
    "Braintree Subscription Agent": "cerebras",
    "Invoice Agent": "cerebras",
    "CDN Agent": "cerebras",
    "SSR Agent": "cerebras",
    "Bundle Analyzer Agent": "cerebras",
    "Lighthouse Agent": "cerebras",
    "Mock API Agent": "cerebras",
    "Load Test Agent": "cerebras",
    "Dependency Audit Agent": "cerebras",
    "License Agent": "cerebras",
    "Terms Agent": "cerebras",
    "Privacy Policy Agent": "cerebras",
    "Cookie Consent Agent": "cerebras",
    "Audit Export Agent": "cerebras",
    "Data Residency Agent": "cerebras",
    "SLA Agent": "cerebras",
    "Cost Optimizer Agent": "cerebras",
    "Accessibility WCAG Agent": "cerebras",
    "RTL Agent": "cerebras",
    "Dark Mode Agent": "cerebras",
    "Keyboard Nav Agent": "cerebras",
    "Screen Reader Agent": "cerebras",
    "Component Library Agent": "cerebras",
    "Design System Agent": "cerebras",
    "Animation Agent": "cerebras",
    "Chart Agent": "cerebras",
    "Table Agent": "cerebras",
    "Form Builder Agent": "cerebras",
    "File Tool Agent": "cerebras",
}


def _primary_llm_is_cerebras() -> bool:
    """When True, Cerebras is tried before Anthropic for every agent (testing / free tier).

    Set PRIMARY_LLM_PROVIDER=cerebras (or CRUCIB_PRIMARY_LLM=cerebras). Default is
    task-tier routing (Anthropic first for deep-reasoning agents when keys exist).
    Remove or set to anthropic to restore normal production order.
    """
    v = (
        os.environ.get("PRIMARY_LLM_PROVIDER", "")
        or os.environ.get("CRUCIB_PRIMARY_LLM", "")
    ).strip().lower()
    return v in ("cerebras", "cerebra", "cb")


def _get_agent_model_chain(
    agent_name: str,
    effective: Dict[str, Any],
) -> List[Dict[str, str]]:
    """
    Build the model chain for a specific agent based on AGENT_MODEL_TIER.

    Anthropic agents: [anthropic, cerebras] — deep reasoning first, fast fallback
    Cerebras agents:  [cerebras, anthropic] — fast first, deep fallback

    IMPORTANT: Anthropic has NO credits on Railway. If Anthropic fails, Cerebras
    MUST be in the chain so the build continues. Never return an Anthropic-only chain.

    PRIMARY_LLM_PROVIDER=cerebras — put Cerebras first for *all* tiers (free testing;
    Anthropic remains as fallback when the key is set).
    """
    from ..llm_router import CEREBRAS_MODEL
    from ..anthropic_models import ANTHROPIC_HAIKU_MODEL

    cerebras_key = (effective or {}).get("cerebras") or os.environ.get("CEREBRAS_API_KEY")
    anthropic_key = (effective or {}).get("anthropic") or os.environ.get("ANTHROPIC_API_KEY")

    cerebras_entry = {"provider": "cerebras", "model": CEREBRAS_MODEL}
    anthropic_entry = {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL}

    tier = AGENT_MODEL_TIER.get(agent_name, "cerebras")  # default to fast
    force_cerebras_first = _primary_llm_is_cerebras()

    if force_cerebras_first:
        # Same order as "cerebras tier": fast first, Claude when needed / on failure
        chain = []
        if cerebras_key:
            chain.append(cerebras_entry)
        if anthropic_key:
            chain.append(anthropic_entry)
        return chain if chain else [anthropic_entry]

    if tier == "anthropic":
        # Anthropic primary — but always include Cerebras as fallback
        chain = []
        if anthropic_key:
            chain.append(anthropic_entry)
        if cerebras_key:
            chain.append(cerebras_entry)
        # If neither key is set, return empty (will raise downstream)
        return chain if chain else [cerebras_entry]
    else:
        # Cerebras primary — Anthropic as fallback if key exists
        chain = []
        if cerebras_key:
            chain.append(cerebras_entry)
        if anthropic_key:
            chain.append(anthropic_entry)
        return chain if chain else [anthropic_entry]


_COMPLEX_SWARM_MARKERS = (
    "helios aegis command",
    "aegis omega",
    "elite autonomous system test",
    "crm",
    "quote workflow",
    "project workflow",
    "policy engine",
    "immutable audit",
    "compliance",
    "tenant isolation",
    "multi-tenant",
    "background jobs",
    "worker/job system",
    "integration adapters",
    "analytics/reporting",
)
_CORE_NO_FALLBACK_AGENTS = frozenset(
    {
        "Planner",
        "Requirements Clarifier",
        "Stack Selector",
        "Frontend Generation",
        "Backend Generation",
        "Database Agent",
        "File Tool Agent",
    }
)


def slugify_agent_name(agent_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (agent_name or "").strip().lower())
    return slug.strip("_") or "agent"


def swarm_step_key(agent_name: str) -> str:
    return f"{SWARM_STEP_PREFIX}.{slugify_agent_name(agent_name)}"


def uses_agent_swarm(goal: str, stack_contract: Dict[str, Any] | None = None) -> bool:
    goal_lc = (goal or "").lower()
    contract = stack_contract or {}
    if contract.get("requires_full_system_builder"):
        return True
    hit_count = sum(1 for marker in _COMPLEX_SWARM_MARKERS if marker in goal_lc)
    return hit_count >= 4


def build_agent_swarm_phases(
    goal: str = "",
    stack_contract: Dict[str, Any] | None = None,
    selected_agents: List[str] | None = None,
) -> List[Dict[str, Any]]:
    phases: List[Dict[str, Any]] = []
    chosen_agents = selected_agents
    if chosen_agents is None:
        chosen_agents = (
            select_agents_for_goal(goal, stack_contract)
            if goal
            else list(AGENT_DAG.keys())
        )

    filtered = {name: AGENT_DAG[name] for name in chosen_agents if name in AGENT_DAG}
    phase_groups = (
        build_full_phases_from_dag(list(filtered.keys()), AGENT_DAG)
        if filtered
        else get_execution_phases(AGENT_DAG)
    )

    for idx, agent_names in enumerate(phase_groups, start=1):
        steps = []
        for agent_name in agent_names:
            deps = [
                swarm_step_key(dep)
                for dep in AGENT_DAG.get(agent_name, {}).get("depends_on", [])
                if dep in AGENT_DAG
            ]
            prompt = (AGENT_DAG.get(agent_name, {}).get("system_prompt") or "").strip()
            description = (
                prompt.splitlines()[0][:180] if prompt else f"Run {agent_name}"
            )
            steps.append(
                {
                    "key": swarm_step_key(agent_name),
                    "agent": agent_name,
                    "name": agent_name,
                    "description": description,
                    "depends_on": deps,
                }
            )
        phases.append(
            {
                "key": f"{SWARM_STEP_PREFIX}.phase_{idx:02d}",
                "label": f"Agent Swarm {idx:02d}",
                "steps": steps,
            }
        )
    return phases


def _safe_user_ref(user_id: str | None) -> Dict[str, str] | None:
    if user_id:
        return {"id": user_id}
    return None


def _workspace_file_snapshot(workspace_path: str) -> Dict[str, str]:
    snapshot: Dict[str, str] = {}
    if not workspace_path or not os.path.isdir(workspace_path):
        return snapshot
    for root, _, files in os.walk(workspace_path):
        for name in files:
            full = os.path.join(root, name)
            try:
                rel = os.path.relpath(full, workspace_path).replace("\\", "/")
                stat = os.stat(full)
                digest = hashlib.sha256(
                    f"{stat.st_mtime_ns}:{stat.st_size}".encode("utf-8")
                ).hexdigest()
                snapshot[rel] = digest
            except OSError:
                continue
    return snapshot


async def _load_previous_agent_outputs(
    job_id: str, current_step: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    previous_outputs: Dict[str, Dict[str, Any]] = {}
    try:
        all_steps = await get_steps(job_id)
    except Exception:
        return previous_outputs
    current_order = int(current_step.get("order_index") or 0)
    for step in all_steps:
        if not str(step.get("step_key") or "").startswith(f"{SWARM_STEP_PREFIX}."):
            continue
        if int(step.get("order_index") or 0) >= current_order:
            continue
        if step.get("status") != "completed":
            continue
        try:
            checkpoint = await load_checkpoint(job_id, step["step_key"])
        except Exception:
            checkpoint = None
        if not checkpoint:
            continue
        agent_name = (
            step.get("agent_name") or checkpoint.get("agent_name") or step["step_key"]
        )
        result = checkpoint.get("result")
        if isinstance(result, dict):
            previous_outputs[agent_name] = result
            continue
        output = checkpoint.get("output") or ""
        previous_outputs[agent_name] = {
            "output": output,
            "result": output,
            "status": checkpoint.get("status") or "completed",
        }
    return previous_outputs


async def _run_server_swarm_agent(
    *,
    project_id: str,
    user_id: str,
    agent_name: str,
    project_prompt: str,
    build_kind: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    workspace_path: str = "",
) -> Dict[str, Any]:
    # FIX: was `import server` (broken — no top-level `server` module when
    # PYTHONPATH=/app:/app/backend; `backend/server.py` is at `backend.server`).
    # FIX: was `server._run_single_agent_with_retry` which does not exist.
    # Correct function is `server._run_single_agent_with_context`.
    from backend import server as _srv
    user_ref = _safe_user_ref(user_id)
    user_keys = await _srv.get_workspace_api_keys(user_ref)
    effective = _srv._effective_api_keys(user_keys)

    # Per-agent model routing: deep agents get Anthropic primary (Cerebras fallback),
    # fast agents get Cerebras primary (Anthropic fallback).
    # IMPORTANT: Anthropic has no credits on Railway — Cerebras is always in chain.
    model_chain = _get_agent_model_chain(agent_name, effective)
    if not model_chain:
        # Final safety fallback: use the legacy auto chain
        model_chain = _srv._get_model_chain(
            "auto",
            project_prompt,
            effective_keys=effective,
            force_complex=False,
        )

    tier = AGENT_MODEL_TIER.get(agent_name, "cerebras")
    logger.info(
        "agent_model_routing: agent=%s tier=%s chain=%s",
        agent_name,
        tier,
        [c.get("provider") for c in model_chain],
    )

    return await _srv._run_single_agent_with_context(
        project_id=project_id,
        user_id=user_id,
        agent_name=agent_name,
        project_prompt=project_prompt,
        previous_outputs=previous_outputs,
        effective=effective,
        model_chain=model_chain,
        build_kind=build_kind,
        workspace_path=workspace_path,
    )


async def run_swarm_agent_step(
    step: Dict[str, Any], job: Dict[str, Any], workspace_path: str = ""
) -> Dict[str, Any]:
    """Execute one AGENT_DAG step through the existing server-side swarm runtime."""
    agent_name = step.get("agent_name") or step.get("name") or ""
    if agent_name not in AGENT_DAG:
        raise RuntimeError(f"unknown_swarm_agent:{agent_name}")

    job_id = job.get("id") or ""
    project_id = job.get("project_id") or job_id
    user_id = job.get("user_id") or ""
    project_prompt = (job.get("goal") or "").strip()
    build_kind = (job.get("build_kind") or "").strip().lower() or "fullstack"

    try:
        from .brain_policy import get_agent_governor_preface

        _gov = get_agent_governor_preface()
        if _gov and not project_prompt.startswith("[GOVERNOR"):
            project_prompt = f"{_gov}\n\n{project_prompt}"
    except Exception:
        pass

    previous_outputs = await _load_previous_agent_outputs(job_id, step)
    before = _workspace_file_snapshot(workspace_path)

    # Read brain repair mutations from step state
    use_minimal_context = step.get("use_minimal_context", False)
    context_reduce_factor = step.get("context_reduce_factor", None)
    force_model = step.get("force_model", None)
    enforce_code_only = step.get("enforce_code_only", False)
    prepend_instruction = step.get("prepend_system_instruction", "")
    retry_count_for_brain = step.get("retry_count", 0)

    # Apply context reduction if brain said so
    if use_minimal_context or context_reduce_factor is not None:
        factor = (
            float(context_reduce_factor) if context_reduce_factor is not None else 0.3
        )
        # Rebuild previous_outputs with reduced context
        relevant = _AGENT_RELEVANT_DEPS.get(agent_name, list(previous_outputs.keys()))
        reduced_outputs = {}
        total = 0
        max_total = max(0, int(15000 * factor))
        for dep in relevant:
            if total >= max_total and max_total > 0:
                break
            if dep in previous_outputs:
                out = previous_outputs[dep]
                raw = out.get("output") or out.get("result") or out.get("code") or ""
                raw = _coerce_swarm_output_to_str(raw)
                if raw.strip():
                    per = int(3000 * factor) if factor > 0 else 0
                    reduced_outputs[dep] = {**out, "output": raw[:per]}
                    total += per
        if factor <= 0.0:
            reduced_outputs = {}  # Zero context
        previous_outputs = reduced_outputs
        logger.info(
            "brain_repair: %s retry=%d strategy=reduce_context factor=%.1f "
            "outputs=%d total_chars=%d",
            agent_name,
            retry_count_for_brain,
            factor,
            len(previous_outputs),
            total,
        )

    # If brain said switch model, set env for this call
    if force_model == "cerebras":
        os.environ["CRUCIBAI_FORCE_CEREBRAS"] = "1"
        logger.info(
            "brain_repair: %s retry=%d forcing Cerebras",
            agent_name,
            retry_count_for_brain,
        )
    else:
        os.environ.pop("CRUCIBAI_FORCE_CEREBRAS", None)

    # If brain wants code-only enforcement, modify project_prompt
    if enforce_code_only or prepend_instruction:
        prefix = prepend_instruction or (
            "CRITICAL: Output ONLY valid code. Start with the first line of code. "
            "No explanation, no preamble."
        )
        project_prompt = f"[SYSTEM CONSTRAINT] {prefix}\n\n{project_prompt}"

    # Initialize build memory on first agent (Planner) so all agents share context
    if agent_name == "Planner" and workspace_path:
        try:
            from .build_memory import init_build_memory
            init_build_memory(workspace_path, project_prompt, build_kind or "fullstack")
            logger.info("build_memory: initialized for job=%s", job_id)
        except Exception as _bm_err:
            logger.warning("build_memory init failed: %s", _bm_err)

    result = await _run_server_swarm_agent(
        project_id=project_id,
        user_id=user_id,
        agent_name=agent_name,
        project_prompt=project_prompt,
        build_kind=build_kind,
        previous_outputs=previous_outputs,
        workspace_path=workspace_path,
    )

    # Clean up forced model env
    os.environ.pop("CRUCIBAI_FORCE_CEREBRAS", None)

    status = str(result.get("status") or "").lower()
    if status in ("failed", "failed_with_fallback", "skipped"):
        criticality = get_criticality(agent_name)
        if agent_name in _CORE_NO_FALLBACK_AGENTS or criticality in (
            "critical",
            "high",
        ):
            raise RuntimeError(
                f"swarm_agent_failed:{agent_name}:{result.get('reason') or status}"
            )

    after = _workspace_file_snapshot(workspace_path)
    changed_files = sorted(
        rel for rel, digest in after.items() if before.get(rel) != digest
    )

    try:
        from backend.orchestration.workspace_assembly_pipeline import (
            assembly_v2_enabled,
            materialize_swarm_agent_output,
        )

        if assembly_v2_enabled() and workspace_path:
            extra_written = materialize_swarm_agent_output(
                workspace_path, agent_name, result
            )
            if extra_written:
                changed_files = sorted(set(changed_files + extra_written))
    except Exception as e:
        logger.warning("assembly v2 swarm materialize: %s", e)

    # === FIX: Materialize expected agent artifacts ===
    # Many agents define artifact paths in agent_real_behavior.py but don't write files.
    # Extract content from LLM response and write to workspace.
    try:
        from agent_real_behavior import ARTIFACT_PATHS
        
        if workspace_path and agent_name in ARTIFACT_PATHS:
            artifact_rel_path = ARTIFACT_PATHS[agent_name]
            llm_output = _coerce_swarm_output_to_str(
                result.get("output") or result.get("result") or ""
            )

            logger.info(
                "artifact_materialization: agent=%s path=%s output_size=%d",
                agent_name,
                artifact_rel_path,
                len(llm_output) if llm_output else 0
            )

            if llm_output and llm_output.strip():
                extracted = _extract_artifact_from_llm_output(
                    llm_output, artifact_rel_path
                )
                logger.info(
                    "artifact_extraction: agent=%s extracted_size=%d",
                    agent_name,
                    len(extracted) if extracted else 0
                )
                
                if extracted:
                    # Route through _safe_write so all language/garbage guards apply
                    # Lazy import to avoid circular import with executor.py
                    from .executor import _safe_write as _sw
                    written = _sw(workspace_path, artifact_rel_path, extracted)
                    if written:
                        if artifact_rel_path not in changed_files:
                            changed_files.append(artifact_rel_path)
                        logger.info(
                            "materialize_agent_artifact_SUCCESS: %s -> %s (%d bytes)",
                            agent_name,
                            artifact_rel_path,
                            len(extracted),
                        )
                    else:
                        logger.warning(
                            "materialize_agent_artifact_REJECTED: agent=%s path=%s — garbage/prose content blocked by _safe_write",
                            agent_name,
                            artifact_rel_path,
                        )
                else:
                    logger.warning(
                        "artifact_extraction_returned_empty: agent=%s path=%s",
                        agent_name,
                        artifact_rel_path
                    )
            else:
                logger.warning(
                    "no_llm_output_for_artifact: agent=%s path=%s",
                    agent_name,
                    artifact_rel_path
                )
    except ImportError:
        logger.debug("agent_real_behavior not available for artifact materialization")
    except Exception as e:
        logger.exception("artifact materialization error: %s", e)

    artifact_path = f"outputs/{slugify_agent_name(agent_name)}.md"
    artifacts = []
    if workspace_path and os.path.isfile(
        os.path.join(workspace_path, artifact_path.replace("/", os.sep))
    ):
        artifacts.append(
            {"kind": "agent_output", "path": artifact_path, "agent": agent_name}
        )

    # Record agent files and model decision into build memory
    if workspace_path and changed_files:
        try:
            from .build_memory import record_agent_files, record_model_decision
            record_agent_files(workspace_path, agent_name, changed_files)
            # Record which model tier was used
            tier = AGENT_MODEL_TIER.get(agent_name, "cerebras")
            record_model_decision(workspace_path, agent_name, tier)
            logger.info(
                "build_memory: recorded %d files for agent=%s",
                len(changed_files),
                agent_name,
            )
        except Exception as _bm_err:
            logger.warning("build_memory record failed: %s", _bm_err)

    # Parse Planner output to extract build_type and complexity into memory
    if agent_name == "Planner" and workspace_path:
        try:
            from .build_memory import update_build_memory
            llm_out = _coerce_swarm_output_to_str(
                result.get("output") or result.get("result") or ""
            )
            _updates: dict = {}
            # Detect build type from planner output
            _out_lower = llm_out.lower()
            for _bt in ("saas", "ecommerce", "mobile", "api", "fullstack", "frontend", "backend"):
                if _bt in _out_lower:
                    _updates["build_type"] = _bt
                    break
            if _updates:
                update_build_memory(workspace_path, _updates)
        except Exception as _bm_err:
            logger.warning("build_memory planner parse failed: %s", _bm_err)

    # Parse Stack Selector output to extract stack into memory
    if agent_name == "Stack Selector" and workspace_path:
        try:
            from .build_memory import update_build_memory
            import json as _json
            llm_out = _coerce_swarm_output_to_str(
                result.get("output") or result.get("result") or ""
            )
            # Try to parse JSON stack from output
            _stack_match = re.search(r'\{[^{}]*(?:frontend|backend|database)[^{}]*\}', llm_out, re.DOTALL | re.IGNORECASE)
            if _stack_match:
                try:
                    _stack_data = _json.loads(_stack_match.group(0))
                    _stack = {}
                    for _k in ("frontend", "backend", "database", "auth", "deploy", "deployment"):
                        if _k in _stack_data:
                            _stack[_k] = str(_stack_data[_k])
                    if _stack:
                        update_build_memory(workspace_path, {"stack": _stack})
                except Exception:
                    pass
        except Exception as _bm_err:
            logger.warning("build_memory stack parse failed: %s", _bm_err)

    return {
        "output": _coerce_swarm_output_to_str(
            result.get("output") or result.get("result") or ""
        ),
        "result": result,
        "output_files": changed_files,
        "artifacts": artifacts,
        "agent_name": agent_name,
        "execution_mode": "agent_swarm",
        "previous_output_count": len(previous_outputs),
    }

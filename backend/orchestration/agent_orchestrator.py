"""
Crew-style multi-agent orchestration (stubs) — complements the DAG executor.

Runs lightweight, deterministic "agent" steps without LLM calls by default; swap Agent.execute
for a model call when keys are configured. Writes markdown/SQL sketches into the job workspace.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, List, Optional

from .domain_packs import fintech_intent, healthcare_intent, marketplace_intent

logger = logging.getLogger(__name__)


class Agent:
    """Single agent: role/goal/backstory + optional tools (callables)."""

    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        tools: Optional[List[Callable[..., Any]]] = None,
    ):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Stub reasoning — returns structured text for downstream tasks."""
        snippet = (task or "")[:120]
        elite = (
            (context.get("elite_system_prompt") or context.get("system_prompt") or "")
            .strip()
        )
        digest = ""
        if elite:
            digest = (
                f"\n\n### Execution authority digest (first 900 chars of system prompt)\n\n"
                f"```\n{elite[:900]}\n```\n"
            )
        return {
            "role": self.role,
            "content": (
                f"## {self.role}\n\n**Task:** {snippet}\n\n"
                f"**Goal:** {self.goal}\n"
                f"{digest}\n"
                f"_Stub agent: wire LLM here; execution authority above is already in model-bound payload when provided._\n"
            ),
            "context_echo": {k: (str(context.get(k) or "")[:200]) for k in context},
        }


class Task:
    """Unit of work; `output_key` stores result on shared context for later tasks."""

    def __init__(
        self,
        description: str,
        expected_output: str,
        agent: Agent,
        context_keys: Optional[List[str]] = None,
        output_key: str = "step",
    ):
        self.description = description
        self.expected_output = expected_output
        self.agent = agent
        self.context_keys = context_keys or []
        self.output_key = output_key


class Crew:
    """Sequential crew — pass context forward like a simple pipeline."""

    def __init__(self, agents: List[Agent], tasks: List[Task], verbose: bool = False):
        self.agents = agents
        self.tasks = tasks
        self.verbose = verbose

    async def kickoff(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        context = dict(inputs)
        outputs: List[Dict[str, Any]] = []
        for task in self.tasks:
            if self.verbose:
                logger.info("crew: %s → %s", task.agent.role, task.description[:80])
            task_context = {k: context.get(k) for k in task.context_keys}
            for inj in ("system_prompt", "elite_system_prompt"):
                if inj in context and inj not in task_context:
                    task_context[inj] = context.get(inj)
            result = await task.agent.execute(task.description, task_context)
            outputs.append(result)
            text = (result.get("content") or "").strip()
            context[task.output_key] = text
        return {"final": outputs, "context": context}


def architect_crew(_goal: str) -> Crew:
    architect = Agent(
        role="System Architect",
        goal="Design a scalable multi-tenant SaaS architecture",
        backstory="Cloud native, RLS, API boundaries.",
    )
    data_modeler = Agent(
        role="Data Modeler",
        goal="PostgreSQL schema with tenant isolation",
        backstory="RLS, migrations, indexing.",
    )
    api_designer = Agent(
        role="API Designer",
        goal="REST/OpenAPI surface for core CRUD",
        backstory="Versioning, auth, and error contracts.",
    )
    tasks = [
        Task(
            "Define tenancy, auth, and deployment boundaries",
            "Architecture.md",
            architect,
            [],
            "architecture",
        ),
        Task(
            "Outline SQL tables with tenant_id and RLS policies",
            "schema.sql",
            data_modeler,
            ["architecture"],
            "schema",
        ),
        Task(
            "List core REST resources and status codes",
            "openapi.md",
            api_designer,
            ["schema"],
            "openapi",
        ),
    ]
    return Crew([architect, data_modeler, api_designer], tasks, verbose=True)


def fintech_crew(_goal: str) -> Crew:
    compliance = Agent(
        role="Fintech Compliance",
        goal="PCI scope reduction and ledger safety",
        backstory="Idempotent payments, audit trail, no PAN in logs.",
    )
    ledger = Agent(
        role="Ledger Architect",
        goal="Double-entry friendly balances",
        backstory="Accounts, postings, reconciliation hooks.",
    )
    tasks = [
        Task(
            "Record PCI/PSD2-style considerations for card data",
            "compliance_notes.md",
            compliance,
            [],
            "architecture",
        ),
        Task(
            "Draft ledger + payment_event tables (comments only)",
            "schema.sql",
            ledger,
            ["architecture"],
            "schema",
        ),
    ]
    return Crew([compliance, ledger], tasks, verbose=True)


def healthcare_crew(_goal: str) -> Crew:
    clinical = Agent(
        role="Clinical Data",
        goal="PHI minimization and access logging",
        backstory="HIPAA-oriented patterns; no medical advice.",
    )
    schema = Agent(
        role="Healthcare Schema",
        goal="Patient pseudonym + encounter model",
        backstory="Consent, retention, audit.",
    )
    tasks = [
        Task(
            "Summarize PHI handling checklist",
            "hipaa_notes.md",
            clinical,
            [],
            "architecture",
        ),
        Task(
            "Sketch patient/encounter tables (comments only)",
            "schema.sql",
            schema,
            ["architecture"],
            "schema",
        ),
    ]
    return Crew([clinical, schema], tasks, verbose=True)


def marketplace_crew(_goal: str) -> Crew:
    ops = Agent(
        role="Marketplace Ops",
        goal="Listings, orders, payouts",
        backstory="Seller verification, disputes, commissions.",
    )
    schema = Agent(
        role="Marketplace Schema",
        goal="Orders and inventory",
        backstory="Idempotent checkout, payout idempotency keys.",
    )
    tasks = [
        Task(
            "Define marketplace actors and money flow",
            "marketplace.md",
            ops,
            [],
            "architecture",
        ),
        Task(
            "Sketch listings/orders/payouts (comments only)",
            "schema.sql",
            schema,
            ["architecture"],
            "schema",
        ),
    ]
    return Crew([ops, schema], tasks, verbose=True)


def _select_crew(goal: str) -> Crew:
    if fintech_intent(goal):
        return fintech_crew(goal)
    if healthcare_intent(goal):
        return healthcare_crew(goal)
    if marketplace_intent(goal):
        return marketplace_crew(goal)
    return architect_crew(goal)


async def run_crew_for_goal(
    goal: str,
    workspace_path: str,
    *,
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a crew for the goal and write artifacts under workspace_path.
    Optional ``system_prompt`` is injected into kickoff inputs for future LLM-backed agents
    and is recorded under proof/ when non-empty.
    Returns {written: [...], crew: kickoff result}.
    """
    if not workspace_path or not os.path.isdir(workspace_path):
        return {"written": [], "crew": {}, "skipped": True}

    crew = _select_crew(goal or "")
    kick_inputs: Dict[str, Any] = {"goal": goal or "", "workspace": workspace_path}
    if system_prompt and str(system_prompt).strip():
        sp = str(system_prompt).strip()
        kick_inputs["system_prompt"] = sp
        kick_inputs["elite_system_prompt"] = sp
    result = await crew.kickoff(kick_inputs)
    ctx = result.get("context") or {}

    written: List[str] = []

    def _write(rel: str, body: str) -> None:
        full = os.path.normpath(os.path.join(workspace_path, rel.replace("/", os.sep)))
        root = os.path.normpath(workspace_path)
        if not full.startswith(root):
            return
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(body)
        written.append(rel.replace("\\", "/"))

    arch = (ctx.get("architecture") or "").strip()
    if arch:
        _write("docs/CREW_ARCHITECTURE.md", arch)

    schema = (ctx.get("schema") or "").strip()
    if schema:
        sql = (
            "-- CrucibAI crew schema sketch (non-executable comments — replace with real migrations)\n\n"
            + schema
            + "\n"
        )
        _write("db/migrations/000_crew_schema.sql", sql)

    openapi = (ctx.get("openapi") or "").strip()
    if openapi:
        _write("docs/CREW_OPENAPI_SKETCH.md", openapi)

    sp = (kick_inputs.get("system_prompt") or "").strip()
    if sp:
        try:
            from .elite_prompt_loader import elite_prompt_fingerprint

            fp = elite_prompt_fingerprint(sp)
            excerpt = sp[:4096] + ("\n\n… [truncated]\n" if len(sp) > 4096 else "")
            body = (
                "# Elite execution directive (injected at planning.requirements)\n\n"
                "Full source: `config/agent_prompts/ELITE_AUTONOMOUS_PROMPT.md` in the CrucibAI repo.\n\n"
                f"SHA256 prefix: `{fp}`\n\n"
                "---\n\n"
                + excerpt
            )
            _write("proof/ELITE_EXECUTION_DIRECTIVE.md", body)
        except Exception as exc:
            logger.warning("crew: could not write proof/ELITE_EXECUTION_DIRECTIVE.md: %s", exc)

    return {"written": written, "crew": result, "skipped": False}

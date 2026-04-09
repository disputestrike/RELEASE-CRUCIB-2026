"""
BuilderAgent - elite directive injected into LLM system context before generation.
Uses workspace proof/ELITE_EXECUTION_DIRECTIVE.md + strict BUILD-mode system prompt.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry
from orchestration.generation_contract import parse_generation_contract

logger = logging.getLogger(__name__)


def _load_elite_directive(workspace: str) -> str:
    """Load the elite builder directive if it exists in the workspace."""
    if not (workspace or "").strip():
        return ""
    path = Path(workspace) / "proof" / "ELITE_EXECUTION_DIRECTIVE.md"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("BuilderAgent: could not read elite directive: %s", e)
            return ""
    return ""


def _parse_build_intent(goal: str) -> Dict[str, Any]:
    """Separate build instructions from content to display."""
    contract = parse_generation_contract(goal)
    if "BLACK-BELT OMEGA GAUNTLET" in goal:
        return {
            "mode": "BUILD",
            "target": "Helios Aegis Command",
            "spec": goal,
            "contract": contract,
            "instruction": (
                "Implement the Helios Aegis Command platform per the Black-Belt Omega Gauntlet spec. "
                "Output real code, not stubs. Enforce proof gates."
            ),
        }
    summary = "; ".join(contract.get("summary_lines") or []) or "Full system requested from prompt"
    return {
        "mode": "BUILD",
        "target": contract.get("product_name") or "unspecified",
        "spec": goal,
        "contract": contract,
        "instruction": (
            "Generate a real integrated system that satisfies the requested stack and services. "
            f"Requested stack summary: {summary}"
        ),
    }


def _spec_echo_blocked(response: str) -> bool:
    if not response:
        return False
    markers = (
        'const goal = "I MADE IT MORE DIFFICULT',
        "{goal}</p>",
    )
    return any(m in response for m in markers)


@AgentRegistry.register
class BuilderAgent(BaseAgent):
    """
    LLM-backed builder with elite directive prepended to system prompt.

    Context:
        - workspace_path: str (required)
        - goal or user_prompt: str - build spec / task text
    """

    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        if not (context.get("workspace_path") or "").strip():
            raise AgentValidationError(f"{self.name}: Missing required field 'workspace_path'")
        if not (context.get("goal") or context.get("user_prompt") or "").strip():
            raise AgentValidationError(f"{self.name}: Missing 'goal' or 'user_prompt'")
        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        if result.get("status") == "❌ CRITICAL BLOCK":
            return True
        required = ["files", "api_spec", "setup_instructions"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        if not isinstance(result["files"], dict):
            raise AgentValidationError(f"{self.name}: files must be a dictionary")
        if "endpoints" not in result.get("api_spec", {}):
            raise AgentValidationError(f"{self.name}: api_spec must have 'endpoints'")
        if not isinstance(result["setup_instructions"], list):
            raise AgentValidationError(f"{self.name}: setup_instructions must be a list")
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        workspace_path = (context.get("workspace_path") or "").strip()
        goal = (context.get("goal") or context.get("user_prompt") or "").strip()

        directive = _load_elite_directive(workspace_path)
        intent = _parse_build_intent(goal)

        system_prompt = f"""{directive}

[EXECUTION MODE] {intent["mode"]}
[TARGET PLATFORM] {intent["target"]}
[BUILD INSTRUCTION] {intent["instruction"]}
[STACK CONTRACT JSON]
{json.dumps(intent.get("contract") or {}, indent=2)}

[WORKSPACE] {workspace_path}
[MANDATORY]
- Output executable code, not stubs or placeholders
- Generate real files for every requested stack component you can implement in this run
- If the prompt asks for frontend, backend, data, infra, tests, and docs, emit all of them in one coherent file set
- Enforce proof/ gates before proceeding
- If you cannot implement a requested feature, return status ❌ CRITICAL BLOCK with a precise reason instead of silently degrading
- Never display the spec as content - implement it
- Prefer real framework/runtime files over explanatory markdown

[FAILURE CONDITIONS]
- Displaying spec text in UI = ❌ CRITICAL BLOCK
- Outputting "stub", "TODO", or placeholder comments in critical paths = ❌ CRITICAL BLOCK
- Skipping proof/ artifacts = ❌ CRITICAL BLOCK
- Returning only a scaffold when the prompt requested a larger integrated system = ❌ CRITICAL BLOCK

You are a senior full-stack builder. Respond with ONLY valid JSON in the same schema as production backend generation:
files, api_spec (with endpoints list), setup_instructions (list of strings).

The files object may include any needed folders such as:
- src/, app/, components/, pages/, hooks/, services/
- backend/, api/, server/, routes/, models/, workers/
- infra/, deploy/, kubernetes/, terraform/, .github/workflows/
- tests/, e2e/, docs/, db/, migrations/, seeds/
"""

        user_message = f"Build {intent['target']} per this goal and stack contract:\n\n{goal}"

        # Prefer injected client.chat when provided (tests / custom adapters)
        response_text: str
        tokens = 0
        if self.llm_client is not None and hasattr(self.llm_client, "chat"):
            chat_fn = getattr(self.llm_client, "chat")
            raw = await chat_fn(
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                temperature=0.1,
                max_tokens=8000,
            )
            if isinstance(raw, dict):
                response_text = raw.get("content") or raw.get("text") or json.dumps(raw)
            else:
                response_text = str(raw)
        else:
            response_text, tokens = await self.call_llm(
                user_prompt=user_message,
                system_prompt=system_prompt,
                model=context.get("llm_model") or "claude-haiku-4-5-20251001",
                temperature=0.1,
                max_tokens=min(8000, int(context.get("max_tokens") or 8000)),
                stream=context.get("stream", True),
            )

        if _spec_echo_blocked(response_text):
            return {
                "status": "❌ CRITICAL BLOCK",
                "reason": "Agent echoed spec as content instead of implementing it. Self-correct required.",
                "continuation": (
                    "Re-run with explicit instruction: 'Do not display the spec. Implement the platform.'"
                ),
            }

        data = self.parse_json_response(response_text)
        data["_tokens_used"] = tokens
        data["_agent"] = self.name
        data["_elite_directive_injected"] = bool(directive.strip())
        data["_build_target"] = intent["target"]
        return data

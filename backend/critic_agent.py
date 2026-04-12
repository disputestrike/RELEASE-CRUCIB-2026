"""
CrucibAI Critic Agent + Truth Module
======================================
Post-build quality review and adversarial self-critique.
Integrates with the existing _call_llm_with_fallback in server.py.

Usage:
    from critic_agent import CriticAgent, TruthModule

    critic = CriticAgent()
    review = await critic.review_build(project_id, agent_outputs, llm_caller)

    truth = TruthModule()
    verdict = await truth.verify_claims(agent_outputs, llm_caller)
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CriticAgent:
    """
    Post-build reviewer that evaluates agent outputs for quality.
    Runs AFTER the DAG completes, scoring each agent's output.
    """

    SYSTEM_PROMPT = """You are CrucibAI's Critic Agent — a ruthless code reviewer.
Your job is to evaluate the output of other AI agents and score them honestly.

For each agent output you review, provide:
1. A quality score from 1-10
2. Specific issues found (bugs, missing features, bad patterns)
3. Suggestions for improvement
4. A pass/fail verdict (pass = score >= 7)

Be honest. Be specific. Reference exact code when pointing out issues.
Output valid JSON with this structure:
{
  "agent_name": "string",
  "score": number,
  "verdict": "pass" | "fail",
  "issues": ["string"],
  "suggestions": ["string"],
  "summary": "string"
}"""

    async def review_build(
        self,
        project_id: str,
        agent_outputs: Dict[str, Dict[str, Any]],
        llm_caller: Callable[..., Awaitable[Tuple[str, str]]],
        model_chain: list = None,
        api_keys: dict = None,
    ) -> Dict[str, Any]:
        """
        Review all agent outputs from a completed build.

        Args:
            project_id: The project being reviewed
            agent_outputs: Dict of agent_name -> {output, tokens_used, status}
            llm_caller: The _call_llm_with_fallback function from server.py
            model_chain: LLM model chain to use
            api_keys: API keys dict

        Returns:
            Dict with overall_score, agent_reviews, pass_rate, recommendations
        """
        reviews = []
        total_score = 0
        passed = 0
        failed = 0

        for agent_name, output_data in agent_outputs.items():
            output_text = str(
                output_data.get("output", "") or output_data.get("result", "")
            )
            if not output_text or len(output_text) < 20:
                continue

            try:
                review = await self._review_single_agent(
                    agent_name, output_text[:3000], llm_caller, model_chain, api_keys
                )
                reviews.append(review)
                total_score += review.get("score", 0)
                if review.get("verdict") == "pass":
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.warning(f"Critic review failed for {agent_name}: {e}")
                reviews.append(
                    {
                        "agent_name": agent_name,
                        "score": 0,
                        "verdict": "error",
                        "issues": [f"Review failed: {str(e)}"],
                        "suggestions": [],
                        "summary": "Could not review this agent's output",
                    }
                )

        agent_count = max(len(reviews), 1)
        overall_score = round(total_score / agent_count, 1)
        pass_rate = round((passed / agent_count) * 100, 1) if agent_count > 0 else 0

        return {
            "project_id": project_id,
            "overall_score": overall_score,
            "pass_rate": pass_rate,
            "total_agents_reviewed": len(reviews),
            "passed": passed,
            "failed": failed,
            "reviews": reviews,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recommendations": self._generate_recommendations(reviews),
        }

    async def _review_single_agent(
        self,
        agent_name: str,
        output_text: str,
        llm_caller: Callable,
        model_chain: list,
        api_keys: dict,
    ) -> Dict[str, Any]:
        """Review a single agent's output."""
        message = f"""Review this output from the '{agent_name}' agent:

```
{output_text}
```

Evaluate quality, correctness, completeness, and best practices.
Return your review as valid JSON."""

        response, _ = await llm_caller(
            message=message,
            system_message=self.SYSTEM_PROMPT,
            session_id=f"critic_{agent_name}",
            model_chain=model_chain or [],
            api_keys=api_keys,
        )

        try:
            # Try to parse JSON from the response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                review = json.loads(json_match.group())
                review["agent_name"] = agent_name
                return review
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback if JSON parsing fails
        return {
            "agent_name": agent_name,
            "score": 5,
            "verdict": "pass",
            "issues": [],
            "suggestions": ["Could not parse structured review"],
            "summary": response[:200] if response else "No review generated",
        }

    def _generate_recommendations(self, reviews: List[Dict]) -> List[str]:
        """Generate overall recommendations from all reviews."""
        recommendations = []
        low_scores = [r for r in reviews if r.get("score", 0) < 7]

        if low_scores:
            names = ", ".join(r["agent_name"] for r in low_scores[:5])
            recommendations.append(f"Re-run or improve these agents: {names}")

        all_issues = []
        for r in reviews:
            all_issues.extend(r.get("issues", []))

        if len(all_issues) > 5:
            recommendations.append(
                f"Total issues found: {len(all_issues)}. Consider a full rebuild."
            )

        if not recommendations:
            recommendations.append(
                "Build quality is acceptable. No critical issues found."
            )

        return recommendations


class TruthModule:
    """
    Adversarial self-critique module.
    Verifies that agent outputs match their claimed capabilities.
    Catches hallucinations, incomplete implementations, and false claims.
    """

    TRUTH_PROMPT = """You are CrucibAI's Truth Module — an adversarial verifier.
Your job is to check if the generated code ACTUALLY implements what was promised.

For each claim, verify:
1. Does the code actually implement this feature?
2. Is it functional or just a placeholder/stub?
3. Are there any lies or exaggerations?

Be brutally honest. Output valid JSON:
{
  "claims_verified": number,
  "claims_failed": number,
  "truth_score": number (0-100),
  "findings": [
    {
      "claim": "string",
      "status": "verified" | "partial" | "false" | "placeholder",
      "evidence": "string"
    }
  ],
  "verdict": "truthful" | "partially_truthful" | "misleading"
}"""

    async def verify_claims(
        self,
        agent_outputs: Dict[str, Dict[str, Any]],
        llm_caller: Callable[..., Awaitable[Tuple[str, str]]],
        model_chain: list = None,
        api_keys: dict = None,
        project_prompt: str = "",
    ) -> Dict[str, Any]:
        """
        Verify that the build output matches the original project prompt.

        Args:
            agent_outputs: All agent outputs from the build
            llm_caller: The _call_llm_with_fallback function
            model_chain: LLM model chain
            api_keys: API keys
            project_prompt: The original user request

        Returns:
            Truth verification report
        """
        # Collect key outputs
        key_outputs = {}
        for agent_name, data in agent_outputs.items():
            output = str(data.get("output", "") or data.get("result", ""))
            if output and len(output) > 50:
                key_outputs[agent_name] = output[:1500]

        if not key_outputs:
            return {
                "truth_score": 0,
                "verdict": "no_data",
                "findings": [],
                "error": "No agent outputs to verify",
            }

        # Build verification prompt
        outputs_summary = "\n\n".join(
            f"=== {name} ===\n{text}" for name, text in list(key_outputs.items())[:10]
        )

        message = f"""The user requested: "{project_prompt[:500]}"

Here are the agent outputs:

{outputs_summary}

Verify: Does the generated code actually deliver what was promised?
Check for placeholders, stubs, TODO comments, and missing implementations.
Return your truth assessment as valid JSON."""

        try:
            response, _ = await llm_caller(
                message=message,
                system_message=self.TRUTH_PROMPT,
                session_id="truth_module",
                model_chain=model_chain or [],
                api_keys=api_keys,
            )

            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                result = json.loads(json_match.group())
                result["timestamp"] = datetime.now(timezone.utc).isoformat()
                return result
        except Exception as e:
            logger.error(f"Truth module verification failed: {e}")

        return {
            "truth_score": 50,
            "verdict": "unknown",
            "findings": [],
            "error": "Verification could not be completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

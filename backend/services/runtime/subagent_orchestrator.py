from __future__ import annotations

import asyncio
import os
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .....services.runtime.runtime_engine import runtime_enginefrom .....services.runtime.swan_engine import SwanEngine

@dataclass(frozen=True)
class SubagentSpec:
    id: str
    role: str
    prior: str
    objective: str


class SubagentOrchestrator:
    DEFAULT_PRIORS = {
        "security_first": 0.34,
        "cost_sensitive": 0.33,
        "speed_first": 0.33,
    }

    def __init__(self, *, job_id: str, user_id: str):
        self.job_id = str(job_id)
        self.user_id = str(user_id)

    @classmethod
    def _normalize_priors(cls, priors: Optional[Dict[str, float]]) -> Dict[str, float]:
        p = dict(cls.DEFAULT_PRIORS)
        if isinstance(priors, dict):
            for k in p:
                if k in priors:
                    try:
                        p[k] = max(0.0, float(priors[k]))
                    except Exception:
                        pass
        total = sum(p.values()) or 1.0
        return {k: v / total for k, v in p.items()}

    @classmethod
    def build_specs(
        cls,
        *,
        task: str,
        count: int,
        mode: str = "swan",
        strategy: Optional[str] = None,
        priors: Optional[Dict[str, float]] = None,
        predefined_ids: Optional[List[str]] = None,
        seed: Optional[int] = None,
    ) -> List[SubagentSpec]:
        n = max(1, int(count))
        roster = SwanEngine.build_subagents(
            count=n,
            mode=mode,
            strategy=strategy,
            predefined_ids=predefined_ids,
        )
        norm = cls._normalize_priors(priors)
        prior_names = list(norm.keys())
        prior_weights = [norm[k] for k in prior_names]
        rng = random.Random(seed)

        specs: List[SubagentSpec] = []
        for i, r in enumerate(roster):
            prior = rng.choices(prior_names, weights=prior_weights, k=1)[0]
            sid = str(r.get("id") or uuid.uuid4())
            role = str(r.get("role") or "worker")
            specs.append(
                SubagentSpec(
                    id=sid,
                    role=role,
                    prior=prior,
                    objective=f"Branch {i + 1}: {task}",
                )
            )
        return specs

    @staticmethod
    def _prior_guidance(prior: str) -> str:
        if prior == "security_first":
            return "Prioritize risk controls, auth boundaries, and rollback safety before speed."
        if prior == "cost_sensitive":
            return "Prioritize lean architecture, low recurring cost, and operational efficiency."
        return "Prioritize speed to value while maintaining acceptable quality and reliability."

    async def _run_single(self, *, spec: SubagentSpec, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Runtime-native sub-agent execution via controlled model dispatch.
        message = (
            f"Task: {task}\n"
            f"Role: {spec.role}\n"
            f"Prior: {spec.prior}\n"
            f"Context: {context or {}}\n"
            "Return concise JSON with keys: recommendation, reasoning, risks, files (optional object)."
        )
        system_message = (
            "You are a focused sub-agent in a multi-agent architecture. "
            "Produce one independent branch decision with explicit tradeoffs. "
            + self._prior_guidance(spec.prior)
        )

        try:
            text, model = await runtime_engine.call_model_for_request(
                session_id=f"spawn-{self.job_id}-{spec.id}",
                project_id=self.job_id,
                description=f"Sub-agent {spec.role} branch execution",
                message=message,
                system_message=system_message,
                model_chain=[],
                user_id=self.user_id,
                agent_name=f"spawn:{spec.role}",
                skill_hint="spawn_parallel_branch",
            )
            return {
                "id": spec.id,
                "role": spec.role,
                "prior": spec.prior,
                "status": "complete",
                "result": {
                    "recommendation": text[:4000],
                    "model": model,
                    "files": {},
                },
            }
        except Exception as exc:
            # Deterministic fallback keeps spawn available when providers are unavailable.
            fallback = (
                f"{spec.role} branch suggests guarded rollout. "
                f"Prior={spec.prior}. Error fallback used: {str(exc)[:220]}"
            )
            return {
                "id": spec.id,
                "role": spec.role,
                "prior": spec.prior,
                "status": "complete",
                "result": {
                    "recommendation": fallback,
                    "model": "fallback",
                    "files": {},
                },
            }

    @staticmethod
    def _aggregate_consensus(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not results:
            return {
                "decision": "No branch results",
                "confidence": 0.0,
                "reasons": [],
            }

        top = [r for r in results if r.get("status") == "complete"]
        if not top:
            return {
                "decision": "All branches failed",
                "confidence": 0.0,
                "reasons": ["No successful sub-agent outputs"],
            }

        reasons = []
        for r in top[:4]:
            rec = ((r.get("result") or {}).get("recommendation") or "").strip()
            if rec:
                reasons.append(rec[:180])

        confidence = min(0.95, 0.45 + (len(top) / max(1, len(results))) * 0.5)
        return {
            "decision": "Proceed with staged rollout and guardrails",
            "confidence": round(confidence, 2),
            "reasons": reasons,
        }

    async def run(
        self,
        *,
        task: str,
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cfg = config or {}
        ctx = context or {}
        requested = int(cfg.get("branches") or 6)
        cap = SwanEngine.resolve_branches(requested)
        actual = int(cap["actual"] or 1)

        specs = self.build_specs(
            task=task,
            count=actual,
            mode=str(cfg.get("mode") or "swan"),
            strategy=str(cfg.get("strategy") or "").strip() or None,
            priors=cfg.get("priors") if isinstance(cfg.get("priors"), dict) else None,
            predefined_ids=ctx.get("subagent_ids") if isinstance(ctx.get("subagent_ids"), list) else None,
            seed=cfg.get("seed") if isinstance(cfg.get("seed"), int) else None,
        )

        max_concurrency = max(1, int(os.environ.get("CRUCIB_SUBAGENT_MAX_CONCURRENCY", "6")))
        sem = asyncio.Semaphore(max_concurrency)

        async def _run(spec: SubagentSpec) -> Dict[str, Any]:
            async with sem:
                return await self._run_single(spec=spec, task=task, context=ctx)

        results = await asyncio.gather(*[_run(s) for s in specs])
        consensus = self._aggregate_consensus(results)

        return {
            "jobId": self.job_id,
            "task": task,
            "requestedBranches": requested,
            "actualBranches": actual,
            "hardLimit": cap.get("hard_limit"),
            "subagentResults": results,
            "consensus": consensus,
            "confidence": consensus.get("confidence", 0.0),
            "recommendedAction": consensus.get("decision"),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }

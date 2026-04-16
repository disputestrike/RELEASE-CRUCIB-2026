"""Scenario simulation engine for counterfactual spawn analysis."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Persona:
    role: str
    prior: str


class SimulationEngine:
    DEFAULT_ROLES = ["architect", "backend", "security", "ux", "devops"]
    DEFAULT_PRIORS = {
        "cost_sensitive": 0.33,
        "security_first": 0.34,
        "speed_first": 0.33,
    }

    @classmethod
    def _normalize_priors(cls, priors: Optional[Dict[str, float]]) -> Dict[str, float]:
        p = dict(cls.DEFAULT_PRIORS)
        if isinstance(priors, dict):
            for k in list(p.keys()):
                if k in priors:
                    try:
                        p[k] = max(0.0, float(priors[k]))
                    except Exception:
                        pass
        total = sum(p.values())
        if total <= 0:
            return dict(cls.DEFAULT_PRIORS)
        return {k: v / total for k, v in p.items()}

    @classmethod
    def generate_personas(
        cls,
        population_size: int,
        agent_roles: Optional[List[str]] = None,
        priors: Optional[Dict[str, float]] = None,
        seed: Optional[int] = None,
    ) -> List[Persona]:
        n = max(3, min(int(population_size), 256))
        roles = [r for r in (agent_roles or cls.DEFAULT_ROLES) if r] or list(cls.DEFAULT_ROLES)
        norm = cls._normalize_priors(priors)
        prior_names = list(norm.keys())
        prior_weights = [norm[k] for k in prior_names]
        rng = random.Random(seed)

        personas: List[Persona] = []
        for i in range(n):
            role = roles[i % len(roles)]
            prior = rng.choices(prior_names, weights=prior_weights, k=1)[0]
            personas.append(Persona(role=role, prior=prior))
        return personas

    @staticmethod
    def _position_from_prior(prior: str, scenario: str) -> str:
        s = (scenario or "").lower()
        if prior == "security_first":
            if "remove" in s or "switch" in s:
                return "Stabilize current stack first, change only with security regression checks"
            return "Prefer safer path with strict controls and verification"
        if prior == "cost_sensitive":
            if "stripe" in s and ("remove" in s or "switch" in s):
                return "Switch to lower-fee option if migration risk is bounded"
            return "Prefer lower operating cost and lean dependencies"
        if prior == "speed_first":
            return "Prefer fastest path to production with minimum migration drag"
        return "Prefer balanced tradeoff path"

    @classmethod
    def _cluster_round(cls, personas: List[Persona], scenario: str, rng: random.Random) -> List[Dict[str, Any]]:
        # Two dominant opinion poles + optional neutral cluster.
        a_size = 0
        b_size = 0
        neutral = 0
        for p in personas:
            roll = rng.random()
            if p.prior == "security_first":
                if roll < 0.65:
                    a_size += 1
                elif roll < 0.9:
                    b_size += 1
                else:
                    neutral += 1
            elif p.prior == "cost_sensitive":
                if roll < 0.62:
                    b_size += 1
                elif roll < 0.9:
                    a_size += 1
                else:
                    neutral += 1
            else:  # speed_first
                if roll < 0.58:
                    b_size += 1
                elif roll < 0.88:
                    a_size += 1
                else:
                    neutral += 1

        total = max(1, len(personas))
        clusters: List[Dict[str, Any]] = []
        if a_size > 0:
            clusters.append(
                {
                    "id": "cluster_a",
                    "size": a_size,
                    "position": "Keep current architecture; migration risk is currently too high",
                    "confidence": round(min(0.95, 0.45 + (a_size / total) * 0.6), 2),
                    "key_arguments": [
                        "existing integrations remain stable",
                        "lower operational disruption",
                        "easier compliance continuity",
                    ],
                }
            )
        if b_size > 0:
            clusters.append(
                {
                    "id": "cluster_b",
                    "size": b_size,
                    "position": "Adopt the proposed change with guarded rollout",
                    "confidence": round(min(0.95, 0.45 + (b_size / total) * 0.6), 2),
                    "key_arguments": [
                        "cost or DX upside",
                        "faster long-term iteration",
                        "manageable migration with staged fallback",
                    ],
                }
            )
        if neutral > 0:
            clusters.append(
                {
                    "id": "cluster_neutral",
                    "size": neutral,
                    "position": "Delay decision and gather additional runtime evidence",
                    "confidence": round(min(0.9, 0.35 + (neutral / total) * 0.5), 2),
                    "key_arguments": [
                        "insufficient benchmark data",
                        "need controlled canary evidence",
                    ],
                }
            )
        return clusters

    @staticmethod
    def _sentiment_shift(clusters: List[Dict[str, Any]], population: int) -> Dict[str, float]:
        total = max(1, population)
        a = next((c for c in clusters if c.get("id") == "cluster_a"), None)
        b = next((c for c in clusters if c.get("id") == "cluster_b"), None)
        a_ratio = float((a or {}).get("size") or 0) / total
        b_ratio = float((b or {}).get("size") or 0) / total
        return {
            "pro_current": round(a_ratio - 0.5, 2),
            "pro_change": round(b_ratio - 0.5, 2),
        }

    @classmethod
    def run_simulation(
        cls,
        *,
        scenario: str,
        population_size: int,
        rounds: int,
        agent_roles: Optional[List[str]] = None,
        priors: Optional[Dict[str, float]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        n_rounds = max(1, min(int(rounds), 8))
        personas = cls.generate_personas(
            population_size=population_size,
            agent_roles=agent_roles,
            priors=priors,
            seed=seed,
        )
        rng = random.Random(seed)

        updates: List[Dict[str, Any]] = []
        last_clusters: List[Dict[str, Any]] = []
        consensus = False
        for r in range(1, n_rounds + 1):
            clusters = cls._cluster_round(personas, scenario, rng)
            last_clusters = clusters
            strongest = max((c.get("size") or 0) for c in clusters) if clusters else 0
            consensus = strongest >= int(len(personas) * 0.7)
            updates.append(
                {
                    "round": r,
                    "clusters": clusters,
                    "sentiment_shift": cls._sentiment_shift(clusters, len(personas)),
                    "consensus_emerging": consensus,
                }
            )
            if consensus:
                break

        dominant = max(last_clusters, key=lambda c: c.get("size") or 0) if last_clusters else None
        recommendation = {
            "recommended_action": (dominant or {}).get("position") or "Collect more evidence before decision",
            "confidence": round((dominant or {}).get("confidence") or 0.5, 2),
            "tradeoffs": (dominant or {}).get("key_arguments") or [],
            "cluster_id": (dominant or {}).get("id"),
        }

        return {
            "scenario": scenario,
            "population_size": len(personas),
            "rounds_executed": len(updates),
            "updates": updates,
            "recommendation": recommendation,
            "consensus_reached": consensus,
        }

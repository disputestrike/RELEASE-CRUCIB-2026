from __future__ import annotations

from typing import Any, Dict, List, Optional

from .agent_factory import build_agents
from .classifier import classify_scenario
from .debate_llm import augment_debate_with_llm_maybe
from .debate_engine import run_debate
from .domain_policy import build_evidence_policy
from .evidence_engine import build_evidence
from .intent_router import route_intent
from .outcome_engine import build_outcomes, build_recommendation
from .output_answer_engine import build_output_answer
from .population_engine import build_population_model
from .pulse_events import build_simulation_pulse
from .report_builder import build_report
from .repository import new_id, now_iso, repository
from .trust_engine import build_trust_score
from .verdict_engine import build_final_verdict


DEPTH_CONFIG = {
    "fast": {"rounds": 3, "agent_count": 6, "population_size": 250, "evidence_depth": 2},
    "balanced": {"rounds": 5, "agent_count": 8, "population_size": 1000, "evidence_depth": 4},
    "deep": {"rounds": 6, "agent_count": 12, "population_size": 5000, "evidence_depth": 6},
    "maximum": {"rounds": 8, "agent_count": 16, "population_size": 10000, "evidence_depth": 8},
}


def _depth_config(depth: str, rounds: int, agent_count: int, population_size: Optional[int], evidence_depth: Optional[int]) -> Dict[str, Any]:
    key = (depth or "balanced").strip().lower()
    if key not in DEPTH_CONFIG:
        key = "balanced"
    cfg = dict(DEPTH_CONFIG[key])
    if population_size:
        cfg["population_size"] = max(100, min(10000, int(population_size)))
    if evidence_depth:
        cfg["evidence_depth"] = max(1, min(10, int(evidence_depth)))
    if key == "balanced":
        cfg["rounds"] = max(1, min(int(rounds or cfg["rounds"]), 8))
        cfg["agent_count"] = max(3, min(int(agent_count or cfg["agent_count"]), 24))
    cfg["depth"] = key
    return cfg


class RealityEngine:
    async def _event(self, *, simulation_id: str, run_id: str, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = {
            "id": new_id("evt"),
            "simulation_id": simulation_id,
            "run_id": run_id,
            "event_type": event_type,
            "payload": payload,
            "created_at": now_iso(),
        }
        await repository.insert("simulation_events", event)
        await repository.insert(
            "simulation_replay_events",
            {
                "id": new_id("replay"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "event_type": event_type,
                "event_payload": payload,
                "created_at": event["created_at"],
            },
        )
        return event

    async def create_simulation(
        self,
        *,
        user_id: str,
        prompt: str,
        assumptions: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        simulation_id = new_id("sim")
        now = now_iso()
        doc = {
            "id": simulation_id,
            "user_id": user_id,
            "org_id": (metadata or {}).get("org_id"),
            "status": "created",
            "title": prompt.strip()[:120],
            "prompt": prompt,
            "assumptions": assumptions or [],
            "attachments": attachments or [],
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }
        await repository.insert("simulations", doc)
        return doc

    async def run_simulation(
        self,
        *,
        simulation_id: str,
        user_id: str,
        prompt: str,
        assumptions: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        depth: str = "balanced",
        use_live_evidence: bool = True,
        population_size: Optional[int] = None,
        evidence_depth: Optional[int] = None,
        rounds: int = 5,
        agent_count: int = 8,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        config = _depth_config(depth, rounds, agent_count, population_size, evidence_depth)
        run_id = new_id("run")
        now = now_iso()
        run_doc = {
            "id": run_id,
            "simulation_id": simulation_id,
            "user_id": user_id,
            "status": "running",
            "depth": config["depth"],
            "rounds_requested": config["rounds"],
            "agent_count_requested": config["agent_count"],
            "population_size_requested": config["population_size"],
            "evidence_depth_requested": config["evidence_depth"],
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }
        await repository.insert("simulation_runs", run_doc)
        await self._event(simulation_id=simulation_id, run_id=run_id, event_type="simulation.created", payload={"status": "running"})

        classification = classify_scenario(prompt)
        routed_intent = route_intent(classification, prompt)
        input_doc = {
            "id": new_id("input"),
            "simulation_id": simulation_id,
            "run_id": run_id,
            "original_prompt": prompt,
            "normalized_prompt": prompt.strip(),
            "classification": classification.model_dump(),
            "user_assumptions": assumptions or [],
            "attachments": attachments or [],
            "created_at": now_iso(),
        }
        await repository.insert("simulation_inputs", input_doc)
        await self._event(
            simulation_id=simulation_id,
            run_id=run_id,
            event_type="simulation.classified",
            payload=classification.model_dump(),
        )

        evidence_policy = build_evidence_policy(classification, prompt)
        await self._event(
            simulation_id=simulation_id,
            run_id=run_id,
            event_type="simulation.evidence_policy_created",
            payload=evidence_policy,
        )
        evidence = await build_evidence(
            simulation_id=simulation_id,
            run_id=run_id,
            prompt=prompt,
            classification=classification,
            assumptions=assumptions or [],
            attachments=attachments or [],
            use_live_evidence=use_live_evidence,
            evidence_depth=config["evidence_depth"],
            evidence_policy=evidence_policy,
        )
        for source in evidence["sources"]:
            await repository.insert("simulation_sources", source)
        for fact in evidence["evidence"]:
            await repository.insert("simulation_evidence", fact)
        for claim in evidence.get("claims") or []:
            await repository.insert("simulation_claims", claim)
        for assumption in evidence["assumptions"]:
            await repository.insert("simulation_assumptions", assumption)
        await self._event(
            simulation_id=simulation_id,
            run_id=run_id,
            event_type="simulation.evidence_collected",
            payload={
                "source_count": len(evidence["sources"]),
                "fact_count": len(evidence["evidence"]),
                "missing_evidence": evidence["missing_evidence"],
                "live_data_used": (evidence.get("quality") or {}).get("live_data_used"),
                "policy_coverage": (evidence.get("quality") or {}).get("policy_coverage"),
            },
        )

        agents = build_agents(
            simulation_id=simulation_id,
            run_id=run_id,
            classification=classification,
            agent_count=config["agent_count"],
            evidence_summary=evidence,
            routed_intent=routed_intent,
            prompt=prompt,
        )
        for agent in agents:
            await repository.insert("simulation_agents", agent)
        await self._event(
            simulation_id=simulation_id,
            run_id=run_id,
            event_type="simulation.agents_created",
            payload={"agent_count": len(agents), "agents": [{"id": a["id"], "role": a["role"]} for a in agents]},
        )

        debate = run_debate(
            simulation_id=simulation_id,
            run_id=run_id,
            classification=classification,
            agents=agents,
            evidence_summary=evidence,
            rounds=config["rounds"],
        )
        debate = await augment_debate_with_llm_maybe(
            debate,
            classification=classification,
            evidence_summary=evidence,
        )
        for row in debate["rounds"]:
            await repository.insert("simulation_rounds", row)
            await self._event(simulation_id=simulation_id, run_id=run_id, event_type="simulation.round_completed", payload=row)
        for row in debate["messages"]:
            await repository.insert("simulation_agent_messages", row)
        for row in debate["belief_updates"]:
            await repository.insert("simulation_belief_updates", row)
        for row in debate["clusters"]:
            await repository.insert("simulation_clusters", row)

        population_model = build_population_model(
            simulation_id=simulation_id,
            run_id=run_id,
            prompt=prompt,
            classification=classification,
            debate=debate,
            evidence_summary=evidence,
            depth=config["depth"],
            requested_population_size=config["population_size"],
        )
        await repository.insert(
            "simulation_population_models",
            {
                "id": new_id("pop_model"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                **population_model,
                "created_at": now_iso(),
            },
        )
        for row in population_model.get("clusters") or []:
            await repository.insert("simulation_clusters", row)
        await self._event(
            simulation_id=simulation_id,
            run_id=run_id,
            event_type="simulation.population_modeled",
            payload={
                "population_size": population_model.get("population_size"),
                "cluster_count": len(population_model.get("clusters") or []),
                "method": population_model.get("method"),
            },
        )

        pulse_feed = build_simulation_pulse(
            classification=classification,
            debate=debate,
            population_model=population_model,
            evidence_summary=evidence,
        )
        for pulse_item in pulse_feed:
            await self._event(
                simulation_id=simulation_id,
                run_id=run_id,
                event_type="simulation.pulse",
                payload=pulse_item,
            )

        outcomes = build_outcomes(
            simulation_id=simulation_id,
            run_id=run_id,
            prompt=prompt,
            classification=classification,
            debate=debate,
            evidence_summary=evidence,
        )
        recommendation = build_recommendation(classification, outcomes)
        for outcome in outcomes:
            await repository.insert("simulation_outcomes", outcome)
        await self._event(simulation_id=simulation_id, run_id=run_id, event_type="simulation.outcomes_generated", payload={"count": len(outcomes)})

        trust = build_trust_score(
            simulation_id=simulation_id,
            run_id=run_id,
            classification=classification,
            evidence_summary=evidence,
            debate=debate,
        )
        await repository.insert("simulation_trust_scores", trust)
        await repository.insert(
            "simulation_trust_snapshots",
            {
                "id": new_id("trust_snapshot"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "phase": "final",
                "trust_score": trust.get("trust_score"),
                "score": trust.get("score"),
                "components": trust.get("components") or {},
                "formula": trust.get("formula"),
                "warnings": trust.get("warnings") or [],
                "created_at": now_iso(),
            },
        )
        final_verdict = build_final_verdict(
            classification=classification,
            evidence_summary=evidence,
            outcomes=outcomes,
            trust=trust,
        )
        output_answer = build_output_answer(
            prompt=prompt,
            classification=classification,
            routed_intent=routed_intent,
            evidence_summary=evidence,
            final_verdict=final_verdict,
            trust=trust,
        )
        await self._event(
            simulation_id=simulation_id,
            run_id=run_id,
            event_type="simulation.final_verdict_generated",
            payload=final_verdict,
        )
        report = build_report(
            prompt=prompt,
            classification=classification,
            evidence_summary=evidence,
            agents=debate["agents"],
            debate=debate,
            outcomes=outcomes,
            recommendation=recommendation,
            trust=trust,
            simulation_id=simulation_id,
            run_id=run_id,
            population_model=population_model,
            final_verdict=final_verdict,
            output_answer=output_answer,
            routed_intent=routed_intent,
        )

        completed = {
            **run_doc,
            "status": "completed",
            "classification": classification.model_dump(),
            "recommendation": recommendation,
            "trust_score": trust,
            "final_verdict": final_verdict,
            "report": report,
            "simulation_pulse": pulse_feed,
            "debate_engine_mode": debate.get("debate_engine_mode"),
            "debate_augment": {
                "reason": debate.get("debate_augment_reason"),
                "caps": debate.get("debate_augment_caps"),
            },
            "output_answer": output_answer,
            "routed_intent": routed_intent,
            "retrieval_ledger": evidence.get("retrieval_ledger"),
            "completed_at": now_iso(),
            "updated_at": now_iso(),
        }
        await repository.upsert("simulation_runs", completed)
        await repository.upsert(
            "simulations",
            {
                "id": simulation_id,
                "user_id": user_id,
                "status": "completed",
                "title": prompt.strip()[:120],
                "prompt": prompt,
                "last_run_id": run_id,
                "updated_at": now_iso(),
            },
        )
        await self._event(
            simulation_id=simulation_id,
            run_id=run_id,
            event_type="simulation.completed",
            payload={
                "recommendation": recommendation,
                "trust_score": trust.get("trust_score"),
                "final_verdict": final_verdict.get("verdict"),
            },
        )

        return {
            "simulation": {"id": simulation_id, "status": "completed", "title": prompt.strip()[:120]},
            "run": completed,
            "input": input_doc,
            "classification": classification.model_dump(),
            "sources": evidence["sources"],
            "evidence": evidence["evidence"],
            "claims": evidence.get("claims") or [],
            "missing_evidence": evidence["missing_evidence"],
            "unsupported_claims": evidence["unsupported_claims"],
            "assumptions": evidence["assumptions"],
            "agents": debate["agents"],
            "rounds": debate["rounds"],
            "agent_messages": debate["messages"],
            "belief_updates": debate["belief_updates"],
            "clusters": debate["clusters"],
            "population_model": population_model,
            "outcomes": outcomes,
            "recommendation": recommendation,
            "final_verdict": final_verdict,
            "trust_score": trust,
            "report": report,
            "simulation_pulse": pulse_feed,
            "debate_engine_mode": debate.get("debate_engine_mode"),
            "debate_augment": {
                "reason": debate.get("debate_augment_reason"),
                "caps": debate.get("debate_augment_caps"),
            },
            "output_answer": output_answer,
            "routed_intent": routed_intent,
            "retrieval_ledger": evidence.get("retrieval_ledger"),
            "engine": "Reality Engine V1",
        }

    async def get_run_details(self, simulation_id: str, run_id: str) -> Dict[str, Any]:
        run = await repository.find_one("simulation_runs", {"id": run_id}) or {}
        return {
            "simulation": await repository.find_one("simulations", {"id": simulation_id}),
            "run": run,
            "inputs": await repository.list("simulation_inputs", {"run_id": run_id}, limit=20),
            "sources": await repository.list("simulation_sources", {"run_id": run_id}, limit=100),
            "evidence": await repository.list("simulation_evidence", {"run_id": run_id}, limit=200),
            "claims": await repository.list("simulation_claims", {"run_id": run_id}, limit=300),
            "agents": await repository.list("simulation_agents", {"run_id": run_id}, limit=100),
            "rounds": await repository.list("simulation_rounds", {"run_id": run_id}, limit=100),
            "agent_messages": await repository.list("simulation_agent_messages", {"run_id": run_id}, limit=500),
            "belief_updates": await repository.list("simulation_belief_updates", {"run_id": run_id}, limit=500),
            "clusters": await repository.list("simulation_clusters", {"run_id": run_id}, limit=100),
            "outcomes": await repository.list("simulation_outcomes", {"run_id": run_id}, limit=50),
            "trust_scores": await repository.list("simulation_trust_scores", {"run_id": run_id}, limit=10),
            "trust_snapshots": await repository.list("simulation_trust_snapshots", {"run_id": run_id}, limit=20),
            "assumptions": await repository.list("simulation_assumptions", {"run_id": run_id}, limit=100),
            "events": await repository.list("simulation_events", {"run_id": run_id}, limit=500),
            "replay_events": await repository.list("simulation_replay_events", {"run_id": run_id}, limit=500),
            "population_models": await repository.list("simulation_population_models", {"run_id": run_id}, limit=20),
        }


reality_engine = RealityEngine()

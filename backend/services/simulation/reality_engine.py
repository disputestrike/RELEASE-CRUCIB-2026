from __future__ import annotations

from typing import Any, Dict, List, Optional

from .agent_factory import build_agents
from .classifier import classify_scenario
from .debate_engine import run_debate
from .evidence_engine import build_evidence
from .outcome_engine import build_outcomes, build_recommendation
from .report_builder import build_report
from .repository import new_id, now_iso, repository
from .trust_engine import build_trust_score


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
        rounds: int = 5,
        agent_count: int = 8,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        run_id = new_id("run")
        now = now_iso()
        run_doc = {
            "id": run_id,
            "simulation_id": simulation_id,
            "user_id": user_id,
            "status": "running",
            "rounds_requested": rounds,
            "agent_count_requested": agent_count,
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }
        await repository.insert("simulation_runs", run_doc)
        await self._event(simulation_id=simulation_id, run_id=run_id, event_type="simulation.created", payload={"status": "running"})

        classification = classify_scenario(prompt)
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

        evidence = build_evidence(
            simulation_id=simulation_id,
            run_id=run_id,
            prompt=prompt,
            classification=classification,
            assumptions=assumptions or [],
            attachments=attachments or [],
        )
        for source in evidence["sources"]:
            await repository.insert("simulation_sources", source)
        for fact in evidence["evidence"]:
            await repository.insert("simulation_evidence", fact)
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
                "live_data_used": False,
            },
        )

        agents = build_agents(
            simulation_id=simulation_id,
            run_id=run_id,
            classification=classification,
            agent_count=agent_count,
            evidence_summary=evidence,
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
            rounds=rounds,
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
        )

        completed = {
            **run_doc,
            "status": "completed",
            "classification": classification.model_dump(),
            "recommendation": recommendation,
            "trust_score": trust,
            "report": report,
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
            payload={"recommendation": recommendation, "trust_score": trust.get("trust_score")},
        )

        return {
            "simulation": {"id": simulation_id, "status": "completed", "title": prompt.strip()[:120]},
            "run": completed,
            "input": input_doc,
            "classification": classification.model_dump(),
            "sources": evidence["sources"],
            "evidence": evidence["evidence"],
            "missing_evidence": evidence["missing_evidence"],
            "unsupported_claims": evidence["unsupported_claims"],
            "assumptions": evidence["assumptions"],
            "agents": debate["agents"],
            "rounds": debate["rounds"],
            "agent_messages": debate["messages"],
            "belief_updates": debate["belief_updates"],
            "clusters": debate["clusters"],
            "outcomes": outcomes,
            "recommendation": recommendation,
            "trust_score": trust,
            "report": report,
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
            "agents": await repository.list("simulation_agents", {"run_id": run_id}, limit=100),
            "rounds": await repository.list("simulation_rounds", {"run_id": run_id}, limit=100),
            "agent_messages": await repository.list("simulation_agent_messages", {"run_id": run_id}, limit=500),
            "belief_updates": await repository.list("simulation_belief_updates", {"run_id": run_id}, limit=500),
            "clusters": await repository.list("simulation_clusters", {"run_id": run_id}, limit=100),
            "outcomes": await repository.list("simulation_outcomes", {"run_id": run_id}, limit=50),
            "trust_scores": await repository.list("simulation_trust_scores", {"run_id": run_id}, limit=10),
            "assumptions": await repository.list("simulation_assumptions", {"run_id": run_id}, limit=100),
            "events": await repository.list("simulation_events", {"run_id": run_id}, limit=500),
        }


reality_engine = RealityEngine()

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

from services.runtime.simulation_engine import SimulationEngine


class SimulationOrchestrator:
    def __init__(self, *, job_id: str, user_id: str):
        self.job_id = str(job_id)
        self.user_id = str(user_id)
        self.simulation_id = f"sim_{uuid.uuid4().hex[:12]}"

    async def _persist_log(self, kind: str, payload: Dict[str, Any]) -> None:
        try:
            from db_pg import get_db

            db = await get_db()
            await db.project_logs.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "project_id": self.job_id,
                    "job_id": self.job_id,
                    "user_id": self.user_id,
                    "kind": kind,
                    "payload": payload,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            # Persistence failures should not block simulation execution.
            return None

    async def run(
        self,
        *,
        scenario: str,
        mode: str = "decision",
        population_size: int,
        rounds: int,
        agent_roles: Optional[List[str]] = None,
        priors: Optional[Dict[str, float]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        # 1. Scenario Validation (LIFTED: All scenarios allowed)


        personas = SimulationEngine.generate_personas(
            population_size=population_size,
            agent_roles=agent_roles,
            priors=priors,
            seed=seed,
        )
        persona_rows = [
            {
                "id": f"p{i+1}",
                "role": p.role,
                "prior": p.prior,
            }
            for i, p in enumerate(personas)
        ]

        await self._persist_log(
            "simulation.started",
            {
                "simulation_id": self.simulation_id,
                "scenario": scenario,
                "mode": mode,
                "population_size": len(persona_rows),
                "rounds": rounds,
            },
        )

        result = SimulationEngine.run_simulation(
            scenario=scenario,
            mode=mode,
            population_size=population_size,
            rounds=rounds,
            agent_roles=agent_roles,
            priors=priors,
            seed=seed,
        )

        updates = result.get("updates") or []
        for u in updates:
            await self._persist_log(
                "simulation.update",
                {
                    "simulation_id": self.simulation_id,
                    "round": u.get("round"),
                    "clusters": u.get("clusters"),
                    "sentiment_shift": u.get("sentiment_shift"),
                    "consensus_emerging": u.get("consensus_emerging"),
                },
            )

        recommendation = result.get("recommendation") or {}
        await self._persist_log(
            "simulation.completed",
            {
                "simulation_id": self.simulation_id,
                "recommendation": recommendation,
                "consensus_reached": result.get("consensus_reached"),
                "rounds_executed": result.get("rounds_executed"),
            },
        )

        return {
            "simulationId": self.simulation_id,
            **result,
            "personas": persona_rows,
            "metadata": {
                "jobId": self.job_id,
                "userId": self.user_id,
                "generatedAt": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def stream_ndjson(
        self,
        *,
        scenario: str,
        mode: str = "decision",
        population_size: int,
        rounds: int,
        agent_roles: Optional[List[str]] = None,
        priors: Optional[Dict[str, float]] = None,
        seed: Optional[int] = None,
    ) -> AsyncIterator[str]:
        out = await self.run(
            scenario=scenario,
            mode=mode,
            population_size=population_size,
            rounds=rounds,
            agent_roles=agent_roles,
            priors=priors,
            seed=seed,
        )

        for update in out.get("updates") or []:
            payload = {
                "type": "simulation.update",
                "jobId": self.job_id,
                "simulationId": self.simulation_id,
                **update,
            }
            yield json.dumps(payload) + "\n"

        yield (
            json.dumps(
                {
                    "type": "simulation.completed",
                    "jobId": self.job_id,
                    "simulationId": self.simulation_id,
                    "recommendation": out.get("recommendation"),
                    "consensus_reached": out.get("consensus_reached"),
                    "rounds_executed": out.get("rounds_executed"),
                    "scenario": out.get("scenario"),
                    "personas": out.get("personas") or [],
                }
            )
            + "\n"
        )

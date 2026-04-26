from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


SIMULATION_COLLECTIONS = [
    "simulations",
    "simulation_runs",
    "simulation_inputs",
    "simulation_sources",
    "simulation_evidence",
    "simulation_claims",
    "simulation_agents",
    "simulation_rounds",
    "simulation_agent_messages",
    "simulation_belief_updates",
    "simulation_clusters",
    "simulation_outcomes",
    "simulation_trust_scores",
    "simulation_trust_snapshots",
    "simulation_population_models",
    "simulation_assumptions",
    "simulation_events",
    "simulation_replay_events",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _get_db_instance():
    try:
        from ...deps import get_db

        return get_db()
    except Exception:
        return None


class SimulationRepository:
    async def insert(self, collection_name: str, doc: Dict[str, Any]) -> bool:
        db = _get_db_instance()
        if db is None:
            return False
        payload = dict(doc)
        payload.setdefault("id", new_id(collection_name.rstrip("s")))
        payload.setdefault("created_at", now_iso())
        payload.setdefault("updated_at", payload["created_at"])
        try:
            await getattr(db, collection_name).insert_one(payload)
            return True
        except Exception:
            return False

    async def upsert(self, collection_name: str, doc: Dict[str, Any]) -> bool:
        db = _get_db_instance()
        if db is None:
            return False
        payload = dict(doc)
        payload.setdefault("id", new_id(collection_name.rstrip("s")))
        payload.setdefault("created_at", now_iso())
        payload["updated_at"] = now_iso()
        try:
            await getattr(db, collection_name).update_one(
                {"id": payload["id"]},
                {"$set": payload},
                upsert=True,
            )
            return True
        except Exception:
            return False

    async def find_one(self, collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        db = _get_db_instance()
        if db is None:
            return None
        try:
            return await getattr(db, collection_name).find_one(query)
        except Exception:
            return None

    async def list(self, collection_name: str, query: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        db = _get_db_instance()
        if db is None:
            return []
        try:
            cursor = getattr(db, collection_name).find(query).sort("created_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception:
            return []


repository = SimulationRepository()

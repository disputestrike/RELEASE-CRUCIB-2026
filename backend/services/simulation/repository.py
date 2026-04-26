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

_MEMORY_STORE: Dict[str, List[Dict[str, Any]]] = {
    name: [] for name in SIMULATION_COLLECTIONS
}


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


def _matches(doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
    return all(doc.get(key) == value for key, value in (query or {}).items())


def _memory_insert(collection_name: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(doc)
    payload.setdefault("id", new_id(collection_name.rstrip("s")))
    payload.setdefault("created_at", now_iso())
    payload.setdefault("updated_at", payload["created_at"])
    _MEMORY_STORE.setdefault(collection_name, []).append(payload)
    return payload


def _memory_upsert(collection_name: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(doc)
    payload.setdefault("id", new_id(collection_name.rstrip("s")))
    payload.setdefault("created_at", now_iso())
    payload["updated_at"] = now_iso()
    rows = _MEMORY_STORE.setdefault(collection_name, [])
    for index, row in enumerate(rows):
        if row.get("id") == payload["id"]:
            rows[index] = {**row, **payload}
            return rows[index]
    rows.append(payload)
    return payload


class SimulationRepository:
    async def insert(self, collection_name: str, doc: Dict[str, Any]) -> bool:
        payload = _memory_insert(collection_name, doc)
        db = _get_db_instance()
        if db is None:
            return True
        try:
            await getattr(db, collection_name).insert_one(payload)
            return True
        except Exception:
            return True

    async def upsert(self, collection_name: str, doc: Dict[str, Any]) -> bool:
        payload = _memory_upsert(collection_name, doc)
        db = _get_db_instance()
        if db is None:
            return True
        try:
            await getattr(db, collection_name).update_one(
                {"id": payload["id"]},
                {"$set": payload},
                upsert=True,
            )
            return True
        except Exception:
            return True

    async def find_one(self, collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        db = _get_db_instance()
        if db is not None:
            try:
                result = await getattr(db, collection_name).find_one(query)
                if result:
                    return result
            except Exception:
                pass
        for row in reversed(_MEMORY_STORE.get(collection_name, [])):
            if _matches(row, query):
                return dict(row)
        return None

    async def list(self, collection_name: str, query: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        db = _get_db_instance()
        if db is not None:
            try:
                cursor = getattr(db, collection_name).find(query).sort("created_at", -1).limit(limit)
                rows = await cursor.to_list(length=limit)
                if rows:
                    return rows
            except Exception:
                pass
        rows = [dict(row) for row in _MEMORY_STORE.get(collection_name, []) if _matches(row, query)]
        rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return rows[:limit]


repository = SimulationRepository()

"""Persistent file-backed memory graph for runtime execution context.

Each node represents a recorded observation (step output, agent result, etc.).
Edges encode directional relations between nodes (caused_by, related_to, etc.).
Graph is stored as a JSON file per project under WORKSPACE_ROOT.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from backend.project_state import WORKSPACE_ROOT

_LOCKS: dict[str, Lock] = {}
_LOCKS_LOCK = Lock()

_MAX_NODES = int(os.environ.get("CRUCIB_MEMORY_GRAPH_MAX_NODES", "2000"))


def _lock_for(project_id: str) -> Lock:
    with _LOCKS_LOCK:
        if project_id not in _LOCKS:
            _LOCKS[project_id] = Lock()
        return _LOCKS[project_id]


def _graph_path(project_id: str) -> Path:
    safe = (project_id or "default").replace("/", "_").replace("\\", "_")
    root = WORKSPACE_ROOT / safe / "memory"
    root.mkdir(parents=True, exist_ok=True)
    return root / "memory_graph.json"


def _load(project_id: str) -> Dict[str, Any]:
    p = _graph_path(project_id)
    if not p.exists():
        return {"nodes": {}, "edges": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"nodes": {}, "edges": []}


def _save(project_id: str, graph: Dict[str, Any]) -> None:
    _graph_path(project_id).write_text(json.dumps(graph, indent=2), encoding="utf-8")


def _prune(graph: Dict[str, Any]) -> None:
    """Remove oldest nodes if over the cap, keeping edges consistent."""
    nodes = graph.get("nodes") or {}
    if len(nodes) <= _MAX_NODES:
        return
    # Sort by ts ascending, drop oldest
    sorted_ids = sorted(nodes, key=lambda nid: float(nodes[nid].get("ts") or 0))
    to_remove = set(sorted_ids[: len(nodes) - _MAX_NODES])
    for nid in to_remove:
        nodes.pop(nid, None)
    graph["nodes"] = nodes
    # Prune edges referencing removed nodes
    graph["edges"] = [
        e for e in (graph.get("edges") or [])
        if e.get("from") not in to_remove and e.get("to") not in to_remove
    ]


def add_node(
    project_id: str,
    *,
    node_id: Optional[str] = None,
    task_id: str,
    node_type: str,
    payload: Dict[str, Any],
    tags: Optional[List[str]] = None,
) -> str:
    """Add a node to the memory graph. Returns the node ID."""
    nid = node_id or f"n_{uuid.uuid4().hex[:10]}"
    with _lock_for(project_id):
        graph = _load(project_id)
        graph["nodes"][nid] = {
            "id": nid,
            "task_id": task_id,
            "type": node_type,
            "payload": payload,
            "tags": tags or [],
            "ts": time.time(),
        }
        _prune(graph)
        _save(project_id, graph)
    return nid


def add_edge(
    project_id: str,
    *,
    from_id: str,
    to_id: str,
    relation: str = "caused_by",
) -> None:
    """Add a directed edge between two nodes."""
    with _lock_for(project_id):
        graph = _load(project_id)
        graph["edges"].append(
            {"from": from_id, "to": to_id, "relation": relation, "ts": time.time()}
        )
        _save(project_id, graph)


def query_nodes(
    project_id: str,
    *,
    task_id: Optional[str] = None,
    node_type: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Query nodes with optional filters. Returns most-recent first."""
    with _lock_for(project_id):
        graph = _load(project_id)
    nodes = list((graph.get("nodes") or {}).values())
    if task_id:
        nodes = [n for n in nodes if n.get("task_id") == task_id]
    if node_type:
        nodes = [n for n in nodes if n.get("type") == node_type]
    if tag:
        nodes = [n for n in nodes if tag in (n.get("tags") or [])]
    nodes.sort(key=lambda n: float(n.get("ts") or 0), reverse=True)
    return nodes[: max(1, int(limit))]


def get_graph(project_id: str) -> Dict[str, Any]:
    """Return the full graph (nodes + edges) for a project."""
    with _lock_for(project_id):
        return _load(project_id)

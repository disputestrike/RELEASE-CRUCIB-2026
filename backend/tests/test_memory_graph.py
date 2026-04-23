from __future__ import annotations

import uuid

import pytest

from services.runtime.memory_graph import add_node, add_edge, query_nodes, get_graph


def _pid() -> str:
    return f"proj-mg-{uuid.uuid4().hex[:8]}"


def test_add_and_query_node():
    project_id = _pid()
    nid = add_node(project_id, task_id="t1", node_type="step_result", payload={"val": 1})
    assert nid.startswith("n_")
    nodes = query_nodes(project_id, task_id="t1")
    assert len(nodes) == 1
    assert nodes[0]["payload"]["val"] == 1


def test_query_filters_by_type():
    project_id = _pid()
    add_node(project_id, task_id="t1", node_type="step_result", payload={"a": 1})
    add_node(project_id, task_id="t1", node_type="agent_output", payload={"b": 2})
    step_nodes = query_nodes(project_id, node_type="step_result")
    assert all(n["type"] == "step_result" for n in step_nodes)
    assert len(step_nodes) == 1


def test_query_filters_by_tag():
    project_id = _pid()
    add_node(project_id, task_id="t1", node_type="step_result", payload={}, tags=["important"])
    add_node(project_id, task_id="t1", node_type="step_result", payload={}, tags=["normal"])
    important = query_nodes(project_id, tag="important")
    assert len(important) == 1


def test_add_edge():
    project_id = _pid()
    a = add_node(project_id, task_id="t1", node_type="step_result", payload={"step": 1})
    b = add_node(project_id, task_id="t1", node_type="step_result", payload={"step": 2})
    add_edge(project_id, from_id=a, to_id=b, relation="caused_by")
    graph = get_graph(project_id)
    edges = graph["edges"]
    assert any(e["from"] == a and e["to"] == b and e["relation"] == "caused_by" for e in edges)


def test_explicit_node_id():
    project_id = _pid()
    nid = add_node(project_id, node_id="custom-id", task_id="t1", node_type="x", payload={})
    assert nid == "custom-id"
    assert "custom-id" in get_graph(project_id)["nodes"]


def test_retention_prunes_oldest(monkeypatch):
    import services.runtime.memory_graph as mg
    monkeypatch.setattr(mg, "_MAX_NODES", 3)
    project_id = _pid()
    ids = []
    for i in range(5):
        nid = add_node(project_id, task_id="t1", node_type="x", payload={"i": i})
        ids.append(nid)
    graph = get_graph(project_id)
    assert len(graph["nodes"]) == 3
    # Oldest two should be gone
    for nid in ids[:2]:
        assert nid not in graph["nodes"]
    # Newest three should remain
    for nid in ids[2:]:
        assert nid in graph["nodes"]

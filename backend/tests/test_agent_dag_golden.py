"""Agent DAG acyclicity (Fifty-point #19)."""

import pytest
from agent_dag import AGENT_DAG, get_execution_phases, topological_sort


@pytest.mark.golden
def test_agent_dag_topological_sort_acyclic():
    order = topological_sort(AGENT_DAG)
    assert len(order) == len(AGENT_DAG)
    assert set(order) == set(AGENT_DAG.keys())


@pytest.mark.golden
def test_agent_dag_execution_phases_cover_all_nodes():
    phases = get_execution_phases(AGENT_DAG)
    flat = [n for ph in phases for n in ph]
    assert len(flat) == len(AGENT_DAG)
    assert len(flat) == len(set(flat))

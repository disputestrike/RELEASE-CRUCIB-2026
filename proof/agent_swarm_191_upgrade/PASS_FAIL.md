# Agent Swarm 191 Upgrade

- `agent_dag_count`: PASS (`190` agents now in `/backend/agent_dag.py`)
- `selection_logic_added`: PASS (`/backend/orchestration/agent_selection_logic.py`)
- `planner_uses_selection_logic`: PASS
- `swarm_phases_use_selected_agents`: PASS
- `legacy_server_registry_synced_to_dag`: PASS
- `focused_orchestration_tests`: PASS (`14 passed`)

## Commands

```powershell
python -m py_compile backend\agent_dag.py backend\orchestration\agent_selection_logic.py backend\orchestration\planner.py backend\orchestration\swarm_agent_runner.py backend\server.py backend\tests\test_agent_selection_logic.py backend\tests\test_agent_swarm_autorunner.py
$env:PYTHONPATH='backend'; python -m pytest backend\tests\test_agent_selection_logic.py backend\tests\test_agent_swarm_autorunner.py backend\tests\test_generation_contract.py -q --noconftest
```

## Notes

- The zip claimed `191` agents, but the supplied `agent_dag.py` contains `190`.
- This patch imports that real DAG into CrucibAI, adds intelligent selection, and keeps the legacy server registry aligned with the DAG.

# Archived Code — Do Not Import

These files were part of the original 245-agent DAG execution system
superseded by `pipeline_orchestrator.py` on 2026-05-01.

They are kept here for reference only. Nothing in the active codebase imports them.
To restore any file, move it back to `backend/orchestration/`.

Active execution path:
  auto_runner.py → pipeline_orchestrator.py → runtime_engine.py

Legacy DAG path (CRUCIBAI_USE_PIPELINE=0 only):
  auto_runner.py → dag_engine.py → executor.py → agent_dag.py

Archived files were last active: pre-v1.0-pipeline-freeze

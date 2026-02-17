"""
Phase F verification: every DAG agent has a real behavior (state write, artifact write, or tool run).
Run from backend: python verify_120_agents.py
"""
import sys
from pathlib import Path

# Run from backend
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_dag import AGENT_DAG
from agent_real_behavior import (
    STATE_WRITERS,
    ARTIFACT_PATHS,
    TOOL_RUNNER_STATE_KEYS,
    REAL_TOOL_AGENTS,
)

SPECIAL = frozenset({"Image Generation", "Video Generation", "Scraping Agent"})

def main():
    dag_agents = set(AGENT_DAG.keys())
    covered = set(STATE_WRITERS) | set(ARTIFACT_PATHS) | set(TOOL_RUNNER_STATE_KEYS) | REAL_TOOL_AGENTS | SPECIAL
    missing = dag_agents - covered
    if missing:
        print("Agents without real behavior mapping:", sorted(missing))
        return 1
    print(f"All {len(dag_agents)} DAG agents have a real behavior (state / artifact / tool).")
    return 0

if __name__ == "__main__":
    sys.exit(main())

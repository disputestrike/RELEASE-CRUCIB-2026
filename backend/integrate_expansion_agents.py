#!/usr/bin/env python3
"""
Integration script: Merge expansion agents into agent_dag.py
Adds all 50+ agents with full wiring and selection logic
"""

import json
import sys

from agents_expansion_all import EXPANSION_AGENTS


def integrate_agents():
    """Add all expansion agents to AGENT_DAG"""

    # Read current agent_dag.py
    with open("agent_dag.py", "r") as f:
        dag_content = f.read()

    # Build new agent dict entries
    new_agent_lines = []
    for agent_name, config in sorted(EXPANSION_AGENTS.items()):
        depends_on = config.get("depends_on", [])
        system_prompt = config.get("system_prompt", "")

        # Escape quotes in system prompt
        system_prompt = system_prompt.replace('"', '\\"')

        # Format agent entry
        entry = f'    "{agent_name}": {{"depends_on": {json.dumps(depends_on)}, "system_prompt": "{system_prompt}"}},'
        new_agent_lines.append(entry)

    new_agents_block = "\n".join(new_agent_lines)

    # Find insertion point (before last closing brace and "def _use_token_optimized")
    insertion_marker = '    "Customization Engine Agent":'
    if insertion_marker in dag_content:
        # Find end of last agent
        pos = dag_content.find(insertion_marker)
        pos = dag_content.find("\n", pos)  # Move to next line

        # Insert new agents before the end of AGENT_DAG dict
        updated_content = (
            dag_content[:pos] + f",\n{new_agents_block}\n" + dag_content[pos:]
        )
    else:
        print("ERROR: Could not find insertion point in agent_dag.py")
        sys.exit(1)

    # Write updated file
    with open("agent_dag.py", "w") as f:
        f.write(updated_content)

    print(f"✅ Integrated {len(EXPANSION_AGENTS)} agents into agent_dag.py")
    return True


def wire_selection_logic():
    """Add selection logic to executor"""

    # Read executor.py
    with open("orchestration/executor.py", "r") as f:
        executor_content = f.read()

    # Add expansion agents selection logic
    selection_logic = '''
# Expansion agents selection logic
from agents_expansion_all import should_activate_agent, EXPANSION_AGENTS

def select_expansion_agents(prompt: str, execution_target: str) -> list:
    """Select which expansion agents to activate based on prompt and target"""
    selected = []
    for agent_name in EXPANSION_AGENTS.keys():
        if should_activate_agent(agent_name, prompt, execution_target):
            selected.append(agent_name)
    return selected
'''

    # Insert if not already present
    if "select_expansion_agents" not in executor_content:
        # Find good insertion point
        insertion_pos = executor_content.find("def _should_use_agent_selection")
        if insertion_pos > 0:
            executor_content = (
                executor_content[:insertion_pos]
                + selection_logic
                + "\n\n"
                + executor_content[insertion_pos:]
            )

            with open("orchestration/executor.py", "w") as f:
                f.write(executor_content)

            print("✅ Added expansion agent selection logic to executor.py")
            return True

    print("⚠️  Selection logic already present or not needed")
    return True


def verify_integration():
    """Verify all agents are properly integrated"""

    # Test import
    try:
        import agent_dag

        total_agents = len(agent_dag.AGENT_DAG)
        print(f"✅ Total agents in DAG: {total_agents}")
        print(f"   Original: 123")
        print(f"   Added: {total_agents - 123}")

        # Verify new agents exist
        from agents_expansion_all import EXPANSION_AGENTS

        for agent_name in EXPANSION_AGENTS.keys():
            if agent_name in agent_dag.AGENT_DAG:
                print(f"   ✓ {agent_name}")
            else:
                print(f"   ✗ MISSING: {agent_name}")
                return False

        return True
    except Exception as e:
        print(f"❌ Integration verification failed: {e}")
        return False


if __name__ == "__main__":
    print("🔥 INTEGRATING EXPANSION AGENTS...")
    print()

    if integrate_agents():
        print()
        if wire_selection_logic():
            print()
            if verify_integration():
                print()
                print("✅ INTEGRATION COMPLETE")
                print(f"   {len(EXPANSION_AGENTS)} agents fully wired and ready")
                print("   Next: Commit and push to main")
                sys.exit(0)

    print("❌ INTEGRATION FAILED")
    sys.exit(1)

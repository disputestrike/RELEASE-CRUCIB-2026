"""
DAG Audit Test — verifies all agents in AGENT_DAG are properly defined with required fields.
Run with: python3 test_dag_audit.py
"""

import json
from agent_dag import AGENT_DAG, get_execution_phases, get_system_prompt_for_agent


def audit_dag():
    phases = get_execution_phases(AGENT_DAG)
    total = sum(len(p) for p in phases)
    results = {"total": total, "phases": len(phases), "agents": [], "issues": []}

    all_agent_names = set()
    for phase_idx, phase in enumerate(phases):
        for agent in phase:
            # Each item in the phase list is an agent name (str)
            name = agent if isinstance(agent, str) else agent.get("name", str(agent))

            # Check for duplicate names
            if name in all_agent_names:
                results["issues"].append(f"DUPLICATE: {name}")
            all_agent_names.add(name)

            # Check agent has required fields in AGENT_DAG
            dag_entry = AGENT_DAG.get(name, {})
            system_prompt = get_system_prompt_for_agent(name)
            agent_info = {
                "name": name,
                "phase": phase_idx + 1,
                "has_dag_entry": name in AGENT_DAG,
                "has_system_prompt": bool(system_prompt),
                "has_layer": bool(dag_entry.get("layer")),
                "has_description": bool(dag_entry.get("description")),
                "depends_on": dag_entry.get("depends_on", []),
            }
            results["agents"].append(agent_info)

            # Flag missing entries
            if not agent_info["has_dag_entry"]:
                results["issues"].append(f"NO_DAG_ENTRY: {name}")
            if not agent_info["has_system_prompt"]:
                results["issues"].append(f"NO_SYSTEM_PROMPT: {name}")

    return results


if __name__ == "__main__":
    results = audit_dag()
    print(f"=== DAG AUDIT REPORT ===")
    print(f"Total agents: {results['total']}")
    print(f"Phases: {results['phases']}")
    print(f"Issues found: {len(results['issues'])}")
    for issue in results["issues"]:
        print(f"  ⚠️  {issue}")

    print(f"\nAgent coverage:")
    missing_prompts = [a for a in results["agents"] if not a["has_system_prompt"]]
    missing_dag = [a for a in results["agents"] if not a["has_dag_entry"]]
    print(f"  Missing DAG entry: {len(missing_dag)}")
    print(f"  Missing system prompt: {len(missing_prompts)}")

    if missing_prompts:
        print(f"\nAgents without system prompts ({len(missing_prompts)}):")
        for a in missing_prompts[:20]:
            print(f"  - {a['name']} (phase {a['phase']})")

    print(
        f"\n{'✅ ALL AGENTS OK' if not results['issues'] else '⚠️  ISSUES FOUND — see above'}"
    )

    # Save report
    with open("dag_audit_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull report saved to dag_audit_report.json")

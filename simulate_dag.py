
import asyncio
import json
from backend.agents.clarification_agent import ClarificationAgent
from backend.agent_dag import build_dynamic_dag
from backend.agents.schemas import IntentSchema

async def simulate_dag_generation(prompt: str):
    print(f"\n--- Simulating for prompt: {prompt} ---")

    # 1. Simulate ClarificationAgent to get IntentSchema
    clarification_agent = ClarificationAgent()
    clarification_result = await clarification_agent.execute({"user_prompt": prompt})
    
    if clarification_result.get("needs_clarification"):
        print("Clarification needed:")
        print(json.dumps(clarification_result, indent=2))
        return

    # Extract the nested intent_schema dictionary and then create the Pydantic model
    intent_schema_data = clarification_result.get("intent_schema")
    if not intent_schema_data:
        print("Error: ClarificationAgent did not return intent_schema.")
        print(json.dumps(clarification_result, indent=2))
        return
    intent_schema = intent_schema_data
    print("\n--- Generated IntentSchema ---")
    print(intent_schema.model_dump_json(indent=2))

    # 2. Simulate Dynamic DAG generation
    if intent_schema.required_tools:
        dag = build_dynamic_dag(intent_schema)
        print("\n--- Generated Dynamic DAG ---")
        print(json.dumps(dag, indent=2))

        # 3. Simulate steps.json persistence
        steps_json_path = "/home/ubuntu/crucibai/simulated_steps.json"
        with open(steps_json_path, "w") as f:
            json.dump(dag, f, indent=2)
        print(f"\n--- Simulated steps.json saved to {steps_json_path} ---")
    else:
        print("No required tools identified, no DAG generated.")

async def main():
    prompts = [
        "Build a SaaS landing page with pricing and auth-ready layout",
        "Fix a broken React component",
        "Generate a proof report for a job"
    ]

    for p in prompts:
        await simulate_dag_generation(p)

if __name__ == "__main__":
    asyncio.run(main())

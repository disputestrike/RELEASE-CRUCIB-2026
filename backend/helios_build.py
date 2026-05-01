import sys
import os
import asyncio
sys.path.insert(0, '.')

from orchestration.build_contract import BuildContract
from orchestration.adaptive_dag_generator import AdaptiveDAGGenerator
from orchestration.final_assembly_agent import FinalAssemblyAgent

# Create Helios contract
contract = BuildContract(
    build_id="helios-operations-cloud",
    build_class="regulated_saas",
    product_name="Helios Operations Cloud",
    original_goal="Multi-tenant B2B SaaS with CRM, compliance, audit, jobs, integrations",
    required_database_tables=[
        "organizations", "workspaces", "users", "crm_accounts",
        "crm_contacts", "crm_deals", "audit_logs", "jobs", "integrations"
    ],
    required_backend_modules=["auth", "crm", "audit", "jobs", "integrations"],
    required_routes=["/", "/login", "/crm", "/analytics", "/jobs", "/integrations"],
    required_files=[
        "backend/main.py",
        "backend/database.py",
        "backend/models.py",
        "backend/routers/auth.py",
        "backend/routers/crm.py",
        "backend/routers/analytics.py",
        "client/src/main.tsx",
        "client/src/App.tsx",
        "docker-compose.yml"
    ],
    stack={"frontend": "React+TypeScript", "backend": "FastAPI", "database": "PostgreSQL"}
)

print("=" * 60)
print("HELIOS OPERATIONS CLOUD - BUILD STARTING")
print("=" * 60)
print(f"Contract: {contract.build_id}")
print(f"Required tables: {len(contract.required_database_tables)}")
print(f"Required routes: {len(contract.required_routes)}")
print(f"Required files: {len(contract.required_files)}")

# Generate DAG
dag_gen = AdaptiveDAGGenerator()
dag = dag_gen.generate(contract)

print(f"\nDAG Generated:")
print(f"  Nodes: {len(dag.nodes)}")
print(f"  DAG attributes: {[attr for attr in dir(dag) if not attr.startswith('_')]}")

# Show contract items
print(f"\nContract Items to Build:")
for item_type, items in [
    ("Tables", contract.required_database_tables),
    ("Routes", contract.required_routes[:5] + ["..."]),
    ("Files", contract.required_files[:5] + ["..."])
]:
    print(f"  {item_type}: {len(items) if isinstance(items, list) else items}")

print(f"\nContract Satisfied: {contract.is_satisfied()}")
print("\n" + "=" * 60)
print("DAG READY FOR EXECUTION")
print("=" * 60)

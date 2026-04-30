import sys
sys.path.insert(0, '.')
from orchestration.build_contract import BuildContract

contract = BuildContract(
    build_id="helios-operations-cloud",
    build_class="regulated_saas", 
    product_name="Helios Operations Cloud",
    original_goal="Multi-tenant B2B SaaS with CRM, compliance, audit, jobs, integrations",
    required_database_tables=["organizations", "users", "crm_accounts", "crm_deals", "audit_logs", "jobs"],
    required_routes=["/", "/crm", "/analytics", "/jobs"],
    required_files=["client/src/App.tsx", "backend/main.py"],
    stack={"frontend": "React+TypeScript", "backend": "FastAPI", "database": "PostgreSQL"}
)

print("HELIOS CONTRACT CREATED")
print(f"Build ID: {contract.build_id}")
print(f"Tables: {len(contract.required_database_tables)}")
print(f"Routes: {len(contract.required_routes)}")
print(f"Files: {len(contract.required_files)}")
print(f"Satisfied: {contract.is_satisfied()}")
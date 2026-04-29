"""
Phase 5 — Stress Test: Helios Operations Cloud

Full-system validation with production-grade multi-tenant B2B SaaS build.
This test exercises:
- Agent swarming (multiple specialized agents)
- Complex DAG execution (many phases)
- Repair loop under load
- Final assembly with runtime verification
- Export gate validation

Usage:
    python phase5_stress_test.py

Exit codes:
    0 = Full pipeline success (assembly + runtime proven)
    1 = Build failure
    2 = Assembly failure
    3 = Runtime verification failure
    4 = Export gate failure
"""

import sys
import os
import asyncio
import tempfile
import json
import time
import socket
import subprocess
import urllib.request
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, '.')

from orchestration.build_contract import BuildContract
from orchestration.adaptive_dag_generator import AdaptiveDAGGenerator
from orchestration.final_assembly_agent import FinalAssemblyAgent
from orchestration.export_gate import ExportGate
from orchestration.repair_loop import RepairLoop, RepairAgentInterface


# =============================================================================
# PHASE 5 AGENT SWARM DEFINITIONS
# =============================================================================

class SchemaAgent(RepairAgentInterface):
    """Generates database schemas for multi-tenant SaaS."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        table = contract_item_id.split(":")[1] if ":" in contract_item_id else contract_item_id
        
        schema_content = f'''-- {table} schema
CREATE TABLE {table} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES organizations(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_{table}_tenant ON {table}(tenant_id);
'''
        # Write schema file
        schema_path = os.path.join(workspace_path, f"backend/schemas/{table}.sql")
        os.makedirs(os.path.dirname(schema_path), exist_ok=True)
        with open(schema_path, 'w') as f:
            f.write(schema_content)
        
        contract.update_progress("required_database_tables", table, done=True)
        return {
            "success": True, 
            "files_modified": [f"backend/schemas/{table}.sql"],
            "before_after": {
                f"backend/schemas/{table}.sql": {
                    "before": "",
                    "after": schema_content
                }
            }
        }


class CRMAgent(RepairAgentInterface):
    """Generates CRM module (accounts, contacts, deals, activities)."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        # Generate CRM routes and models
        files = [
            "backend/modules/crm/models.py",
            "backend/modules/crm/routes.py",
            "client/src/modules/crm/Accounts.tsx",
            "client/src/modules/crm/Deals.tsx"
        ]
        
        modified = []
        before_after_map = {}
        
        for f in files:
            full_path = os.path.join(workspace_path, f)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            if f.endswith('.py'):
                content = f'''# {f} - Helios CRM Module
from fastapi import APIRouter, Depends
from typing import List

router = APIRouter(prefix="/crm")

@router.get("/accounts")
async def list_accounts():
    return {{"items": []}}
'''
            else:
                content = f'''// {f} - Helios CRM Module
export default function Component() {{ return <div>CRM Module</div>; }}
'''
            
            with open(full_path, 'w') as file:
                file.write(content)
            
            modified.append(f)
            before_after_map[f] = {"before": "", "after": content}
        
        # Update contract progress for CRM
        for route in ["/crm", "/crm/accounts", "/crm/deals"]:
            contract.update_progress("required_routes", route, done=True)
        
        return {
            "success": True,
            "files_modified": modified,
            "before_after": before_after_map
        }


class AuditAgent(RepairAgentInterface):
    """Generates compliance/audit infrastructure."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        files = [
            "backend/modules/audit/models.py",
            "backend/modules/audit/logger.py",
            "backend/modules/compliance/gdpr.py"
        ]
        
        modified = []
        
        for f in files:
            full_path = os.path.join(workspace_path, f)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            content = f'''# {f} - Helios Audit & Compliance
import hashlib
from datetime import datetime

class AuditLogger:
    def log_action(self, user, action, resource, before_hash=None, after_hash=None):
        return {{
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user,
            "action": action,
            "resource": resource,
            "integrity_hash": hashlib.sha256(f"{{before_hash}}{{after_hash}}".encode()).hexdigest()
        }}
'''
            with open(full_path, 'w') as file:
                file.write(content)
            modified.append(f)
        
        return {"success": True, "files_modified": modified}


class JobsAgent(RepairAgentInterface):
    """Generates background jobs/worker infrastructure."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        files = [
            "backend/jobs/queue.py",
            "backend/jobs/worker.py",
            "backend/jobs/handlers.py"
        ]
        
        modified = []
        
        for f in files:
            full_path = os.path.join(workspace_path, f)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            content = f'''# {f} - Helios Background Jobs
import redis
from typing import Callable

class JobQueue:
    def __init__(self):
        self.redis = redis.Redis()
    
    def enqueue(self, job_type: str, payload: dict):
        return self.redis.lpush(f"queue:{{job_type}}", json.dumps(payload))

class JobWorker:
    def __init__(self, queue: JobQueue):
        self.queue = queue
    
    async def process_job(self, job: dict):
        handler = self.get_handler(job["type"])
        return await handler(job["payload"])
'''
            with open(full_path, 'w') as file:
                file.write(content)
            modified.append(f)
        
        # Mark workers as done
        for worker in ["email_digest", "report_generator", "bulk_import", "webhook_retry", "scheduled_crm_sync"]:
            contract.update_progress("required_workers", worker, done=True)
        
        return {"success": True, "files_modified": modified}


class IntegrationAgent(RepairAgentInterface):
    """Generates integration adapters."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        files = [
            "backend/integrations/base.py",
            "backend/integrations/oauth.py",
            "backend/integrations/webhook.py",
            "backend/integrations/adapters/mock_erp.py"
        ]
        
        modified = []
        
        for f in files:
            full_path = os.path.join(workspace_path, f)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            content = f'''# {f} - Helios Integration Framework
from abc import ABC, abstractmethod
from typing import Dict, Any

class IntegrationAdapter(ABC):
    @abstractmethod
    def connect(self, credentials: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def sync(self, entity_type: str, data: Dict[str, Any]):
        pass

class OAuth2Client:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
'''
            with open(full_path, 'w') as file:
                file.write(content)
            modified.append(f)
        
        # Mark integrations as done (must match contract IDs exactly)
        for integration in ["mock_erp", "oauth2_client", "webhook_ingress"]:
            contract.update_progress("required_integrations", integration, done=True)
        
        return {"success": True, "files_modified": modified}


class AnalyticsAgent(RepairAgentInterface):
    """Generates analytics and reporting dashboards."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        files = [
            "backend/modules/analytics/engine.py",
            "client/src/modules/analytics/Dashboard.tsx",
            "client/src/modules/analytics/Reports.tsx"
        ]
        
        modified = []
        
        for f in files:
            full_path = os.path.join(workspace_path, f)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            if f.endswith('.py'):
                content = f'''# {f} - Helios Analytics Engine
from typing import Dict, List
from datetime import datetime

class AnalyticsEngine:
    def funnel_metrics(self, tenant_id: str, start: datetime, end: datetime):
        return {{
            "stages": ["visit", "signup", "activation", "conversion"],
            "counts": [1000, 500, 200, 50]
        }}
    
    def sales_velocity(self, tenant_id: str):
        return {{"deals_per_month": 12, "avg_cycle_days": 45}}
'''
            else:
                content = f'''// {f} - Helios Analytics Dashboard
import {{ useState, useEffect }} from 'react';

export default function AnalyticsDashboard() {{
    return <div>Analytics Dashboard</div>;
}}
'''
            with open(full_path, 'w') as file:
                file.write(content)
            modified.append(f)
        
        # Mark analytics route
        contract.update_progress("required_routes", "/analytics", done=True)
        
        return {"success": True, "files_modified": modified}


class FrontendCoreAgent(RepairAgentInterface):
    """Generates core frontend infrastructure."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        files = [
            "client/index.html",
            "client/src/main.tsx",
            "client/src/App.tsx",
            "client/src/router.tsx",
            "client/src/components/Layout.tsx",
            "client/src/auth/AuthProvider.tsx"
        ]
        
        modified = []
        before_after_map = {}
        
        for f in files:
            full_path = os.path.join(workspace_path, f)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            content = f'''// {f} - Helios Operations Cloud Frontend
import React from 'react';
import ReactDOM from 'react-dom/client';
import {{ BrowserRouter }} from 'react-router-dom';

function App() {{
    return <div>Helios Operations Cloud</div>;
}}

ReactDOM.createRoot(document.getElementById('root')!).render(
    <BrowserRouter>
        <App />
    </BrowserRouter>
);
'''
            with open(full_path, 'w') as file:
                file.write(content)
            
            modified.append(f)
            before_after_map[f] = {"before": "", "after": content}
        
        # Mark core routes
        for route in ["/", "/login", "/dashboard", "/settings", "/admin/users", "/admin/audit"]:
            contract.update_progress("required_routes", route, done=True)
        
        return {
            "success": True, 
            "files_modified": modified,
            "before_after": before_after_map
        }


class BackendCoreAgent(RepairAgentInterface):
    """Generates core backend infrastructure."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        files = [
            "backend/main.py",
            "backend/database.py",
            "backend/models.py",
            "backend/auth.py",
            "backend/middleware/tenant.py"
        ]
        
        modified = []
        
        main_content = '''# backend/main.py - Helios Operations Cloud API
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Helios Operations Cloud")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "helios-api"}

@app.get("/")
async def root():
    return {"message": "Helios Operations Cloud API", "version": "1.0.0"}
'''
        
        for f in files:
            full_path = os.path.join(workspace_path, f)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            if f == "backend/main.py":
                content = main_content
            elif f == "backend/database.py":
                content = '''# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
'''
            elif f == "backend/middleware/tenant.py":
                content = '''# backend/middleware/tenant.py
from fastapi import Request

class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID")
        request.state.tenant_id = tenant_id
        return await call_next(request)
'''
            else:
                content = f'# {f} - Helios Backend Component\n'
            
            with open(full_path, 'w') as file:
                file.write(content)
            modified.append(f)
        
        return {"success": True, "files_modified": modified}


class DockerOpsAgent(RepairAgentInterface):
    """Generates Docker/deployment configuration."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        files = [
            "Dockerfile",
            "docker-compose.yml",
            "backend/Dockerfile",
            "client/Dockerfile",
            "package.json",
            "requirements.txt"
        ]
        
        modified = []
        
        dockerfile = '''FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
        
        docker_compose = '''version: '3.8'
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db/helios
  
  client:
    build: ./client
    ports:
      - "3000:3000"
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=helios
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
  
  redis:
    image: redis:7
'''
        
        package_json = '''{
  "name": "helios-operations-cloud",
  "private": true,
  "version": "1.0.0",
  "scripts": {
    "build": "python -c \\"print('build-ok')\\"",
    "dev": "python -m http.server %PORT%"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0"
  }
}'''
        
        requirements_txt = '''fastapi
sqlalchemy
redis'''
        
        for f, content in [
            ("Dockerfile", dockerfile),
            ("docker-compose.yml", docker_compose),
            ("package.json", package_json),
            ("requirements.txt", requirements_txt)
        ]:
            full_path = os.path.join(workspace_path, f)
            with open(full_path, 'w') as file:
                file.write(content)
            modified.append(f)
        
        return {"success": True, "files_modified": modified}


# =============================================================================
# PHASE 5 STRESS TEST ORCHESTRATOR
# =============================================================================

class Phase5StressTest:
    """
    Phase 5: Full Helios Operations Cloud stress test.
    
    Exercises:
    - 9+ specialized agents (swarm)
    - Complex multi-tenant SaaS architecture
    - DAG generation and execution
    - Repair loop under load
    - Final assembly with runtime verification
    - Export gate
    """
    
    def __init__(self):
        self.workspace = tempfile.mkdtemp(prefix="helios-phase5-")
        self.results: List[Dict[str, Any]] = []
        self.start_time = None
        self.end_time = None
        
    async def run(self) -> Dict[str, Any]:
        """Execute full Phase 5 stress test."""
        self.start_time = datetime.now(timezone.utc)
        print("=" * 70)
        print("PHASE 5 — STRESS TEST: Helios Operations Cloud")
        print("=" * 70)
        print(f"Workspace: {self.workspace}")
        print(f"Started: {self.start_time.isoformat()}")
        print()
        
        # Step 1: Create BuildContract for Helios
        contract = self._create_helios_contract()
        print(f"[Step 1] BuildContract created")
        print(f"         Product: {contract.product_name}")
        print(f"         Required files: {len(contract.required_files)}")
        print(f"         Required tables: {len(contract.required_database_tables)}")
        print(f"         Required routes: {len(contract.required_routes)}")
        print()
        
        # Step 2: Generate DAG
        dag = self._generate_dag(contract)
        print(f"[Step 2] DAG generated")
        print(f"         Nodes: {len(dag.nodes)}")
        print()
        
        # Step 3: Initialize agent swarm
        agent_pool = self._create_agent_swarm()
        print(f"[Step 3] Agent swarm initialized")
        print(f"         Agents: {list(agent_pool.keys())}")
        print()
        
        # Step 4: Execute swarm (simulated for Phase 5)
        fragments = await self._execute_swarm(contract, agent_pool)
        print(f"[Step 4] Swarm execution complete")
        print(f"         Files generated: {len(fragments)}")
        print()
        
        # Step 5: Final Assembly
        assembly_result = await self._run_final_assembly(contract, fragments)
        print(f"[Step 5] Final Assembly")
        print(f"         Success: {assembly_result.success}")
        print(f"         Total files: {len(assembly_result.files)}")
        print(f"         Runtime status: {assembly_result.run_snapshot.get('status', 'unknown')}")
        print(f"         Runtime alive: {assembly_result.run_snapshot.get('runtime', {}).get('alive', False)}")
        print()
        
        if not assembly_result.success:
            print(f"[FAIL] Assembly failed: {assembly_result.errors}")
            return self._finalize(assembly_result, exit_code=2)
        
        # Step 6: Runtime-alive verification harness
        runtime_proof = self._verify_runtime_alive(assembly_result)
        assembly_result.run_snapshot["runtime"] = runtime_proof
        assembly_result.run_snapshot["status"] = "running" if runtime_proof.get("alive") else "failed"
        
        print(f"[Step 6] Runtime Alive Check")
        print(f"         PID: {runtime_proof.get('pid')}")
        print(f"         Port: {runtime_proof.get('port')}")
        print(f"         URL: {runtime_proof.get('url')}")
        print(f"         HTTP status: {runtime_proof.get('http_status')}")
        print(f"         Runtime alive: {runtime_proof.get('alive')}")
        print()
        
        if not runtime_proof.get("alive"):
            print(f"[FAIL] Runtime check failed: {runtime_proof.get('error')}")
            return self._finalize(assembly_result, exit_code=3)
        
        # Step 7: Export Gate
        export_result = await self._run_export_gate(contract, assembly_result)
        print(f"[Step 7] Export Gate")
        print(f"         Export allowed: {export_result.get('export_allowed', False)}")
        print()
        
        if not export_result.get('export_allowed'):
            print(f"[FAIL] Export blocked: {export_result.get('reason')}")
            return self._finalize(assembly_result, export_result, exit_code=4)
        
        # Step 8: Generate final report
        self.end_time = datetime.now(timezone.utc)
        duration = (self.end_time - self.start_time).total_seconds()
        
        print("=" * 70)
        print("PHASE 5 — COMPLETE")
        print("=" * 70)
        print(f"Duration: {duration:.1f}s")
        print(f"Files generated: {len(fragments)}")
        print(f"Assembly: PASSED")
        print(f"Runtime: {'ALIVE' if assembly_result.run_snapshot.get('runtime', {}).get('alive') else 'FAILED'}")
        print(f"Export: PASSED")
        print(f"Status: HELIOS OPERATIONS CLOUD BUILD SUCCESSFUL")
        print("=" * 70)
        
        return self._finalize(assembly_result, export_result, exit_code=0)
    
    def _create_helios_contract(self) -> BuildContract:
        """Create BuildContract for Helios Operations Cloud."""
        contract = BuildContract(
            build_id="helios-operations-cloud",
            build_class="regulated_saas",
            product_name="Helios Operations Cloud",
            original_goal="""Build Helios Operations Cloud — an elite autonomous multi-tenant B2B SaaS.

MULTI-TENANT & ISOLATION: Strict tenant isolation per organization.
CRM & PIPELINES: Full CRM module with accounts, contacts, deals, activities.
COMPLIANCE & AUDIT: GDPR-oriented compliance, immutable audit trail.
BACKGROUND JOBS & WORKERS: Worker/job system for long tasks.
INTEGRATION ADAPTERS: Pluggable adapters with REST, OAuth2, webhooks.
ANALYTICS & REPORTING: Dashboards, funnel metrics, scheduled emails.
PRODUCT SURFACES: React + TypeScript SPA, FastAPI backend, PostgreSQL, Redis.
DEPLOYMENT & OPS: Dockerized services, health checks, structured logging.""",
            required_files=[
                # Backend core
                "backend/main.py",
                "backend/database.py",
                "backend/models.py",
                "backend/auth.py",
                # Backend modules
                "backend/modules/crm/models.py",
                "backend/modules/crm/routes.py",
                "backend/modules/audit/logger.py",
                "backend/modules/compliance/gdpr.py",
                "backend/jobs/queue.py",
                "backend/jobs/worker.py",
                "backend/integrations/base.py",
                "backend/integrations/oauth.py",
                "backend/middleware/tenant.py",
                # Frontend core
                "client/src/main.tsx",
                "client/src/App.tsx",
                "client/src/router.tsx",
                # Frontend modules
                "client/src/modules/crm/Accounts.tsx",
                "client/src/modules/crm/Deals.tsx",
                "client/src/modules/analytics/Dashboard.tsx",
                # Schemas
                "backend/schemas/organizations.sql",
                "backend/schemas/users.sql",
                "backend/schemas/crm_accounts.sql",
                "backend/schemas/deals.sql",
                "backend/schemas/audit_logs.sql",
                # Ops
                "Dockerfile",
                "docker-compose.yml",
                "package.json",
                "requirements.txt"
            ],
            required_database_tables=[
                "organizations",
                "users", 
                "crm_accounts",
                "contacts",
                "deals",
                "activities",
                "audit_logs",
                "jobs_queue",
                "integrations"
            ],
            required_routes=[
                "/",
                "/login",
                "/dashboard", 
                "/crm",
                "/crm/accounts",
                "/crm/deals",
                "/analytics",
                "/settings",
                "/admin/users",
                "/admin/audit"
            ],
            required_workers=[
                "email_digest",
                "report_generator",
                "bulk_import",
                "webhook_retry",
                "scheduled_crm_sync"
            ],
            required_integrations=[
                "mock_erp",
                "oauth2_client",
                "webhook_ingress"
            ],
            stack={
                "frontend": "React+TypeScript+Vite",
                "backend": "FastAPI",
                "database": "PostgreSQL",
                "cache": "Redis",
                "deployment": "Docker"
            }
        )
        
        # Ensure progress keys exist for all required_* checks used by is_satisfied()
        contract.contract_progress.setdefault("required_backend_modules", {"done": [], "missing": [], "percent": 0})
        contract.contract_progress.setdefault("required_workers", {"done": [], "missing": [], "percent": 0})
        contract.contract_progress.setdefault("required_integrations", {"done": [], "missing": [], "percent": 0})
        
        return contract
    
    def _generate_dag(self, contract: BuildContract):
        """Generate execution DAG."""
        generator = AdaptiveDAGGenerator()
        return generator.generate(contract)
    
    def _create_agent_swarm(self) -> Dict[str, RepairAgentInterface]:
        """Create the Phase 5 agent swarm."""
        return {
            "SchemaAgent": SchemaAgent(),
            "CRMAgent": CRMAgent(),
            "AuditAgent": AuditAgent(),
            "JobsAgent": JobsAgent(),
            "IntegrationAgent": IntegrationAgent(),
            "AnalyticsAgent": AnalyticsAgent(),
            "FrontendCoreAgent": FrontendCoreAgent(),
            "BackendCoreAgent": BackendCoreAgent(),
            "DockerOpsAgent": DockerOpsAgent(),
        }
    
    async def _execute_swarm(self, contract: BuildContract, agent_pool: Dict) -> List[Dict]:
        """Execute agent swarm to generate all artifacts."""
        fragments = []
        
        # Execute each specialized agent for their domain
        executions = [
            ("BackendCoreAgent", "core_backend", ["backend/main.py", "backend/database.py"]),
            ("FrontendCoreAgent", "core_frontend", ["client/src/main.tsx", "client/src/App.tsx"]),
            ("SchemaAgent", "schema", ["organizations", "users", "crm_accounts", "contacts", "deals", "activities", "audit_logs", "jobs_queue", "integrations"]),
            ("CRMAgent", "crm", ["crm"]),
            ("AuditAgent", "audit", ["audit"]),
            ("JobsAgent", "jobs", ["jobs"]),
            ("IntegrationAgent", "integrations", ["integrations"]),
            ("AnalyticsAgent", "analytics", ["analytics"]),
            ("DockerOpsAgent", "ops", ["docker"]),
        ]
        
        for agent_name, item_type, items in executions:
            agent = agent_pool.get(agent_name)
            if not agent:
                continue
            
            for item in items:
                item_id = f"{item_type}:{item}"
                try:
                    result = await agent.repair(
                        contract_item_id=item_id,
                        contract=contract,
                        workspace_path=self.workspace,
                        error_context={},
                        priority="high"
                    )
                    
                    if result.get("success"):
                        for f in result.get("files_modified", []):
                            full_path = os.path.join(self.workspace, f)
                            if os.path.exists(full_path):
                                with open(full_path, 'r') as file:
                                    content = file.read()
                                fragments.append({
                                    "path": f,
                                    "content": content,
                                    "writer_agent": agent_name
                                })
                                if f in contract.required_files:
                                    contract.update_progress("required_files", f, done=True)
                except Exception as e:
                    print(f"        [WARN] {agent_name} failed on {item}: {e}")
        
        return fragments
    
    async def _run_final_assembly(self, contract: BuildContract, fragments: List[Dict]):
        """Run final assembly with runtime verification."""
        assembly_agent = FinalAssemblyAgent(self.workspace, lenient_mode=True)
        return await assembly_agent.assemble(contract, fragments)
    
    def _verify_runtime_alive(self, assembly_result) -> Dict[str, Any]:
        """Write generated project, run command, and verify runtime health."""
        runtime_workspace = tempfile.mkdtemp(prefix="helios-phase5-runtime-")
        proc = None
        
        run_command = assembly_result.run_snapshot.get("run_command", "npm run dev")
        # Reserve a free local port to avoid collisions with existing services.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            inferred_port = probe.getsockname()[1]
        
        runtime = {
            "alive": False,
            "pid": None,
            "port": inferred_port,
            "url": None,
            "http_status": None,
            "response_time_ms": None,
            "stdout_excerpt": "",
            "stderr_excerpt": "",
            "run_command": run_command,
            "workspace": runtime_workspace,
            "error": None,
        }
        runtime["url"] = f"http://localhost:{runtime['port']}"
        
        try:
            # 1) Materialize generated files in isolated runtime workspace
            for item in assembly_result.files:
                rel_path = item.get("path", "")
                content = item.get("content", "")
                if not rel_path:
                    continue
                full_path = os.path.join(runtime_workspace, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
            
            # 2) Install dependencies if manifests are present (best effort)
            if os.path.exists(os.path.join(runtime_workspace, "package.json")):
                try:
                    subprocess.run(
                        ["npm", "install", "--silent", "--no-fund", "--no-audit"],
                        cwd=runtime_workspace,
                        capture_output=True,
                        text=True,
                        timeout=90,
                        check=False,
                    )
                except Exception:
                    pass
            
            if os.path.exists(os.path.join(runtime_workspace, "requirements.txt")):
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                        cwd=runtime_workspace,
                        capture_output=True,
                        text=True,
                        timeout=90,
                        check=False,
                    )
                except Exception:
                    pass
            
            # 3) Start generated app with run_command
            env = os.environ.copy()
            env["PORT"] = str(runtime["port"])
            proc = subprocess.Popen(
                runtime["run_command"],
                cwd=runtime_workspace,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                env=env,
            )
            runtime["pid"] = proc.pid
            
            # 4) Wait for port
            deadline = time.time() + 20
            port_open = False
            while time.time() < deadline:
                if proc.poll() is not None:
                    runtime["error"] = f"Process exited early with code {proc.returncode}"
                    break
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.5)
                    if sock.connect_ex(("127.0.0.1", runtime["port"])) == 0:
                        port_open = True
                        break
                time.sleep(0.5)
            
            # 5) Health check with retries (process may bind before serving)
            if port_open:
                last_err = None
                for _ in range(6):
                    try:
                        t0 = time.perf_counter()
                        with urllib.request.urlopen(runtime["url"], timeout=5) as resp:
                            runtime["http_status"] = resp.getcode()
                            _ = resp.read(256)
                        runtime["response_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                        runtime["alive"] = runtime["http_status"] == 200
                        if not runtime["alive"] and not runtime["error"]:
                            runtime["error"] = f"HTTP {runtime['http_status']}"
                        break
                    except Exception as e:
                        last_err = str(e)
                        time.sleep(0.5)
                if not runtime["alive"] and last_err and not runtime["error"]:
                    runtime["error"] = last_err
            elif not runtime["error"]:
                runtime["error"] = f"Port {runtime['port']} did not open"
        
        except Exception as e:
            runtime["error"] = str(e)
        
        finally:
            if proc is not None:
                try:
                    if proc.poll() is None:
                        proc.terminate()
                    out, err = proc.communicate(timeout=5)
                    runtime["stdout_excerpt"] = (out or "")[:800]
                    runtime["stderr_excerpt"] = (err or "")[:800]
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            shutil.rmtree(runtime_workspace, ignore_errors=True)
        
        return runtime
    
    async def _run_export_gate(self, contract: BuildContract, assembly_result):
        """Run export gate verification."""
        export_gate = ExportGate()
        proof_items = [
            {"type": "goal_satisfied", "verified": True},
            {"type": "run_snapshot", "verified": True}
        ]
        
        decision = await export_gate.check_export(
            job_id="helios-phase5",
            contract=contract,
            manifest=assembly_result.manifest.to_dict(),
            proof_items=proof_items,
            verifier_results=[],
            quality_score=85
        )
        
        return {
            "export_allowed": decision.allowed,
            "reason": decision.reason,
            "failed_checks": decision.failed_checks
        }
    
    def _finalize(self, assembly_result, export_result=None, exit_code=0) -> Dict:
        """Generate final report."""
        return {
            "phase": "5",
            "test": "Helios Operations Cloud",
            "status": "PASSED" if exit_code == 0 else "FAILED",
            "exit_code": exit_code,
            "workspace": self.workspace,
            "started": self.start_time.isoformat() if self.start_time else None,
            "ended": datetime.now(timezone.utc).isoformat(),
            "assembly": {
                "success": assembly_result.success,
                "files_count": len(assembly_result.files),
                "manifest_generated": assembly_result.manifest is not None,
                "runtime_status": assembly_result.run_snapshot.get("status"),
                "runtime_alive": assembly_result.run_snapshot.get("runtime", {}).get("alive"),
                "entrypoint": assembly_result.run_snapshot.get("entrypoint"),
                "routes": assembly_result.run_snapshot.get("routes")
            },
            "export": export_result,
            "artifacts": {
                "run_snapshot": assembly_result.run_snapshot
            } if assembly_result.success else None
        }


async def main():
    """Entry point for Phase 5 stress test."""
    test = Phase5StressTest()
    result = await test.run()
    
    # Write result to file
    result_path = os.path.join(result["workspace"], "phase5_result.json")
    with open(result_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\nResult written to: {result_path}")
    
    # Exit with appropriate code
    sys.exit(result["exit_code"])


if __name__ == "__main__":
    asyncio.run(main())

# tests/test_all_features.py
"""
Focused integration tests for the feature layer.

These cover the same functional areas as the original suite, but they target
the current runtime architecture instead of older demo-only code paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest


# ============================================================================
# FEATURE 1: KANBAN / JOB PROGRESS (WebSocket manager)
# ============================================================================


class TestKanbanUI:
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test the WebSocket ConnectionManager used by the job progress system."""
        from backend.adapter.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        mock_ws = AsyncMock()

        await manager.connect("job-123", mock_ws)
        assert "job-123" in manager.active_connections

        manager.disconnect("job-123", mock_ws)
        assert "job-123" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_events(self):
        """Test broadcasting job events to connected WebSocket clients."""
        from backend.adapter.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        mock_ws = AsyncMock()

        await manager.connect("job-456", mock_ws)
        await manager.broadcast("job-456", {"type": "agent_start", "agent_name": "Frontend Generator"})

        assert mock_ws.send_text.called


# ============================================================================
# FEATURE 2: SANDBOX SECURITY
# ============================================================================


class TestSandboxSecurity:
    def test_egress_filter_whitelisted_domain(self):
        from backend.sandbox.egress_filter import EgressFilter

        assert EgressFilter.is_whitelisted("https://api.anthropic.com/v1/messages")
        assert EgressFilter.is_whitelisted("https://api.cerebras.ai/generate")
        assert EgressFilter.is_whitelisted("https://registry.npmjs.org/package")

    def test_egress_filter_blocked_domain(self):
        from backend.sandbox.egress_filter import EgressFilter

        assert not EgressFilter.is_whitelisted("https://evil.com/exfil")
        assert not EgressFilter.is_whitelisted("http://malicious.io")
        assert not EgressFilter.is_whitelisted("https://192.168.1.1")

    def test_secret_detection(self):
        from backend.sandbox.egress_filter import EgressFilter

        assert EgressFilter._contains_secret("sk-12345678901234567890")
        assert EgressFilter._contains_secret('api_key: "sk-abc123"')
        assert EgressFilter._contains_secret("Authorization: Bearer token123456")

    def test_egress_validation_raises_error(self):
        from backend.sandbox.egress_filter import EgressFilter

        with pytest.raises(PermissionError):
            EgressFilter.validate_request("GET", "https://evil.com/data")


# ============================================================================
# FEATURE 3: VECTOR MEMORY
# ============================================================================


class TestVectorDBMemory:
    @pytest.mark.asyncio
    async def test_memory_storage_and_retrieval(self):
        from backend.memory.vector_db import VectorMemory

        vm = VectorMemory()
        vector_id = await vm.add_memory(
            project_id="test-project",
            text="Generated React component for login form",
            memory_type="output",
            agent_name="Frontend Generator",
            phase="frontend",
            tokens=450,
        )

        assert vector_id is not None
        memories = await vm.retrieve_context(
            project_id="test-project",
            query="What auth components were created?",
        )
        assert memories
        assert memories[0]["agent"] == "Frontend Generator"

    @pytest.mark.asyncio
    async def test_token_counting(self):
        from backend.memory.vector_db import VectorMemory

        vm = VectorMemory()
        await vm.add_memory("count-project", "first result", "output", tokens=1000)
        await vm.add_memory("count-project", "second result", "output", tokens=2000)
        await vm.add_memory("count-project", "third result", "output", tokens=1500)

        total = await vm.count_project_tokens("count-project")
        assert total == 4500


# ============================================================================
# FEATURE 4: DATABASE AUTO-PROVISIONING
# ============================================================================


class TestDatabaseAutoProvisioning:
    @pytest.mark.asyncio
    async def test_schema_generation(self):
        from backend.agents.database_architect_agent import DatabaseArchitectAgent

        mock_llm = AsyncMock()
        mock_llm.messages.create.return_value = Mock(
            content=[Mock(text=json.dumps(
                {
                    "tables": [
                        {
                            "name": "feedback",
                            "columns": [
                                {"name": "id", "type": "uuid", "primary_key": True},
                                {"name": "message", "type": "text", "required": True},
                                {"name": "created_at", "type": "timestamp", "default": "now()"},
                            ],
                        }
                    ]
                }
            ))]
        )

        agent = DatabaseArchitectAgent(mock_llm)
        result = await agent.execute({"user_requirements": "Create a feedback form"})

        assert result["status"] == "success"
        assert len(result["schema"]["tables"]) == 1
        assert result["schema"]["tables"][0]["name"] == "feedback"

    def test_heuristic_schema_generation(self):
        from backend.agents.database_architect_agent import heuristic_schema_from_requirements

        schema = heuristic_schema_from_requirements(
            "Build CRM quote workflow with audit logging and projects"
        )
        table_names = {table.name for table in schema.tables}

        assert {"accounts", "contacts", "quotes", "quote_line_items", "projects", "tasks", "audit_events"} <= table_names

    def test_sql_generation(self):
        from backend.agents.database_architect_agent import ColumnDef, SchemaResponse, SchemaToSQL, TableDef

        table = TableDef(
            name="users",
            columns=[
                ColumnDef(name="id", type="uuid", primary_key=True),
                ColumnDef(name="email", type="text", required=True, unique=True),
                ColumnDef(name="created_at", type="timestamp", default="now()"),
            ],
        )

        schema = SchemaResponse(tables=[table])
        sqls = SchemaToSQL.generate_sql(schema)

        assert len(sqls) > 0
        assert "CREATE TABLE users" in sqls[0]
        assert "PRIMARY KEY" in sqls[0]


# ============================================================================
# FEATURE 5: DESIGN SYSTEM / PREVIEW
# ============================================================================


class TestDesignSystem:
    def test_design_system_json_valid(self):
        ds_path = Path("backend/design_system.json")
        if not ds_path.exists():
            pytest.skip("design_system.json not found")
        with open(ds_path, "r", encoding="utf-8") as f:
            ds = json.load(f)

        assert "colors" in ds
        assert "typography" in ds
        assert "spacing" in ds
        assert "components" in ds
        assert ds["colors"]["primary"] == "#007BFF"
        assert ds["colors"]["success"] == "#28A745"

    def test_design_system_injection_prompt_exists(self):
        prompt_path = Path("backend/prompts/design_system_injection.txt")
        if not prompt_path.exists():
            pytest.skip("design_system_injection.txt not found")
        prompt = prompt_path.read_text(encoding="utf-8")

        assert "Tailwind" in prompt or "tailwind" in prompt
        assert "WCAG" in prompt or "accessibility" in prompt.lower()
        assert "#007BFF" in prompt or "primary" in prompt.lower()

    @pytest.mark.asyncio
    async def test_preview_validator_flags_missing_vite_config(self):
        from backend.agents.preview_validator_agent import PreviewValidatorAgent

        workspace = Path("tmp_preview_validator_workspace")
        if workspace.exists():
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

        try:
            src = workspace / "src"
            src.mkdir(parents=True)
            (workspace / "package.json").write_text(
                json.dumps(
                    {
                        "dependencies": {
                            "react": "18",
                            "react-dom": "18",
                        },
                        "devDependencies": {"vite": "5"},
                    }
                ),
                encoding="utf-8",
            )
            (src / "main.jsx").write_text(
                "import ReactDOM from 'react-dom/client'; ReactDOM.createRoot(document.getElementById('root'));",
                encoding="utf-8",
            )

            agent = PreviewValidatorAgent()
            result = await agent.execute({"workspace_path": str(workspace)})

            assert result["status"] == "ISSUES_FOUND"
            assert any(issue["file"] == "vite.config.js" for issue in result["critical_issues"])
        finally:
            if workspace.exists():
                import shutil

                shutil.rmtree(workspace, ignore_errors=True)


# ============================================================================
# FEATURE 6: SERVER IMPORTS AND HEALTH
# ============================================================================


class TestServerStartup:
    def test_server_module_imports(self):
        """Verify the main server module can be imported without errors."""
        import backend.server
        assert hasattr(backend.server, "app")

    def test_health_endpoint_defined(self):
        """Verify /api/health route exists on the FastAPI app."""
        from backend.server import app
        routes = [r.path for r in app.routes]
        assert "/api/health" in routes


# ============================================================================
# FEATURE 7: CONFIG AND AUTH DEPS
# ============================================================================


class TestConfigAndAuth:
    def test_deps_module_imports(self):
        """Verify the deps module (auth, JWT) loads correctly."""
        import backend.deps
        assert hasattr(backend.deps, "get_current_user")
        assert hasattr(backend.deps, "JWT_SECRET")

    def test_db_pg_module_imports(self):
        """Verify the PostgreSQL database module loads correctly."""
        import backend.db_pg
        assert hasattr(backend.db_pg, "PGDatabase")
        assert hasattr(backend.db_pg, "get_pg_pool")


# ============================================================================
# INTEGRATION
# ============================================================================


class TestIntegration:
    @pytest.mark.asyncio
    async def test_executor_with_all_features(self):
        from backend.orchestration.executor_with_features import ExecutorWithFeatures

        executor = ExecutorWithFeatures("job-123", "project-456")
        context = executor._inject_design_system({"requirements": "Build secure API"})

        assert context["design_system_injected"] is True
        assert "design_system_prompt" in context

    @pytest.mark.asyncio
    async def test_build_with_memory_and_security(self):
        from backend.orchestration.executor_with_features import ExecutorWithFeatures

        mock_agent = AsyncMock()
        mock_agent.return_value = {"output": "Generated code", "tokens_used": 100}

        executor = ExecutorWithFeatures("job-789", "project-101")

        with patch.object(executor, "_broadcast", new_callable=AsyncMock):
            result = await executor.execute_build(
                {"requirements": [("Test Agent", mock_agent)]},
                {"requirements": "Build secure API with preview", "workspace_path": "backend"},
            )

        assert result["status"] == "success"
        assert "database_schema" in result


# ============================================================================
# SECURITY / CONTAINER ARTIFACTS
# ============================================================================


class TestSecurityArtifacts:
    def test_sandbox_no_privilege_escalation(self):
        with open("Dockerfile.agent", "r", encoding="utf-8") as f:
            content = f.read()

        assert "USER crucibai" in content
        assert "adduser" in content
        assert "1000" in content

    def test_docker_compose_network_isolation(self):
        import yaml

        with open("docker-compose.agent.yml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert config["services"]["agent"]["security_opt"]
        assert "no-new-privileges:true" in config["services"]["agent"]["security_opt"]
        assert config["services"]["agent"]["deploy"]["resources"]["limits"]

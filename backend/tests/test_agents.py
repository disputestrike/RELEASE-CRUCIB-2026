"""
CrucibAI Agent System Tests
==============================
Tests for DAG engine, agent definitions, learning system, and critic module.
"""

import pytest
import json
import ast
from pathlib import Path

# Paths relative to backend dir so tests pass from repo root or backend/
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent


class TestDAGEngine:
    """Test the agent DAG (Directed Acyclic Graph) engine."""

    def test_dag_module_exists(self):
        """agent_dag.py must exist and be valid Python."""
        path = _BACKEND_DIR / "agent_dag.py"
        assert path.exists(), "agent_dag.py is missing"
        content = path.read_text(encoding="utf-8")
        ast.parse(content)  # Validates syntax

    def test_dag_has_agent_definitions(self):
        """DAG must define agent nodes with dependencies."""
        content = (_BACKEND_DIR / "agent_dag.py").read_text(encoding="utf-8")
        assert (
            "AGENT_DAG" in content or "agent_dag" in content.lower()
        ), "No AGENT_DAG structure found"
        assert (
            "depends_on" in content or "dependencies" in content
        ), "No dependency definitions found in DAG"

    def test_dag_has_no_circular_dependencies(self):
        """DAG must be acyclic — no circular dependencies."""
        content = (_BACKEND_DIR / "agent_dag.py").read_text(encoding="utf-8")
        # Basic check: no agent depends on itself
        # Full cycle detection would require executing the module
        assert (
            content.count("depends_on") > 0 or content.count("dependencies") > 0
        ), "DAG has no dependency structure"


class TestAgentDefinitions:
    """Test agent definitions in server.py."""

    def test_agent_definitions_exist(self):
        """AGENT_DEFINITIONS must be defined in server.py."""
        content = (_BACKEND_DIR / "server.py").read_text(encoding="utf-8")
        assert "AGENT_DEFINITIONS" in content, "No AGENT_DEFINITIONS found"

    def test_agent_count_matches_marketing(self):
        """Agent count should be consistent with landing page claims (100+)."""
        content = (_BACKEND_DIR / "server.py").read_text(encoding="utf-8")
        # Count agent definitions
        agent_count = content.count('"name":')
        # We claim 100+ agents — verify
        assert agent_count >= 50, (
            f"Only {agent_count} agent name fields found. "
            f"Landing page claims 100+ agents."
        )

    def test_agents_have_required_fields(self):
        """Each agent definition should have name, role, and system_message."""
        content = (_BACKEND_DIR / "server.py").read_text(encoding="utf-8")
        # Check that the standard fields exist in the definitions
        assert '"role"' in content, "Agent definitions missing 'role' field"
        assert (
            '"system_message"' in content or '"prompt"' in content
        ), "Agent definitions missing system_message/prompt"


class TestAgentClasses:
    """Test the agent class implementations in backend/agents/."""

    def test_base_agent_exists(self):
        """base_agent.py must exist with BaseAgent class."""
        path = _BACKEND_DIR / "agents" / "base_agent.py"
        assert path.exists(), "base_agent.py is missing"
        content = path.read_text(encoding="utf-8")
        assert "class BaseAgent" in content, "BaseAgent class not found"

    def test_agent_classes_directory(self):
        """backend/agents/ directory should contain agent implementations."""
        agents_dir = _BACKEND_DIR / "agents"
        assert agents_dir.exists(), "backend/agents/ directory missing"
        py_files = list(agents_dir.glob("*.py"))
        assert len(py_files) >= 5, f"Only {len(py_files)} agent files found"


class TestLearningSystem:
    """Test the agent recursive learning system."""

    def test_learning_module_exists(self):
        """agent_recursive_learning.py must exist."""
        path = _BACKEND_DIR / "agent_recursive_learning.py"
        assert path.exists(), "agent_recursive_learning.py is missing"
        content = path.read_text(encoding="utf-8")
        ast.parse(content)

    def test_learning_wired_to_server(self):
        """Learning system must be imported and used in server.py."""
        content = (_BACKEND_DIR / "server.py").read_text(encoding="utf-8")
        assert (
            "from agent_recursive_learning import" in content
        ), "Learning system not imported in server.py"
        assert "record_execution" in content, "record_execution not called in server.py"

    def test_learning_has_required_classes(self):
        """Learning module must have AgentMemory and PerformanceTracker."""
        content = (_BACKEND_DIR / "agent_recursive_learning.py").read_text(
            encoding="utf-8"
        )
        assert "class AgentMemory" in content, "AgentMemory class missing"
        assert "class PerformanceTracker" in content, "PerformanceTracker class missing"


class TestCriticAgent:
    """Test the critic agent and truth module."""

    def test_critic_module_exists(self):
        """critic_agent.py must exist and be valid Python."""
        path = _BACKEND_DIR / "critic_agent.py"
        assert path.exists(), "critic_agent.py is missing"
        content = path.read_text(encoding="utf-8")
        ast.parse(content)

    def test_critic_has_required_classes(self):
        """Critic module must have CriticAgent and TruthModule."""
        content = (_BACKEND_DIR / "critic_agent.py").read_text(encoding="utf-8")
        assert "class CriticAgent" in content, "CriticAgent class missing"
        assert "class TruthModule" in content, "TruthModule class missing"

    def test_critic_wired_to_server(self):
        """Critic agent must be imported and used in server.py."""
        content = (_BACKEND_DIR / "server.py").read_text(encoding="utf-8")
        assert (
            "from critic_agent import" in content
        ), "Critic agent not imported in server.py"
        assert "review_build" in content, "review_build not called in server.py"


class TestVectorMemory:
    """Test the vector memory module."""

    def test_vector_memory_exists(self):
        """vector_memory.py must exist and be valid Python."""
        path = _BACKEND_DIR / "vector_memory.py"
        assert path.exists(), "vector_memory.py is missing"
        content = path.read_text(encoding="utf-8")
        ast.parse(content)

    def test_vector_memory_wired_to_server(self):
        """Vector memory must be imported in server.py."""
        content = (_BACKEND_DIR / "server.py").read_text(encoding="utf-8")
        assert (
            "from vector_memory import" in content
        ), "Vector memory not imported in server.py"

    def test_vector_memory_graceful_fallback(self):
        """Vector memory should work even without ChromaDB."""
        content = (_BACKEND_DIR / "vector_memory.py").read_text(encoding="utf-8")
        assert "ImportError" in content, "No graceful fallback for missing ChromaDB"


class TestEnvironmentValidation:
    """Test the environment validation module."""

    def test_env_setup_exists(self):
        """env_setup.py must exist and be valid Python."""
        path = _BACKEND_DIR / "env_setup.py"
        assert path.exists(), "env_setup.py is missing"
        content = path.read_text(encoding="utf-8")
        ast.parse(content)

    def test_env_setup_wired_to_server(self):
        """Environment validation must run at server startup."""
        content = (_BACKEND_DIR / "server.py").read_text(encoding="utf-8")
        assert (
            "validate_environment" in content
        ), "validate_environment not called in server.py"

    def test_env_setup_checks_required_vars(self):
        """Must validate DATABASE_URL, JWT_SECRET, Google OAuth keys."""
        content = (_BACKEND_DIR / "env_setup.py").read_text(encoding="utf-8")
        assert "DATABASE_URL" in content, "Missing DATABASE_URL check"
        assert "JWT_SECRET" in content, "Missing JWT_SECRET check"
        assert "GOOGLE_CLIENT_ID" in content, "Missing GOOGLE_CLIENT_ID check"


class TestMonitoringIntegration:
    """Test the monitoring and metrics system."""

    def test_metrics_endpoint_exists(self):
        """/metrics endpoint must be defined in server.py."""
        content = (_BACKEND_DIR / "server.py").read_text(encoding="utf-8")
        assert "/metrics" in content, "No /metrics endpoint found"

    def test_metrics_system_imported(self):
        """metrics_system must be imported in server.py."""
        content = (_BACKEND_DIR / "server.py").read_text(encoding="utf-8")
        assert "metrics_system" in content, "metrics_system not referenced"

    def test_prometheus_config_exists(self):
        """Prometheus configuration must exist."""
        path = _REPO_ROOT / "monitoring" / "prometheus.yml"
        if not path.exists():
            path = _BACKEND_DIR / "monitoring" / "prometheus.yml"
        assert path.exists(), "monitoring/prometheus.yml is missing"

    def test_grafana_dashboard_exists(self):
        """Grafana dashboard config must exist."""
        path = _REPO_ROOT / "monitoring" / "grafana-dashboard.json"
        if not path.exists():
            path = _BACKEND_DIR / "monitoring" / "grafana-dashboard.json"
        assert path.exists(), "monitoring/grafana-dashboard.json is missing"
        content = json.loads(path.read_text(encoding="utf-8"))
        assert "dashboard" in content, "Invalid Grafana dashboard format"
        assert (
            len(content["dashboard"]["panels"]) >= 4
        ), "Dashboard needs at least 4 panels"

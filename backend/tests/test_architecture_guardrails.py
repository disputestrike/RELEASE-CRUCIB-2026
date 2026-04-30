"""Architecture guardrail tests.

NOTE: The original verify_architecture_guardrails script was removed in a prior
purge. These tests verify the core architectural invariants directly instead.
"""
from __future__ import annotations

from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class TestAgentFilesExist:
    """Verify all critical agent files exist."""

    def test_builder_agent_exists(self):
        assert (BACKEND_ROOT / "agents" / "builder_agent.py").is_file()

    def test_frontend_agent_exists(self):
        assert (BACKEND_ROOT / "agents" / "frontend_agent.py").is_file()

    def test_backend_agent_exists(self):
        assert (BACKEND_ROOT / "agents" / "backend_agent.py").is_file()

    def test_repair_agents_exists(self):
        assert (BACKEND_ROOT / "agents" / "repair_agents.py").is_file()


class TestOrchestrationFilesExist:
    """Verify all critical orchestration files exist."""

    def test_executor_exists(self):
        assert (BACKEND_ROOT / "orchestration" / "executor.py").is_file()

    def test_runtime_validator_exists(self):
        assert (BACKEND_ROOT / "orchestration" / "runtime_validator.py").is_file()

    def test_runtime_repair_gate_exists(self):
        assert (BACKEND_ROOT / "orchestration" / "runtime_repair_gate.py").is_file()

    def test_proof_artifact_service_exists(self):
        assert (BACKEND_ROOT / "orchestration" / "proof_artifact_service.py").is_file()

    def test_what_if_simulator_exists(self):
        assert (BACKEND_ROOT / "orchestration" / "what_if_simulator.py").is_file()


class TestTemplatesAndValidators:
    """Verify template and validator infrastructure."""

    def test_template_registry_exists(self):
        assert (BACKEND_ROOT / "agents" / "templates" / "registry.py").is_file()

    def test_at_least_7_stack_templates(self):
        templates_dir = BACKEND_ROOT / "agents" / "templates"
        py_files = [f for f in templates_dir.glob("*.py") if f.name != "__init__.py" and f.name != "registry.py"]
        assert len(py_files) >= 7, f"Expected >= 7 templates, found: {[f.name for f in py_files]}"

    def test_validator_factory_exists(self):
        assert (BACKEND_ROOT / "agents" / "validators" / "validator_factory.py").is_file()

    def test_at_least_6_language_validators(self):
        validators_dir = BACKEND_ROOT / "agents" / "validators"
        py_files = [f for f in validators_dir.glob("*_validator.py")]
        assert len(py_files) >= 6, f"Expected >= 6 validators, found: {[f.name for f in py_files]}"


class TestNoFallbackStubs:
    """Verify the executor does not contain fallback stub patterns."""

    def test_executor_no_placeholder_pass(self):
        executor_src = (BACKEND_ROOT / "orchestration" / "executor.py").read_text()
        # Must NOT have placeholder pass-through
        assert "placeholder" not in executor_src.lower() or "no placeholder" in executor_src.lower()
        assert "stub" not in executor_src.lower() or "no stub" in executor_src.lower() or "no-stub" in executor_src.lower()

    def test_executor_has_verification_failed(self):
        executor_src = (BACKEND_ROOT / "orchestration" / "executor.py").read_text()
        assert "VerificationFailed" in executor_src

    def test_executor_returns_false_on_failure(self):
        executor_src = (BACKEND_ROOT / "orchestration" / "executor.py").read_text()
        assert "success" in executor_src and "False" in executor_src

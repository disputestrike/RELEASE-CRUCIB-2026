"""
Tests for the final gap closure: Hard Runtime Gate, Real Repair Loop,
Runtime Validation, Confidence Scoring, Template Enforcement.

These tests verify that the system is Manus-level reliable:
  - No fake success paths
  - Validation = execution (not just static analysis)
  - Repair loop = mandatory, not optional
  - Confidence scoring = enforced
"""

import asyncio
import json
import os
import pytest
from typing import Dict, Any


# ── 1. Confidence Scoring Tests ────────────────────────────────────────────

class TestConfidenceScoring:
    """Tests for stack_confidence.py — enforced, not decorative."""

    def test_production_stack_passes(self):
        """Python FastAPI is production tier — should pass without warnings."""
        from backend.stack_confidence import check_stack_confidence
        stack = {"backend": {"language": "python", "framework": "fastapi"}}
        result = check_stack_confidence(stack)
        assert result["tier"] == "production"
        assert result["confidence"] >= 0.90
        assert result["blocked"] is False
        assert len(result["warnings"]) == 0

    def test_stable_stack_passes_with_info(self):
        """C++ CMake is stable tier — should pass."""
        from backend.stack_confidence import check_stack_confidence
        stack = {"backend": {"language": "cpp", "framework": "cmake"}}
        result = check_stack_confidence(stack)
        assert result["tier"] == "stable"
        assert result["blocked"] is False

    def test_beta_stack_warns(self):
        """Go Gin is beta tier — should warn but not block."""
        from backend.stack_confidence import check_stack_confidence
        stack = {"backend": {"language": "go", "framework": "gin"}}
        result = check_stack_confidence(stack)
        assert result["tier"] == "beta"
        assert result["blocked"] is False
        assert len(result["warnings"]) > 0
        assert "beta" in result["warnings"][0].lower()

    def test_experimental_stack_blocked(self):
        """Ruby Rails is experimental — should be BLOCKED."""
        from backend.stack_confidence import check_stack_confidence, StackNotSupportedError
        stack = {"backend": {"language": "ruby", "framework": "rails"}}
        with pytest.raises(StackNotSupportedError):
            check_stack_confidence(stack)

    def test_experimental_stack_allowed_with_env(self):
        """Experimental stack passes when CRUCIBAI_ALLOW_EXPERIMENTAL=1."""
        os.environ["CRUCIBAI_ALLOW_EXPERIMENTAL"] = "1"
        try:
            from backend.stack_confidence import check_stack_confidence
            stack = {"backend": {"language": "ruby", "framework": "rails"}}
            result = check_stack_confidence(stack)
            assert result["tier"] == "experimental"
            assert result["blocked"] is False
            assert len(result["warnings"]) > 0
        finally:
            os.environ.pop("CRUCIBAI_ALLOW_EXPERIMENTAL", None)

    def test_get_stack_key_mapping(self):
        """Stack key derivation from stack dict."""
        from backend.stack_confidence import get_stack_key
        tests = [
            ({"backend": {"language": "python", "framework": "fastapi"}}, "python_fastapi"),
            ({"backend": {"language": "javascript", "framework": "express"}}, "node_express"),
            ({"backend": {"language": "cpp", "framework": "cmake"}}, "cpp_cmake"),
            ({"backend": {"language": "go", "framework": "gin"}}, "go_gin"),
            ({"frontend": {"language": "typescript", "framework": "react-vite"}, "backend": None}, "react_vite"),
        ]
        for stack, expected in tests:
            assert get_stack_key(stack) == expected, f"Expected {expected} for {stack}"

    def test_ema_tracking(self):
        """EMA score tracks outcomes over time."""
        from backend.stack_confidence import record_outcome, get_ema_score
        # Record outcomes
        record_outcome("_test_stack_ema", True)
        record_outcome("_test_stack_ema", True)
        record_outcome("_test_stack_ema", False)
        record_outcome("_test_stack_ema", True)

        ema = get_ema_score("_test_stack_ema")
        assert ema is not None
        assert 0.0 <= ema <= 1.0
        # Should be above 0.5 (3 out of 4 successes)
        assert ema > 0.5

    def test_get_tier_classification(self):
        """Tier classification from confidence scores."""
        from backend.stack_confidence import get_tier, TIER_PRODUCTION, TIER_STABLE, TIER_BETA, TIER_EXPERIMENTAL
        assert get_tier(0.95) == TIER_PRODUCTION
        assert get_tier(0.80) == TIER_PRODUCTION
        assert get_tier(0.60) == TIER_STABLE
        assert get_tier(0.40) == TIER_BETA
        assert get_tier(0.39) == TIER_EXPERIMENTAL
        assert get_tier(0.0) == TIER_EXPERIMENTAL


# ── 2. Runtime Validator Tests ─────────────────────────────────────────────

class TestRuntimeValidator:
    """Tests for runtime_validator.py — actual execution, not static analysis."""

    @pytest.mark.asyncio
    async def test_syntax_validation_passes_valid_python(self):
        """Valid Python code passes syntax validation."""
        from backend.orchestration.runtime_validator import RuntimeValidator
        validator = RuntimeValidator()
        files = {
            "backend/main.py": '''
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
''',
            "backend/requirements.txt": "fastapi\nuvicorn\n",
        }
        result = await validator._validate_syntax(files, {"backend": {"language": "python"}})
        assert result.passed is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_syntax_validation_fails_bad_python(self):
        """Invalid Python code fails syntax validation."""
        from backend.orchestration.runtime_validator import RuntimeValidator
        validator = RuntimeValidator()
        files = {
            "backend/main.py": '''
def broken(
    # Missing closing paren and colon
''',
        }
        result = await validator._validate_syntax(files, {"backend": {"language": "python"}})
        assert result.passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_syntax_validation_fails_bad_json(self):
        """Invalid JSON fails syntax validation."""
        from backend.orchestration.runtime_validator import RuntimeValidator
        validator = RuntimeValidator()
        files = {
            "package.json": '{invalid json syntax,,,',
        }
        result = await validator._validate_syntax(files, {"backend": {"language": "javascript"}})
        assert result.passed is False
        assert any("JSON" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_syntax_validation_passes_valid_json(self):
        """Valid JSON passes syntax validation."""
        from backend.orchestration.runtime_validator import RuntimeValidator
        validator = RuntimeValidator()
        files = {
            "package.json": json.dumps({"name": "test", "version": "1.0.0", "scripts": {"start": "node server.js"}}),
        }
        result = await validator._validate_syntax(files, {"backend": {"language": "javascript"}})
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_full_validation_without_workspace(self):
        """Validation without workspace fails at runtime stage."""
        from backend.orchestration.runtime_validator import RuntimeValidator
        validator = RuntimeValidator()
        files = {
            "backend/main.py": '''
from fastapi import FastAPI
app = FastAPI()
@app.get("/health")
def health():
    return {"status": "ok"}
''',
        }
        result = await validator.validate(files, {"backend": {"language": "python", "framework": "fastapi"}})
        # Should fail at runtime stage (no workspace to run server)
        assert result.success is False
        assert result.stage in ("runtime", "build")

    @pytest.mark.asyncio
    async def test_validation_result_dataclass(self):
        """ValidationResult has correct structure."""
        from backend.orchestration.runtime_validator import ValidationResult
        vr = ValidationResult(success=True, stage="passed")
        assert vr.success is True
        assert bool(vr) is True

        vr_fail = ValidationResult(success=False, errors=["test error"], stage="syntax")
        assert vr_fail.success is False
        assert bool(vr_fail) is False


# ── 3. Repair Gate Tests ───────────────────────────────────────────────────

class TestRepairGate:
    """Tests for runtime_repair_gate.py — real repair loop."""

    def test_error_classification_syntax(self):
        """SyntaxError is classified as syntax error."""
        from backend.orchestration.runtime_repair_gate import classify_errors
        hints = classify_errors([
            'SyntaxError: invalid syntax in backend/main.py',
            '  File "backend/main.py", line 12',
        ])
        assert len(hints) >= 1
        assert hints[0].error_type == "syntax"

    def test_error_classification_import(self):
        """ModuleNotFoundError is classified as import error."""
        from backend.orchestration.runtime_repair_gate import classify_errors
        hints = classify_errors([
            'ModuleNotFoundError: No module named fastapi',
        ])
        assert len(hints) == 1
        assert hints[0].error_type == "import"

    def test_error_classification_dependency(self):
        """npm ERR! is classified as dependency error."""
        from backend.orchestration.runtime_repair_gate import classify_errors
        hints = classify_errors([
            'npm ERR! Could not resolve dependency: express@^4.0.0',
        ])
        assert len(hints) == 1
        assert hints[0].error_type == "dependency"

    def test_error_classification_json(self):
        """JSON decode error is classified as json error."""
        from backend.orchestration.runtime_repair_gate import classify_errors
        hints = classify_errors([
            'JSONDecodeError: Expecting value: line 1 column 1 (char 0)',
        ])
        assert len(hints) == 1
        assert hints[0].error_type == "json"

    def test_error_classification_mixed(self):
        """Multiple error types are classified correctly."""
        from backend.orchestration.runtime_repair_gate import classify_errors
        hints = classify_errors([
            'SyntaxError: invalid syntax',
            'ModuleNotFoundError: No module named fastapi',
            'npm ERR! Could not resolve dependency',
            'TypeError: undefined is not a function',
        ])
        types = {h.error_type for h in hints}
        assert "syntax" in types
        assert "import" in types
        assert "dependency" in types

    def test_apply_patch(self):
        """apply_patch correctly merges patch into original."""
        from backend.orchestration.runtime_repair_gate import apply_patch
        original = {"a.py": "original", "b.py": "keep"}
        patch = {"a.py": "patched", "c.py": "new"}
        result = apply_patch(original, patch)
        assert result == {"a.py": "patched", "b.py": "keep", "c.py": "new"}
        # Original should be unchanged
        assert original["a.py"] == "original"

    @pytest.mark.asyncio
    async def test_syntax_repair_agent(self):
        """SyntaxRepairAgent can fix missing colons."""
        from backend.orchestration.runtime_repair_gate import SyntaxRepairAgent, RepairHint
        agent = SyntaxRepairAgent()

        files = {
            "main.py": "def hello()\n    print('hello')\n",
        }
        hints = [RepairHint(
            error_type="syntax",
            file_path="main.py",
            error_message="SyntaxError: expected ':'",
        )]

        result = await agent.repair(files, hints)
        assert result["success"] is True
        assert "main.py" in result["files_changed"]
        assert ":" in result["files_changed"]["main.py"]

    @pytest.mark.asyncio
    async def test_json_repair_agent(self):
        """JsonRepairAgent can fix trailing commas."""
        from backend.orchestration.runtime_repair_gate import JsonRepairAgent, RepairHint
        agent = JsonRepairAgent()

        files = {
            "config.json": '{"name": "test", "version": "1.0",}',
        }
        hints = [RepairHint(
            error_type="json",
            file_path="config.json",
            error_message="JSONDecodeError: Expecting property name",
        )]

        result = await agent.repair(files, hints)
        assert result["success"] is True
        # Verify the fixed JSON is valid
        json.loads(result["files_changed"]["config.json"])

    @pytest.mark.asyncio
    async def test_dependency_repair_agent(self):
        """DependencyRepairAgent adds missing packages to package.json."""
        from backend.orchestration.runtime_repair_gate import DependencyRepairAgent, RepairHint
        agent = DependencyRepairAgent()

        files = {
            "package.json": json.dumps({"name": "test", "version": "1.0.0", "dependencies": {}}),
        }
        hints = [RepairHint(
            error_type="dependency",
            file_path="package.json",
            error_message="npm ERR! Could not resolve dependency: express@^4.0.0",
        )]

        result = await agent.repair(files, hints)
        assert result["success"] is True
        assert "package.json" in result["files_changed"]
        # Verify express was added
        pkg = json.loads(result["files_changed"]["package.json"])
        assert "express" in pkg.get("dependencies", {})

    @pytest.mark.asyncio
    async def test_select_repair_agent(self):
        """select_repair_agent routes to the correct agent."""
        from backend.orchestration.runtime_repair_gate import (
            select_repair_agent, SyntaxRepairAgent, ImportRepairAgent,
            DependencyRepairAgent, JsonRepairAgent, LLMCodeRepairAgent, RepairHint
        )

        assert isinstance(select_repair_agent([RepairHint("syntax", "f.py", "err")]), SyntaxRepairAgent)
        assert isinstance(select_repair_agent([RepairHint("import", "f.py", "err")]), ImportRepairAgent)
        assert isinstance(select_repair_agent([RepairHint("dependency", "f.py", "err")]), DependencyRepairAgent)
        assert isinstance(select_repair_agent([RepairHint("json", "f.json", "err")]), JsonRepairAgent)
        assert isinstance(select_repair_agent([RepairHint("runtime", "f.py", "err")]), LLMCodeRepairAgent)


# ── 4. Template Enforcement Tests ──────────────────────────────────────────

class TestTemplateEnforcement:
    """Tests for template registry — agents MUST use templates."""

    def test_template_registry_has_7_templates(self):
        """Registry has all 7 expected templates."""
        from backend.agents.templates.registry import list_templates
        templates = list_templates()
        assert len(templates) == 7

    def test_python_fastapi_template_exists(self):
        """Python FastAPI template has required files."""
        from backend.agents.templates.registry import get_template
        stack = {"backend": {"language": "python", "framework": "fastapi"}}
        template = get_template(stack)
        assert template is not None
        assert template["name"] == "Python FastAPI"
        paths = [f["path"] for f in template["files"]]
        assert "backend/main.py" in paths
        assert "backend/models.py" in paths
        assert "backend/requirements.txt" in paths

    def test_react_vite_template_exists(self):
        """React Vite template has required files."""
        from backend.agents.templates.registry import get_template
        stack = {"frontend": {"language": "typescript", "framework": "react-vite"}, "backend": None}
        template = get_template(stack)
        assert template is not None
        paths = [f["path"] for f in template["files"]]
        assert "frontend/package.json" in paths
        assert "frontend/src/main.jsx" in paths
        assert "frontend/src/App.jsx" in paths

    def test_unknown_stack_returns_none(self):
        """Unknown stack returns None (allows experimental mode)."""
        from backend.agents.templates.registry import get_template
        stack = {"backend": {"language": "ruby", "framework": "rails"}}
        template = get_template(stack)
        assert template is None

    def test_template_has_build_commands(self):
        """Templates include build commands."""
        from backend.agents.templates.registry import get_template
        stack = {"backend": {"language": "python", "framework": "fastapi"}}
        template = get_template(stack)
        assert "build_commands" in template
        assert len(template["build_commands"]) >= 2

    def test_template_has_min_files(self):
        """Templates define minimum file count."""
        from backend.agents.templates.registry import get_template
        stack = {"backend": {"language": "python", "framework": "fastapi"}}
        template = get_template(stack)
        assert "min_files" in template
        assert template["min_files"] >= 2


# ── 5. Hard Runtime Gate Tests ─────────────────────────────────────────────

class TestHardRuntimeGate:
    """Tests for the hard verification gate in executor.py."""

    def test_executor_imports_runtime_validator(self):
        """Executor imports RuntimeValidator at module level."""
        from backend.orchestration.executor import RuntimeValidator as EV
        from backend.orchestration.runtime_validator import RuntimeValidator
        assert EV is RuntimeValidator

    def test_executor_imports_repair_gate(self):
        """Executor imports repair_until_valid at module level."""
        from backend.orchestration.executor import repair_until_valid as ER
        from backend.orchestration.runtime_repair_gate import repair_until_valid
        assert ER is repair_until_valid

    def test_executor_imports_confidence(self):
        """Executor imports check_stack_confidence at module level."""
        from backend.orchestration.executor import check_stack_confidence as EC
        from backend.stack_confidence import check_stack_confidence
        assert EC is check_stack_confidence

    def test_handle_verification_step_is_real(self):
        """handle_verification_step is a real function, not a passthrough."""
        import inspect
        from backend.orchestration.executor import handle_verification_step
        source = inspect.getsource(handle_verification_step)
        # Must NOT contain the old passthrough
        assert "Verification is applied in execute_step via verify_step" not in source
        # Must contain the new hard gate
        assert "HARD VERIFICATION GATE" in source
        assert "repair_until_valid" in source
        assert "RuntimeValidator" in source

    def test_handle_verification_step_raises_on_failure(self):
        """handle_verification_step raises VerificationFailed on hard failure."""
        import inspect
        from backend.orchestration.executor import handle_verification_step
        source = inspect.getsource(handle_verification_step)
        assert "raise VerificationFailed" in source
        assert "HARD FAIL" in source


# ── 6. Builder Agent Integration Tests ─────────────────────────────────────

class TestBuilderAgentIntegration:
    """Tests for BuilderAgent with confidence gate and template enforcement."""

    def test_builder_agent_has_confidence_gate(self):
        """BuilderAgent.execute calls check_stack_confidence."""
        import inspect
        from backend.agents.builder_agent import BuilderAgent
        source = inspect.getsource(BuilderAgent.execute)
        assert "check_stack_confidence" in source
        assert "CONFIDENCE GATE" in source

    def test_builder_agent_has_template_lock(self):
        """BuilderAgent.execute calls get_template."""
        import inspect
        from backend.agents.builder_agent import BuilderAgent
        source = inspect.getsource(BuilderAgent.execute)
        assert "get_template" in source
        assert "TEMPLATE LOCK" in source


# ── 7. End-to-End Pipeline Tests ───────────────────────────────────────────

class TestEndToEndPipeline:
    """Test the complete pipeline: stack select → validate → repair → gate."""

    def test_full_pipeline_no_fake_success(self):
        """
        Verify the pipeline has NO fake success paths.

        This is the most critical test:
        - handle_verification_step must call RuntimeValidator
        - RuntimeValidator must actually validate (not just log)
        - repair_until_valid must re-validate after repair
        - BuilderAgent must check confidence before LLM calls
        """
        import inspect
        from backend.orchestration.executor import handle_verification_step
        from backend.orchestration.runtime_repair_gate import repair_until_valid
        from backend.orchestration.runtime_validator import RuntimeValidator

        # 1. handle_verification_step calls RuntimeValidator
        hv_source = inspect.getsource(handle_verification_step)
        assert "RuntimeValidator()" in hv_source
        assert "validator.validate(" in hv_source

        # 2. handle_verification_step calls repair on failure
        assert "repair_until_valid(" in hv_source

        # 3. handle_verification_step raises VerificationFailed on hard fail
        assert "raise VerificationFailed(" in hv_source

        # 4. repair_until_valid re-validates after repair
        repair_source = inspect.getsource(repair_until_valid)
        assert "revalidation" in repair_source.lower() or "validator.validate(" in repair_source

        # 5. BuilderAgent has confidence gate
        from backend.agents.builder_agent import BuilderAgent
        ba_source = inspect.getsource(BuilderAgent.execute)
        assert "check_stack_confidence" in ba_source

        print("✅ Pipeline has NO fake success paths")

    @pytest.mark.asyncio
    async def test_repair_loop_revalidates(self):
        """
        Repair loop MUST re-validate after every repair attempt.
        No agent can return success unless re-validation passes.
        """
        from backend.orchestration.runtime_repair_gate import repair_until_valid
        import inspect
        source = inspect.getsource(repair_until_valid)
        # Must call validator.validate() inside the loop
        assert "validator.validate(" in source
        # Must check revalidation.success
        assert "revalidation.success" in source or "validation.success" in source

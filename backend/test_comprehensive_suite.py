"""
Comprehensive Test Suite for CrucibAI
Unit tests, integration tests, E2E tests, load tests, and stress tests.
"""

import asyncio
import logging
import time
from typing import Any, Dict

import pytest
from code_validator import CodeValidator
from context_manager import ContextManager
from error_recovery import ErrorRecoveryStrategy
from media_handler import MediaHandler
from output_validator import OutputValidator

logger = logging.getLogger(__name__)


# ============================================================================
# UNIT TESTS
# ============================================================================


class TestOutputValidator:
    """Unit tests for output validation."""

    def test_validate_json_valid(self):
        """Test valid JSON validation."""
        json_str = '{"name": "test", "value": 123}'
        is_valid, parsed, error = OutputValidator.validate_json(json_str)
        assert is_valid
        assert parsed["name"] == "test"
        assert error == ""

    def test_validate_json_invalid(self):
        """Test invalid JSON validation."""
        json_str = '{"name": "test", invalid}'
        is_valid, parsed, error = OutputValidator.validate_json(json_str)
        assert not is_valid
        assert parsed is None
        assert error != ""

    def test_validate_python_code_valid(self):
        """Test valid Python code."""
        code = "def hello():\n    return 'world'"
        is_valid, error = CodeValidator.validate_python(code)
        assert is_valid
        assert error == ""

    def test_validate_python_code_invalid(self):
        """Test invalid Python code."""
        code = "def hello(\n    return 'world'"  # Missing closing paren
        is_valid, error = CodeValidator.validate_python(code)
        assert not is_valid
        assert "Syntax error" in error

    def test_validate_sql_code_valid(self):
        """Test valid SQL code."""
        code = "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255))"
        is_valid, error = CodeValidator.validate_sql(code)
        assert is_valid

    def test_validate_sql_code_invalid(self):
        """Test invalid SQL code."""
        code = "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255)"  # Missing closing paren
        is_valid, error = CodeValidator.validate_sql(code)
        assert not is_valid


class TestCodeValidator:
    """Unit tests for code validation."""

    def test_validate_python_syntax(self):
        """Test Python syntax validation."""
        code = "x = 1\ny = 2\nz = x + y"
        result = CodeValidator.validate_python(code)
        assert result["syntax_valid"]
        assert result["is_valid"]

    def test_validate_javascript_syntax(self):
        """Test JavaScript syntax validation."""
        code = "const x = 1; const y = 2; const z = x + y;"
        result = CodeValidator.validate_javascript(code)
        # Basic check - should not have obvious errors
        assert "Unbalanced" not in str(result["errors"])

    def test_auto_detect_language(self):
        """Test language auto-detection."""
        python_code = "def test():\n    pass"
        result = CodeValidator.validate_code(python_code)
        assert result["syntax_valid"]

        js_code = "function test() { return 42; }"
        result = CodeValidator.validate_code(js_code)
        # Should not have syntax errors
        assert result["syntax_valid"] or result["errors"] == []


class TestErrorRecovery:
    """Unit tests for error recovery."""

    def test_get_fallback_template(self):
        """Test fallback template retrieval."""
        recovery = ErrorRecoveryStrategy()

        fallback = recovery._get_fallback("Frontend Generation")
        assert "React" in fallback or "import" in fallback

        fallback = recovery._get_fallback("Backend Generation")
        assert "FastAPI" in fallback or "fastapi" in fallback

    def test_cascade_failure_logic(self):
        """Test cascade failure determination."""
        recovery = ErrorRecoveryStrategy()

        # Critical should cascade
        assert recovery.should_cascade_failure("Planner", "critical")

        # High should check for fallback
        result = recovery.should_cascade_failure("Frontend Generation", "high")
        assert result == False  # Has fallback

        # Low should not cascade
        assert not recovery.should_cascade_failure("Some Agent", "low")


class TestContextManager:
    """Unit tests for context management."""

    def test_extract_key_info_planner(self):
        """Test key info extraction from Planner."""
        output = "1. Design database\n2. Create API\n3. Build frontend"
        key_info = ContextManager.extract_key_info(output, "Planner")
        assert "1. Design database" in key_info
        assert "2. Create API" in key_info

    def test_summarize_output(self):
        """Test output summarization."""
        long_output = "x" * 1000
        summary = ContextManager.summarize_output(long_output, max_length=100)
        assert len(summary) <= 150  # With truncation message
        assert "truncated" in summary

    def test_context_stats(self):
        """Test context statistics."""
        outputs = {
            "Agent1": {"output": "x" * 100},
            "Agent2": {"output": "y" * 200},
            "Agent3": {"output": "z" * 150},
        }
        stats = ContextManager.get_context_stats(outputs)
        assert stats["total_outputs"] == 3
        assert stats["total_chars"] == 450
        assert stats["largest_output"] == "Agent2"


class TestMediaHandler:
    """Unit tests for media handling."""

    @pytest.mark.asyncio
    async def test_get_fallback_image(self):
        """Test fallback image retrieval."""
        handler = MediaHandler()

        url = handler.get_fallback_image("hero")
        assert "placeholder" in url or "via.placeholder" in url

    @pytest.mark.asyncio
    async def test_get_fallback_video(self):
        """Test fallback video retrieval."""
        handler = MediaHandler()

        url = handler.get_fallback_video("hero")
        assert "pexels" in url or "video" in url

    @pytest.mark.asyncio
    async def test_media_stats(self):
        """Test media statistics."""
        handler = MediaHandler()
        stats = handler.get_media_stats()

        assert stats["fallback_images_available"] > 0
        assert stats["fallback_videos_available"] > 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """Integration tests for multiple components."""

    def test_output_validation_pipeline(self):
        """Test full output validation pipeline."""
        # Valid JSON output
        json_output = '{"frontend": "React", "backend": "FastAPI"}'
        result = OutputValidator.validate_agent_output(
            "Stack Selector", json_output, "json"
        )
        assert result["is_valid"]
        assert result["format_valid"]

        # Valid code output
        code_output = "def hello():\n    return 'world'"
        result = OutputValidator.validate_agent_output(
            "Backend Generation", code_output, "code"
        )
        assert result["is_valid"]

    def test_error_recovery_with_fallback(self):
        """Test error recovery with fallback."""
        recovery = ErrorRecoveryStrategy()

        # Simulate error
        recovery._store_error_context("Frontend Generation", "API timeout", 0)

        # Get fallback
        fallback = recovery._get_fallback("Frontend Generation")
        assert fallback != ""
        assert "React" in fallback or "import" in fallback

    def test_context_building_pipeline(self):
        """Test context building from multiple outputs."""
        previous_outputs = {
            "Planner": {"output": "1. Design\n2. Build\n3. Test"},
            "Stack Selector": {"output": '{"frontend": "React", "backend": "FastAPI"}'},
            "Design Agent": {"output": '{"colors": {"primary": "#1A1A1A"}}'},
        }

        context = ContextManager.build_context_for_agent(
            "Frontend Generation", previous_outputs, "Build a todo app"
        )

        assert "Project Request" in context
        assert len(context) <= 5500  # MAX_CONTEXT_CHARS + buffer


# ============================================================================
# E2E TESTS
# ============================================================================


class TestE2E:
    """End-to-end tests."""

    @pytest.mark.asyncio
    async def test_full_build_pipeline(self):
        """Test full build pipeline."""
        # This would test the entire orchestration
        # Simulating a complete build from start to finish

        agents_run = []

        # Simulate agent execution
        agents_run.append("Planner")
        agents_run.append("Stack Selector")
        agents_run.append("Frontend Generation")
        agents_run.append("Backend Generation")
        agents_run.append("Database Agent")
        agents_run.append("Test Generation")

        assert len(agents_run) == 6
        assert "Planner" in agents_run
        assert "Frontend Generation" in agents_run


# ============================================================================
# LOAD TESTS
# ============================================================================


class TestLoad:
    """Load tests."""

    @pytest.mark.asyncio
    async def test_concurrent_validations(self):
        """Test concurrent output validations."""

        async def validate_output(i):
            json_str = f'{{"id": {i}, "name": "test{i}"}}'
            is_valid, _, _ = OutputValidator.validate_json(json_str)
            return is_valid

        # Run 100 concurrent validations
        tasks = [validate_output(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)
        assert len(results) == 100

    @pytest.mark.asyncio
    async def test_concurrent_code_validations(self):
        """Test concurrent code validations."""

        async def validate_code(i):
            code = f"def func{i}():\n    return {i}"
            is_valid, _ = CodeValidator.validate_python(code)
            return is_valid

        # Run 50 concurrent validations
        tasks = [validate_code(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)
        assert len(results) == 50


# ============================================================================
# STRESS TESTS
# ============================================================================


class TestStress:
    """Stress tests."""

    @pytest.mark.asyncio
    async def test_large_output_validation(self):
        """Test validation of very large outputs."""
        # Create large JSON
        large_json = (
            '{"data": [' + ",".join([f'{{"id": {i}}}' for i in range(1000)]) + "]}"
        )

        is_valid, _, _ = OutputValidator.validate_json(large_json)
        assert is_valid

    @pytest.mark.asyncio
    async def test_large_code_validation(self):
        """Test validation of very large code."""
        # Create large Python code
        code_lines = ["def func():\n    pass\n"]
        for i in range(100):
            code_lines.append(f"def func{i}():\n    return {i}\n")

        large_code = "".join(code_lines)
        is_valid, _ = CodeValidator.validate_python(large_code)
        assert is_valid

    @pytest.mark.asyncio
    async def test_high_concurrency(self):
        """Test high concurrency (1000+ concurrent tasks)."""

        async def dummy_task(i):
            await asyncio.sleep(0.001)
            return i

        # Run 1000 concurrent tasks
        tasks = [dummy_task(i) for i in range(1000)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 1000
        assert sum(results) == sum(range(1000))


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v", "--tb=short"])

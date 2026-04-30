"""Tests for the repair_loop orchestration module."""
import pytest

from backend.orchestration.repair_loop import (
    RepairLoop,
    RepairResult,
    RepairAgentInterface,
    SyntaxRepairAgent,
)


class TestRepairResult:
    """Test RepairResult dataclass."""

    def test_repair_result_defaults(self):
        result = RepairResult(
            success=False,
            contract_item_id="required_files:main.py",
            repair_agents_executed=[],
            files_modified=[],
        )
        assert result.success is False
        assert result.error is None
        assert result.requires_human is False

    def test_repair_result_with_error(self):
        result = RepairResult(
            success=False,
            contract_item_id="required_files:main.py",
            repair_agents_executed=["syntax"],
            files_modified=[],
            error="Could not fix syntax",
            requires_human=True,
        )
        assert result.requires_human is True
        assert len(result.repair_agents_executed) == 1


class TestRepairLoop:
    """Test RepairLoop orchestrator."""

    def test_repair_loop_init(self):
        loop = RepairLoop(
            agent_pool={"syntax": SyntaxRepairAgent()},
            workspace_path="/tmp/test_workspace",
        )
        assert loop.workspace_path == "/tmp/test_workspace"
        assert "syntax" in loop.agent_pool

    def test_repair_loop_has_circuit_breaker(self):
        loop = RepairLoop(
            agent_pool={},
            workspace_path="/tmp/test_workspace",
        )
        assert loop.circuit_breaker is not None
        assert loop.error_parser is not None


class TestRepairAgentInterface:
    """Test that repair agents implement the interface."""

    @pytest.mark.asyncio
    async def test_syntax_repair_agent_returns_success(self):
        import tempfile, os
        agent = SyntaxRepairAgent()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with a missing colon (fixable by SyntaxRepairAgent)
            test_file = os.path.join(tmpdir, "main.py")
            with open(test_file, "w") as f:
                f.write("def hello()\n    print('hello')\n")
            result = await agent.repair(
                contract_item_id="required_files:main.py",
                contract=None,
                workspace_path=tmpdir,
                error_context={},
                priority="high",
            )
            assert result["success"] is True
            assert "main.py" in result["files_modified"]

    @pytest.mark.asyncio
    async def test_base_interface_raises_not_implemented(self):
        agent = RepairAgentInterface()
        with pytest.raises(NotImplementedError):
            await agent.repair("", None, "", {}, "")

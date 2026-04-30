#!/usr/bin/env python
"""
PHASE 3 FINAL RUNTIME VERIFICATION

Runtime proof that:
1. ExportGate blocks before repair (allowed=False)
2. ExportGate allows after repair (allowed=True)
3. Contract progress structure is correct (done/missing, not todo)
4. KeyError 'todo' does not occur
"""

import asyncio
import tempfile
import os
from datetime import datetime

from orchestration.build_contract import BuildContract
from orchestration.export_gate import ExportGate, ExportDecision
from orchestration.final_assembly_agent import DiskManifest
from orchestration.repair_loop import RepairLoop, RepairAgentInterface
from orchestration.error_as_data_parser import ErrorAsDataParser, StructuredError, ErrorType, RepairRouter
from orchestration.circuit_breaker import CircuitBreaker


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class MockRepairAgent(RepairAgentInterface):
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        route = contract_item_id.split(":")[1]
        contract.update_progress("required_routes", route, done=True)
        return {"success": True, "files_modified": ["analytics.tsx"]}


def test_export_gate_flip():
    """
    CRITICAL: ExportGate MUST flip from False -> True after repair.
    """
    print("\n" + "=" * 60)
    print("TEST: ExportGate False -> True After Repair")
    print("=" * 60)

    contract = BuildContract(
        build_id="flip-test",
        build_class="saas",
        product_name="Test",
        original_goal="Test",
        required_routes=["/analytics"],
        stack={"frontend": "React+TypeScript"}
    )

    manifest = {
        "build_id": "flip-test",
        "contract_version": 1,
        "generated_at": datetime.utcnow().isoformat(),
        "entries": [],
        "total_files": 0,
        "total_bytes": 0,
        "build_target": "saas"
    }

    gate = ExportGate(db_session=None)

    # BEFORE repair - should be BLOCKED
    proof_items = [{"type": "goal_satisfied", "verified": True}]
    d1 = run_async(gate.check_export(
        "flip-test", contract, manifest, proof_items, [], 85
    ))

    print(f"  BEFORE: allowed = {d1.allowed}")
    assert d1.allowed == False, f"Should be blocked, got: {d1.failed_checks}"

    # REPAIR
    contract.update_progress("required_routes", "/analytics", done=True)
    print(f"  REPAIR: /analytics marked done")
    print(f"  CONTRACT SATISFIED: {contract.is_satisfied()}")

    # AFTER repair - should be ALLOWED
    d2 = run_async(gate.check_export(
        "flip-test", contract, manifest, proof_items, [], 85
    ))

    print(f"  AFTER: allowed = {d2.allowed}")
    if not d2.allowed:
        print(f"  FAILED CHECKS: {d2.failed_checks}")

    assert d2.allowed == True, f"Should allow, failed: {d2.failed_checks}"

    # THE FLIP
    print(f"\n  *** EXPORT FLIP: {d1.allowed} -> {d2.allowed} ***")
    assert d1.allowed == False and d2.allowed == True

    print("  PASS: ExportGate flips correctly")


def test_contract_progress_no_todo():
    """
    CRITICAL: Contract progress uses done/missing, NEVER todo.
    """
    print("\n" + "=" * 60)
    print("TEST: Contract Progress Structure (no 'todo' key)")
    print("=" * 60)

    contract = BuildContract(
        build_id="structure-test",
        build_class="saas",
        product_name="Test",
        original_goal="Test",
        required_routes=["/", "/analytics"]
    )

    progress = contract.contract_progress["required_routes"]

    print(f"  Progress keys: {list(progress.keys())}")

    # Verify correct structure
    assert "done" in progress, "Must have 'done'"
    assert "missing" in progress, "Must have 'missing'"
    assert "percent" in progress, "Must have 'percent'"
    assert "todo" not in progress, "Must NOT have 'todo'"

    print("  PASS: Structure correct (done/missing/percent, no todo)")

    # Test updates
    contract.update_progress("required_routes", "/", done=True)
    assert "/" in progress["done"]
    print("  PASS: update_progress works correctly")


def test_helios_scenario():
    """
    Helios: missing /analytics -> repair -> export allowed.
    """
    print("\n" + "=" * 60)
    print("TEST: Helios Scenario (/analytics repair)")
    print("=" * 60)

    workspace = tempfile.mkdtemp()

    contract = BuildContract(
        build_id="helios",
        build_class="regulated_saas",
        product_name="Helios",
        original_goal="Build Helios",
        required_files=["main.tsx"],
        required_routes=["/", "/dashboard", "/crm", "/analytics"],
        stack={"frontend": "React+TypeScript", "backend": "FastAPI"}
    )

    # Mark all done except /analytics
    contract.update_progress("required_files", "main.tsx", done=True)
    contract.update_progress("required_routes", "/", done=True)
    contract.update_progress("required_routes", "/dashboard", done=True)
    contract.update_progress("required_routes", "/crm", done=True)

    print(f"  Initial missing: {contract.get_missing_items()}")
    print(f"  Initial satisfied: {contract.is_satisfied()}")

    assert not contract.is_satisfied()

    # Repair
    agent_pool = {"RoutingAgent": MockRepairAgent()}
    repair_loop = RepairLoop(agent_pool=agent_pool, workspace_path=workspace)

    error = Exception("Missing /analytics")
    context = {"contract_item_id": "required_routes:/analytics"}
    manifest = {"entries": [], "total_files": 0, "total_bytes": 0}

    result = run_async(repair_loop.handle_failure(
        "helios", contract, error, context, manifest
    ))

    print(f"  Repair succeeded: {result.get('repair_succeeded')}")
    assert result.get("repair_succeeded")

    print(f"  After missing: {contract.get_missing_items()}")
    print(f"  After satisfied: {contract.is_satisfied()}")

    assert contract.is_satisfied()
    print("  PASS: Helios scenario works")


def test_circuit_breaker():
    """
    Circuit breaker opens after 3 failures.
    """
    print("\n" + "=" * 60)
    print("TEST: Circuit Breaker (3 failures -> open)")
    print("=" * 60)

    cb = CircuitBreaker(max_failures=3)

    for i in range(3):
        cb.record_failure("item1", "error", "msg", f"Agent{i}")

    can_execute = cb.can_execute("item1")
    print(f"  After 3 failures: can_execute = {can_execute}")

    assert not can_execute, "Circuit should be open"
    print("  PASS: Circuit breaker trips correctly")


if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("# PHASE 3 FINAL RUNTIME VERIFICATION")
    print("#" * 60)

    test_export_gate_flip()
    test_contract_progress_no_todo()
    test_helios_scenario()
    test_circuit_breaker()

    print("\n" + "#" * 60)
    print("# ALL TESTS PASSED - PHASE 3 COMPLETE")
    print("#" * 60)

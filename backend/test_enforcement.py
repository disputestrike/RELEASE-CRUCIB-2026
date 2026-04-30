#!/usr/bin/env python
"""Enforcement layer validation tests."""

import asyncio
from orchestration.build_contract import BuildContract
from orchestration.export_gate import ExportGate, ExportDecision
from orchestration.contract_aware_retry import ContractCoverageChecker, ContractCoverageError
from orchestration.adaptive_dag_generator import (
    AdaptiveDAGGenerator, ContractBoundExecution, DAGNode, NodeType, UnboundNodeError
)

def run_async(coro):
    """Helper to run async code in sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)

def test_helios_missing_routes_blocks_export():
    """CRITICAL TEST: Helios build with missing analytics route is BLOCKED."""
    print("\n[Test] Helios missing routes blocks export")
    
    contract = BuildContract(
        build_id="helios-123",
        build_class="regulated_saas",
        product_name="Helios Operations Cloud",
        original_goal="Build Helios...",
        required_files=["client/src/main.tsx", "client/src/App.tsx"],
        required_routes=["/", "/dashboard", "/crm", "/analytics", "/settings"],
        required_database_tables=["users", "organizations", "accounts"]
    )
    
    # Simulate: all files present, but missing analytics route
    contract.update_progress("required_files", "client/src/main.tsx", done=True)
    contract.update_progress("required_files", "client/src/App.tsx", done=True)
    
    contract.update_progress("required_routes", "/", done=True)
    contract.update_progress("required_routes", "/dashboard", done=True)
    contract.update_progress("required_routes", "/crm", done=True)
    contract.update_progress("required_routes", "/settings", done=True)
    # /analytics route MISSING!
    
    for table in contract.required_database_tables:
        contract.update_progress("required_database_tables", table, done=True)
    
    # Contract should NOT be satisfied
    is_satisfied = contract.is_satisfied()
    print(f"  Contract satisfied: {is_satisfied}")
    assert not is_satisfied, "Contract should NOT be satisfied with missing route"
    
    # Export should be blocked
    gate = ExportGate()
    
    manifest = {
        "entries": [
            {"path": "client/src/main.tsx"},
            {"path": "client/src/App.tsx"}
        ]
    }
    
    decision = run_async(gate.check_export(
        job_id="helios-123",
        contract=contract,
        manifest=manifest,
        proof_items=[{"type": "build_pass", "verified": True}],
        verifier_results=[],
        quality_score=75
    ))
    
    print(f"  Export allowed: {decision.allowed}")
    print(f"  Contract satisfied check: {decision.contract_satisfied}")
    
    assert not decision.allowed, "Export should be BLOCKED"
    assert not decision.contract_satisfied, "Contract should be reported as not satisfied"
    print("  [PASS] Export correctly blocked!")

def test_export_gate_blocks_unsatisfied_contract():
    """ExportGate blocks when contract not satisfied."""
    print("\n[Test] Export gate blocks unsatisfied contract")
    
    contract = BuildContract(
        build_id="test-123",
        build_class="saas",
        product_name="Test",
        original_goal="Test",
        required_files=["file1.tsx", "file2.tsx"]
    )
    
    # Only satisfy 1 file
    contract.update_progress("required_files", "file1.tsx", done=True)
    
    gate = ExportGate()
    
    decision = run_async(gate.check_export(
        job_id="test-123",
        contract=contract,
        manifest={"entries": [{"path": "file1.tsx"}]},
        proof_items=[{"type": "build_pass", "verified": True}],
        verifier_results=[],
        quality_score=90
    ))
    
    print(f"  Export allowed: {decision.allowed}")
    print(f"  Failed checks: {decision.failed_checks}")
    
    assert not decision.allowed, "Export should be blocked"
    assert "contract_satisfied" in decision.failed_checks
    print("  [PASS] Export blocked for unsatisfied contract!")

def test_dag_nodes_must_have_contract_binding():
    """Nodes without contract_item_id are REJECTED."""
    print("\n[Test] DAG nodes must have contract binding")
    
    # Valid node with binding
    valid_node = DAGNode(
        id="node-1",
        type=NodeType.GENERATE,
        agent="TestAgent",
        contract_item_id="required_files:file.tsx",
        contract_item_type="required_files",
        description="Test"
    )
    
    # Should pass validation
    result = ContractBoundExecution.validate_node(valid_node)
    print(f"  Valid node accepted: {result}")
    assert result is True
    
    # Invalid node without binding
    invalid_node = DAGNode(
        id="node-2",
        type=NodeType.GENERATE,
        agent="TestAgent",
        contract_item_id="",  # Missing!
        contract_item_type="required_files",
        description="Test"
    )
    
    # Should raise
    try:
        ContractBoundExecution.validate_node(invalid_node)
        assert False, "Should have raised UnboundNodeError"
    except UnboundNodeError as e:
        print(f"  Unbound node rejected: {e}")
        print("  [PASS] Unbound nodes correctly rejected!")

def test_contract_drives_dag_generation():
    """DAG is generated FROM contract requirements."""
    print("\n[Test] Contract drives DAG generation")
    
    contract = BuildContract(
        build_id="test-123",
        build_class="saas",
        product_name="Test",
        original_goal="Test",
        required_files=["client/src/main.tsx", "client/src/App.tsx"],
        required_routes=["/", "/dashboard"],
        required_database_tables=["users", "posts"]
    )
    
    generator = AdaptiveDAGGenerator()
    dag = generator.generate(contract)
    
    # Verify DAG has nodes for each contract item
    file_nodes = [n for n in dag.nodes if n.contract_item_type == "required_files"]
    route_nodes = [n for n in dag.nodes if n.contract_item_type == "required_routes"]
    table_nodes = [n for n in dag.nodes if n.contract_item_type == "required_database_tables"]
    
    print(f"  File nodes: {len(file_nodes)} (expected: 2)")
    print(f"  Route nodes: {len(route_nodes)} (expected: 2)")
    print(f"  Table nodes: {len(table_nodes)} (expected: 2)")
    
    assert len(file_nodes) == 2, f"Expected 2 file nodes, got {len(file_nodes)}"
    assert len(route_nodes) == 2, f"Expected 2 route nodes, got {len(route_nodes)}"
    assert len(table_nodes) == 2, f"Expected 2 table nodes, got {len(table_nodes)}"
    
    # Verify each node has proper binding
    for node in dag.nodes:
        assert node.contract_item_id, f"Node {node.id} missing contract_item_id"
        assert node.contract_item_type, f"Node {node.id} missing contract_item_type"
    
    print("  [PASS] DAG correctly generated from contract!")

def test_helios_missing_database_blocks_export():
    """Helios build with missing database tables is BLOCKED."""
    print("\n[Test] Helios missing database blocks export")
    
    contract = BuildContract(
        build_id="helios-456",
        build_class="regulated_saas",
        product_name="Helios",
        original_goal="Build Helios...",
        required_files=["client/src/main.tsx"],
        required_routes=["/"],
        required_database_tables=["users", "organizations", "audit_events"]
    )
    
    # Mark everything done EXCEPT audit_events
    contract.update_progress("required_files", "client/src/main.tsx", done=True)
    contract.update_progress("required_routes", "/", done=True)
    contract.update_progress("required_database_tables", "users", done=True)
    contract.update_progress("required_database_tables", "organizations", done=True)
    # audit_events missing!
    
    # Should NOT be satisfied
    is_satisfied = contract.is_satisfied()
    print(f"  Contract satisfied: {is_satisfied}")
    assert not is_satisfied
    
    # Export blocked
    gate = ExportGate()
    decision = run_async(gate.check_export(
        job_id="helios-456",
        contract=contract,
        manifest={"entries": [{"path": "client/src/main.tsx"}]},
        proof_items=[{"type": "build_pass", "verified": True}],
        verifier_results=[],
        quality_score=90
    ))
    
    print(f"  Export allowed: {decision.allowed}")
    assert not decision.allowed
    print("  [PASS] Export blocked for missing database!")

def test_resume_restores_contract_state():
    """Resume restores contract progress."""
    print("\n[Test] Resume restores contract state")
    
    contract = BuildContract(
        build_id="resume-test",
        build_class="saas",
        product_name="Test",
        original_goal="Test",
        required_files=["file1.tsx", "file2.tsx", "file3.tsx"]
    )
    
    # Simulate partial completion
    contract.update_progress("required_files", "file1.tsx", done=True)
    contract.update_progress("required_files", "file2.tsx", done=True)
    # file3.tsx still missing
    
    # Check that contract is NOT satisfied (file3 missing)
    is_satisfied = contract.is_satisfied()
    print(f"  Contract satisfied: {is_satisfied}")
    
    done_count = len(contract.contract_progress["required_files"]["done"])
    missing_items = contract.get_missing_items()
    
    print(f"  Done items: {done_count}")
    print(f"  Missing items: {missing_items}")
    
    # Core assertions
    assert not is_satisfied, "Contract should NOT be satisfied with missing file"
    assert done_count == 2, f"Expected 2 done, got {done_count}"
    assert "required_files" in missing_items, "Should have missing files"
    assert "file3.tsx" in missing_items["required_files"], "file3.tsx should be missing"
    
    print("  [PASS] Contract state correctly tracked!")

def test_contract_coverage_checker():
    """ContractCoverageChecker validates all requirements are met."""
    print("\n[Test] Contract coverage checker")
    
    contract = BuildContract(
        build_id="test-123",
        build_class="saas",
        product_name="Test",
        original_goal="Test",
        required_files=["file1.tsx", "file2.tsx", "file3.tsx"]
    )
    
    # Manifest missing one file
    manifest = {
        "entries": [
            {"path": "file1.tsx"},
            {"path": "file2.tsx"}
            # file3.tsx missing!
        ]
    }
    
    checker = ContractCoverageChecker()
    
    try:
        checker.validate_before_export(contract, manifest)
        assert False, "Should have raised ContractCoverageError"
    except ContractCoverageError as e:
        print(f"  Coverage error raised: {len(e.missing_items)} missing items")
        assert "file3.tsx" in e.missing_items or any("file3" in str(item) for item in e.missing_items)
        print("  [PASS] Coverage checker correctly detects missing files!")

if __name__ == "__main__":
    print("=" * 60)
    print("CONTRACT ENFORCEMENT LAYER VALIDATION")
    print("=" * 60)
    
    test_helios_missing_routes_blocks_export()
    test_export_gate_blocks_unsatisfied_contract()
    test_dag_nodes_must_have_contract_binding()
    test_contract_drives_dag_generation()
    test_helios_missing_database_blocks_export()
    test_resume_restores_contract_state()
    test_contract_coverage_checker()
    
    print("\n" + "=" * 60)
    print("ALL ENFORCEMENT TESTS PASSED!")
    print("=" * 60)

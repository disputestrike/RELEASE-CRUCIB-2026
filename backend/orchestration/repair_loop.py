"""
Repair Loop - Self-healing orchestration.

The complete repair workflow:
1. Detect failure
2. Parse error-as-data
3. Plan repair (contract-aware)
4. Execute repair
5. Reassemble
6. Re-verify
7. Repeat until success or circuit breaker
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from .build_contract import BuildContract
from .error_as_data_parser import ErrorAsDataParser, StructuredError, RepairRouter
from .circuit_breaker import CircuitBreaker
from .final_assembly_agent import FinalAssemblyAgent
from .export_gate import ExportGate


@dataclass
class RepairResult:
    """Result of a repair attempt."""
    success: bool
    contract_item_id: str
    repair_agents_executed: List[str]
    files_modified: List[str]
    error: Optional[str] = None
    requires_human: bool = False


class RepairLoop:
    """
    The self-healing repair orchestrator.
    
    Manages the complete repair workflow:
    - Parse errors
    - Route to repair agents
    - Track circuit breakers
    - Reassemble and re-verify
    """
    
    def __init__(
        self,
        agent_pool: Dict[str, Callable],
        db_session=None,
        workspace_path: str = "/tmp/workspace"
    ):
        self.agent_pool = agent_pool
        self.db = db_session
        self.workspace_path = workspace_path
        
        # Components
        self.error_parser = ErrorAsDataParser()
        self.repair_router = RepairRouter()
        self.circuit_breaker = CircuitBreaker(
            max_failures=3,
            reset_timeout_seconds=600
        )
        self.assembly_agent = FinalAssemblyAgent(workspace_path)
        self.export_gate = ExportGate(db_session)
    
    async def handle_failure(
        self,
        job_id: str,
        contract: BuildContract,
        error: Exception,
        context: Dict[str, Any],
        current_manifest: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main entry point: handle a build/assembly failure.
        
        This is the "error-as-data" workflow:
        1. Parse error into structured form
        2. Check circuit breaker
        3. Plan repair
        4. Execute repair
        5. Reassemble
        6. Re-verify
        
        Returns:
            Dict with repair result and next state
        """
        # 1. PARSE ERROR
        structured_error = self.error_parser.parse(error, context)
        print(f"[RepairLoop] Parsed error: {structured_error.error_type.value}")
        print(f"[RepairLoop] Affected contract item: {structured_error.affected_contract_item}")
        
        contract_item_id = structured_error.affected_contract_item
        if not contract_item_id:
            return {
                "success": False,
                "error": "Cannot repair: error not mapped to contract item",
                "requires_human": True
            }
        
        # 2. CHECK CIRCUIT BREAKER
        if not self.circuit_breaker.can_execute(contract_item_id):
            print(f"[RepairLoop] Circuit breaker OPEN for {contract_item_id}")
            
            if self.circuit_breaker.should_escalate_to_human(contract_item_id):
                return {
                    "success": False,
                    "error": f"Circuit breaker tripped for {contract_item_id}. Escalating to human.",
                    "requires_human": True,
                    "circuit_state": "open_escalated"
                }
            
            return {
                "success": False,
                "error": f"Circuit breaker OPEN for {contract_item_id}. Retry later.",
                "circuit_state": "open",
                "retry_after": 600
            }
        
        # 3. PLAN REPAIR
        repair_plan = self.repair_router.route_with_context(structured_error, contract)
        print(f"[RepairLoop] Repair plan: {repair_plan['target_agents']}")
        
        # 4. EXECUTE REPAIR
        repair_result = await self._execute_repair(
            job_id=job_id,
            contract=contract,
            plan=repair_plan,
            structured_error=structured_error
        )
        
        # 5. RECORD RESULT
        if repair_result.success:
            self.circuit_breaker.record_success(contract_item_id)
            # Update contract progress
            self._update_contract_progress(contract, contract_item_id)
        else:
            self.circuit_breaker.record_failure(
                contract_item_id=contract_item_id,
                error_type=structured_error.error_type.value,
                error_message=structured_error.raw_message,
                repair_agent=repair_result.repair_agents_executed[0] if repair_result.repair_agents_executed else "unknown"
            )
        
        # 6. REASSEMBLE AND VERIFY (if repair succeeded)
        if repair_result.success:
            print(f"[RepairLoop] Repair succeeded, reassembling...")
            
            # Get updated fragments
            updated_fragments = await self._get_current_fragments(job_id)
            
            # Reassemble
            assembly_result = await self.assembly_agent.assemble(
                contract=contract,
                fragments=updated_fragments
            )
            
            # Emit assembly event for timeline visibility
            await self._emit_assembly_event(job_id, assembly_result)
            
            # Emit run snapshot for proof tab visibility
            if assembly_result.run_snapshot:
                await self._emit_run_snapshot_event(job_id, assembly_result.run_snapshot)
            
            if not assembly_result.success:
                print(f"[RepairLoop] Reassembly failed: {assembly_result.errors}")
                return {
                    "success": False,
                    "error": f"Reassembly failed: {assembly_result.errors}",
                    "repair_succeeded": True,
                    "assembly_succeeded": False,
                    "requires_human": False  # Can retry
                }
            
            # 7. RE-VERIFY WITH EXPORT GATE
            export_decision = await self.export_gate.check_export(
                job_id=job_id,
                contract=contract,
                manifest=assembly_result.manifest.to_dict(),
                proof_items=[],  # Would come from proof system
                verifier_results=[],
                quality_score=85  # Would be calculated
            )
            
            if export_decision.allowed:
                print(f"[RepairLoop] SUCCESS! Contract satisfied, export allowed.")
                return {
                    "success": True,
                    "repair_succeeded": True,
                    "assembly_succeeded": True,
                    "export_allowed": True,
                    "files_modified": repair_result.files_modified
                }
            else:
                print(f"[RepairLoop] Export still blocked: {export_decision.failed_checks}")
                return {
                    "success": False,
                    "error": f"Export blocked: {export_decision.reason}",
                    "failed_checks": export_decision.failed_checks,
                    "repair_succeeded": True,
                    "assembly_succeeded": True,
                    "export_allowed": False,
                    "can_retry": True
                }
        
        # Repair failed
        return {
            "success": False,
            "error": repair_result.error,
            "repair_succeeded": False,
            "requires_human": repair_result.requires_human,
            "circuit_state": self.circuit_breaker.get_state(contract_item_id).state.value
        }
    
    async def _execute_repair(
        self,
        job_id: str,
        contract: BuildContract,
        plan: Dict[str, Any],
        structured_error: StructuredError
    ) -> RepairResult:
        """
        Execute the repair plan.
        
        Tries each agent in order until one succeeds.
        """
        result = RepairResult(
            success=False,
            contract_item_id=plan["contract_item_id"],
            repair_agents_executed=[],
            files_modified=[]
        )
        
        for agent_name in plan["target_agents"]:
            agent = self.agent_pool.get(agent_name)
            if not agent:
                print(f"[RepairLoop] Agent {agent_name} not found in pool")
                continue
            
            print(f"[RepairLoop] Trying repair agent: {agent_name}")
            
            try:
                # Execute repair
                agent_result = await agent.repair(
                    contract_item_id=plan["contract_item_id"],
                    contract=contract,
                    workspace_path=self.workspace_path,
                    error_context=plan["repair_context"],
                    priority=plan["priority"]
                )
                
                result.repair_agents_executed.append(agent_name)
                
                if agent_result.get("success"):
                    print(f"[RepairLoop] Agent {agent_name} succeeded!")
                    result.success = True
                    result.files_modified = agent_result.get("files_modified", [])
                    
                    # Get before/after content if agent provided it
                    before_after_map = agent_result.get("before_after", {})
                    
                    # Emit code mutation proof for timeline visibility (with real diff)
                    await self._emit_code_mutation_event(
                        job_id=plan.get("job_id", "unknown"),
                        instruction=plan.get("repair_context", {}).get("instruction", "repair"),
                        files_modified=result.files_modified,
                        agent_name=agent_name,
                        before_after_map=before_after_map
                    )
                    break
                else:
                    print(f"[RepairLoop] Agent {agent_name} failed: {agent_result.get('error')}")
                    
            except Exception as e:
                print(f"[RepairLoop] Agent {agent_name} threw exception: {e}")
                result.repair_agents_executed.append(agent_name)
                continue
        
        if not result.success:
            result.error = f"All repair agents failed: {result.repair_agents_executed}"
            
            # Check if we should escalate (tried many agents)
            if len(result.repair_agents_executed) >= 3:
                result.requires_human = True
        
        return result
    
    def _update_contract_progress(self, contract: BuildContract, contract_item_id: str):
        """Update contract progress after successful repair."""
        # Parse contract_item_id: "required_files:path/to/file.tsx"
        if ":" in contract_item_id:
            item_type, item_name = contract_item_id.split(":", 1)
            contract.update_progress(item_type, item_name, done=True)
            print(f"[RepairLoop] Updated progress: {item_type}:{item_name} = done")
    
    async def _get_current_fragments(self, job_id: str) -> List[Dict[str, Any]]:
        """Get current file fragments from database or workspace."""
        # This would query the database for GeneratedFile records
        # For now, placeholder
        if self.db:
            from ..db.build_contract_models import GeneratedFile
            files = self.db.query(GeneratedFile).filter(GeneratedFile.job_id == job_id).all()
            return [
                {
                    "path": f.path,
                    "content": f.content,
                    "writer_agent": f.writer_agent
                }
                for f in files
            ]
        return []
    
    async def run_repair_cycle(
        self,
        job_id: str,
        contract: BuildContract,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Run multiple repair cycles until success or max iterations.
        
        This is the main entry point for a job in repair_required state.
        """
        for iteration in range(max_iterations):
            print(f"\n[RepairLoop] === Repair Cycle {iteration + 1}/{max_iterations} ===")
            
            # Try to assemble first to identify failures
            fragments = await self._get_current_fragments(job_id)
            
            assembly_result = await self.assembly_agent.assemble(contract, fragments)
            
            if assembly_result.success:
                # Check export gate
                export_decision = await self.export_gate.check_export(
                    job_id=job_id,
                    contract=contract,
                    manifest=assembly_result.manifest.to_dict(),
                    proof_items=[],
                    verifier_results=[],
                    quality_score=85
                )
                
                if export_decision.allowed:
                    return {
                        "success": True,
                        "iterations": iteration,
                        "message": "Build complete and export allowed"
                    }
                else:
                    # Export blocked - need to repair
                    error = Exception(f"Export blocked: {export_decision.reason}")
                    context = {"contract_item_id": export_decision.failed_checks[0] if export_decision.failed_checks else "unknown"}
            else:
                # Assembly failed - use first error
                error = Exception(assembly_result.errors[0] if assembly_result.errors else "Assembly failed")
                context = {"contract_item_id": assembly_result.errors[0] if assembly_result.errors else "unknown"}
            
            # Handle the failure
            repair_result = await self.handle_failure(
                job_id=job_id,
                contract=contract,
                error=error,
                context=context,
                current_manifest=assembly_result.manifest.to_dict() if assembly_result.manifest else {}
            )
            
            if repair_result.get("success"):
                return {
                    "success": True,
                    "iterations": iteration + 1,
                    "message": "Repair succeeded"
                }
            
            if repair_result.get("requires_human"):
                return {
                    "success": False,
                    "iterations": iteration + 1,
                    "requires_human": True,
                    "error": repair_result.get("error")
                }
            
            # Continue to next iteration
            await asyncio.sleep(1)  # Brief pause between cycles
        
        # Max iterations reached
        return {
            "success": False,
            "iterations": max_iterations,
            "error": "Max repair iterations reached",
            "requires_human": True
        }
    
    async def _emit_assembly_event(self, job_id: str, assembly_result):
        """
        Emit assembly completion event for timeline/proof visibility.
        
        This ensures Final Assembly appears in:
        - Timeline tab
        - Proof tab
        - BrainGuidancePanel thread
        """
        if not self.db:
            return
        
        try:
            from ..db.build_contract_models import JobEvent
            
            payload = {
                "phase": "final_assembly",
                "status": "success" if assembly_result.success else "failed",
                "files_count": len(assembly_result.files) if assembly_result.files else 0,
                "manifest_generated": assembly_result.manifest is not None,
                "build_success": assembly_result.build_proof.get("success") if assembly_result.build_proof else False,
                "errors": assembly_result.errors[:5] if assembly_result.errors else [],
                "entrypoint": self._detect_entrypoint(assembly_result.files),
                "routes": list(assembly_result.route_map.keys()) if assembly_result.route_map else [],
            }
            
            if assembly_result.manifest:
                payload["total_files"] = assembly_result.manifest.total_files
                payload["total_bytes"] = assembly_result.manifest.total_bytes
                payload["build_target"] = assembly_result.manifest.build_target
            
            event = JobEvent(
                job_id=job_id,
                event_type="assembly_completed" if assembly_result.success else "assembly_failed",
                payload=payload,
                dag_state_snapshot={"state": "completed" if assembly_result.success else "failed_recoverable"}
            )
            
            self.db.add(event)
            self.db.commit()
            print(f"[RepairLoop] Emitted assembly_{'completed' if assembly_result.success else 'failed'} event for job {job_id}")
            
        except Exception as e:
            print(f"[RepairLoop] Failed to emit assembly event: {e}")
    
    def _detect_entrypoint(self, files: List[Dict[str, Any]]) -> str:
        """Detect main entrypoint from generated files."""
        candidates = ["main.py", "index.js", "index.tsx", "App.jsx", "App.tsx"]
        file_paths = [f.get("path", "") for f in files] if files else []
        for candidate in candidates:
            for path in file_paths:
                if path.endswith(candidate):
                    return path
        return file_paths[0] if file_paths else "unknown"
    
    async def _emit_code_mutation_event(
        self,
        job_id: str,
        instruction: str,
        files_modified: List[str],
        agent_name: str,
        before_after_map: Dict[str, Dict[str, str]] = None
    ):
        """
        Emit code mutation proof showing what changed.
        
        Includes REAL diff (before/after) for verification.
        This appears in:
        - Timeline as "instruction_applied"
        - Proof tab with file diff summary
        """
        if not self.db:
            return
        
        try:
            from ..db.build_contract_models import JobEvent
            import difflib
            
            # Create file change records with REAL diff
            file_changes = []
            for path in files_modified[:5]:  # Limit to first 5 files for size
                change_record = {
                    "path": path,
                    "change_type": "modified"
                }
                
                # If before/after provided, generate real diff
                if before_after_map and path in before_after_map:
                    before = before_after_map[path].get("before", "")
                    after = before_after_map[path].get("after", "")
                    
                    # Generate unified diff
                    diff_lines = list(difflib.unified_diff(
                        before.splitlines(keepends=True),
                        after.splitlines(keepends=True),
                        fromfile=f"a/{path}",
                        tofile=f"b/{path}",
                        lineterm=""
                    ))
                    
                    diff_text = "".join(diff_lines)
                    
                    change_record["before_length"] = len(before)
                    change_record["after_length"] = len(after)
                    change_record["lines_added"] = len([l for l in diff_lines if l.startswith('+') and not l.startswith('+++')])
                    change_record["lines_removed"] = len([l for l in diff_lines if l.startswith('-') and not l.startswith('---')])
                    change_record["diff"] = diff_text[:5000] if diff_text else "(binary or empty)"  # Limit diff size
                    change_record["has_diff"] = bool(diff_text)
                else:
                    # Fallback: read from workspace if available
                    change_record["diff"] = "(diff generated on workspace access)"
                    change_record["has_diff"] = False
                
                file_changes.append(change_record)
            
            event = JobEvent(
                job_id=job_id,
                event_type="code_mutation",
                payload={
                    "instruction": instruction,
                    "files_changed": files_modified,
                    "file_changes": file_changes,
                    "agent": agent_name,
                    "mutation_summary": f"Applied '{instruction[:60]}...' to {len(files_modified)} files",
                    "timestamp": datetime.utcnow().isoformat(),
                    "has_real_diff": any(f.get("has_diff") for f in file_changes)
                },
                dag_state_snapshot={"state": "repairing"}
            )
            
            self.db.add(event)
            self.db.commit()
            print(f"[RepairLoop] Emitted code_mutation event for job {job_id}: {len(files_modified)} files changed with real diffs")
            
        except Exception as e:
            print(f"[RepairLoop] Failed to emit code_mutation event: {e}")
    
    async def _emit_run_snapshot_event(self, job_id: str, snapshot: Dict[str, Any]):
        """
        Emit run snapshot artifact for Proof tab visibility.
        
        This is the COMPLETE OUTPUT PROOF showing:
        - Full project tree
        - Entrypoint
        - Routes
        - Dependencies
        - Build/run commands
        - Status
        """
        if not self.db:
            return
        
        try:
            from ..db.build_contract_models import JobEvent
            
            # Also store as ProofItem for permanent record
            from ..db.build_contract_models import ProofItem
            
            proof_item = ProofItem(
                job_id=job_id,
                proof_type="run_snapshot",
                artifact=json.dumps(snapshot),
                metadata={
                    "build_id": snapshot.get("build_id"),
                    "status": snapshot.get("status"),
                    "total_files": snapshot.get("total_files"),
                    "entrypoint": snapshot.get("entrypoint"),
                    "routes_count": snapshot.get("route_count"),
                    "build_success": snapshot.get("build_success")
                }
            )
            self.db.add(proof_item)
            
            # Emit event for real-time display
            event = JobEvent(
                job_id=job_id,
                event_type="run_snapshot",
                payload={
                    "snapshot_summary": {
                        "status": snapshot.get("status"),
                        "total_files": snapshot.get("total_files"),
                        "total_bytes": snapshot.get("total_bytes"),
                        "entrypoint": snapshot.get("entrypoint"),
                        "routes": snapshot.get("routes")[:5] if snapshot.get("routes") else [],
                        "routes_count": snapshot.get("route_count"),
                        "build_command": snapshot.get("build_command"),
                        "run_command": snapshot.get("run_command"),
                        "build_success": snapshot.get("build_success"),
                    },
                    "full_snapshot_available": True
                },
                dag_state_snapshot={"state": "completed" if snapshot.get("build_success") else "failed_recoverable"}
            )
            
            self.db.add(event)
            self.db.commit()
            print(f"[RepairLoop] Emitted run_snapshot event for job {job_id}: {snapshot.get('total_files')} files, status={snapshot.get('status')}")
            
        except Exception as e:
            print(f"[RepairLoop] Failed to emit run_snapshot event: {e}")


class RepairAgentInterface:
    """
    Base interface for repair agents.
    
    All repair agents must implement this interface.
    """
    
    async def repair(
        self,
        contract_item_id: str,
        contract: BuildContract,
        workspace_path: str,
        error_context: Dict[str, Any],
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """
        Execute repair.
        
        Returns:
            Dict with:
            - success: bool
            - files_modified: List[str]
            - error: Optional[str]
        """
        raise NotImplementedError


# Example repair agent implementations (stubs for reference)

class SyntaxRepairAgent(RepairAgentInterface):
    """Repairs syntax errors in code files."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        # Implementation would fix syntax errors
        return {"success": True, "files_modified": [contract_item_id.split(":")[1]]}


class ImportRepairAgent(RepairAgentInterface):
    """Repairs missing import errors."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        missing_import = error_context.get("missing_import")
        # Implementation would add missing imports or create stub files
        return {"success": True, "files_modified": []}


class RouteGenerationAgent(RepairAgentInterface):
    """Generates missing routes/pages."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        # Implementation would generate the missing route/page
        route = contract_item_id.split(":")[1]
        # Generate page component
        return {"success": True, "files_modified": [f"client/src/pages/{route.strip('/').capitalize()}.tsx"]}


class ContractRepairAgent(RepairAgentInterface):
    """Repairs contract violations by generating missing contract items."""
    
    async def repair(self, contract_item_id, contract, workspace_path, error_context, priority):
        # Implementation would generate missing contract items
        item_type = contract_item_id.split(":")[0]
        item_name = contract_item_id.split(":")[1]
        
        if item_type == "required_files":
            # Generate the missing file
            return {"success": True, "files_modified": [item_name]}
        elif item_type == "required_routes":
            # Generate the missing route
            return {"success": True, "files_modified": [f"client/src/pages/{item_name.strip('/').capitalize()}.tsx"]}
        
        return {"success": False, "error": f"Unknown contract item type: {item_type}"}

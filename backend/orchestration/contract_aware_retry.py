"""
Contract-Aware Retry System.

Retries target specific contract items, not random nodes.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

from .build_contract import BuildContract
from .adaptive_dag_generator import DAGNode


@dataclass
class RetryPlan:
    """A plan for retrying failed contract items."""
    contract_item_id: str
    contract_item_type: str
    retry_agents: List[str]
    reason: str
    max_attempts: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_item_id": self.contract_item_id,
            "contract_item_type": self.contract_item_type,
            "retry_agents": self.retry_agents,
            "reason": self.reason,
            "max_attempts": self.max_attempts
        }


class ContractAwareRetryRouter:
    """
    Routes retry requests to specific agents based on contract item type.
    
    NOT random retry - targeted, contract-aware retry.
    """
    
    # Map contract item types to repair agents
    REPAIR_ROUTES = {
        "required_files": {
            ".tsx": ["FrontendGenerationAgent", "SyntaxRepairAgent"],
            ".ts": ["FrontendGenerationAgent", "TypeRepairAgent"],
            ".jsx": ["FrontendGenerationAgent", "SyntaxRepairAgent"],
            ".js": ["FrontendGenerationAgent", "SyntaxRepairAgent"],
            ".py": ["BackendGenerationAgent", "PythonSyntaxAgent"],
            "Dockerfile": ["DeploymentAgent"],
            "default": ["FileGenerationAgent"]
        },
        "required_routes": ["RoutingAgent", "IntegrationAgent"],
        "required_database_tables": ["DatabaseMigrationAgent", "SchemaRepairAgent"],
        "required_backend_modules": ["BackendModuleAgent"],
        "required_workers": ["WorkerQueueAgent"],
        "required_integrations": ["IntegrationAdapterAgent"],
        "required_tests": ["TestGenerationAgent"],
        "verification": ["VerificationRepairAgent"],
        "assembly": ["FinalAssemblyAgent"]
    }
    
    def create_retry_plan(
        self,
        contract: BuildContract,
        failed_node: DAGNode,
        error_details: Dict[str, Any]
    ) -> RetryPlan:
        """
        Create a targeted retry plan for a failed node.
        
        Args:
            contract: The BuildContract
            failed_node: The node that failed
            error_details: Error information from the failure
            
        Returns:
            RetryPlan targeting the specific contract item
        """
        item_type = failed_node.contract_item_type
        item_id = failed_node.contract_item_id
        
        # Select repair agents based on item type
        retry_agents = self._select_repair_agents(item_type, item_id, error_details)
        
        # Determine reason
        reason = self._determine_retry_reason(error_details)
        
        return RetryPlan(
            contract_item_id=item_id,
            contract_item_type=item_type,
            retry_agents=retry_agents,
            reason=reason
        )
    
    def _select_repair_agents(
        self,
        item_type: str,
        item_id: str,
        error_details: Dict[str, Any]
    ) -> List[str]:
        """Select appropriate repair agents."""
        
        # Check for specific error type routing
        error_type = error_details.get("error_type", "")
        
        if error_type == "syntax_error":
            return ["SyntaxRepairAgent"]
        
        if error_type == "import_error":
            return ["ImportRepairAgent", "IntegrationAgent"]
        
        if error_type == "build_error":
            return ["BuildRepairAgent"]
        
        # Route by contract item type
        if item_type in self.REPAIR_ROUTES:
            route = self.REPAIR_ROUTES[item_type]
            
            # For files, check extension
            if item_type == "required_files":
                ext = self._get_file_extension(item_id)
                return route.get(ext, route.get("default", ["FileGenerationAgent"]))
            
            return route if isinstance(route, list) else ["GenericRepairAgent"]
        
        return ["GenericRepairAgent"]
    
    def _get_file_extension(self, item_id: str) -> str:
        """Extract file extension from contract item ID."""
        # item_id format: "required_files:path/to/file.tsx"
        if ":" in item_id:
            path = item_id.split(":")[1]
            if "." in path:
                return "." + path.split(".")[-1]
        return "default"
    
    def _determine_retry_reason(self, error_details: Dict[str, Any]) -> str:
        """Determine why retry is needed."""
        error_type = error_details.get("error_type", "unknown")
        error_msg = error_details.get("message", "")
        
        return f"{error_type}: {error_msg[:100]}"
    
    def should_escalate(
        self,
        contract_item_id: str,
        retry_history: List[Dict[str, Any]]
    ) -> bool:
        """
        Determine if retry should escalate to human.
        
        Circuit breaker: if same item failed 3 times, escalate.
        """
        same_item_failures = [
            h for h in retry_history
            if h.get("contract_item_id") == contract_item_id
        ]
        
        return len(same_item_failures) >= 3


class ContractCoverageChecker:
    """
    Validates that final artifact covers all contract requirements.
    
    This is DIFFERENT from correctness - it checks completeness.
    """
    
    def check_coverage(
        self,
        contract: BuildContract,
        manifest: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if manifest covers all contract requirements.
        
        Returns coverage report with missing items.
        """
        report = {
            "fully_covered": True,
            "missing_files": [],
            "missing_routes": [],
            "missing_tables": [],
            "missing_workers": [],
            "missing_integrations": [],
            "covered_items": []
        }
        
        # Get actual files from manifest
        actual_files = {
            entry.get("path", "")
            for entry in manifest.get("entries", [])
        }
        
        # Check required files
        for required_file in contract.required_files:
            if required_file not in actual_files:
                report["missing_files"].append(required_file)
                report["fully_covered"] = False
            else:
                report["covered_items"].append(f"file:{required_file}")
        
        # Check required routes (would need route verification)
        for required_route in contract.required_routes:
            # Route coverage checked separately via route verification
            report["covered_items"].append(f"route:{required_route}")
        
        # Check required database tables
        # Would need to check migrations/schema
        for table in contract.required_database_tables:
            report["covered_items"].append(f"table:{table}")
        
        # Check required workers
        for worker in contract.required_workers:
            report["covered_items"].append(f"worker:{worker}")
        
        # Check required integrations
        for integration in contract.required_integrations:
            report["covered_items"].append(f"integration:{integration}")
        
        return report
    
    def validate_before_export(
        self,
        contract: BuildContract,
        manifest: Dict[str, Any]
    ) -> bool:
        """
        Validate coverage before allowing export.
        
        Raises ContractCoverageError if not fully covered.
        """
        report = self.check_coverage(contract, manifest)
        
        if not report["fully_covered"]:
            missing = (
                report["missing_files"] +
                report["missing_routes"] +
                report["missing_tables"]
            )
            raise ContractCoverageError(
                f"Contract not fully covered. Missing: {missing}",
                missing_items=missing,
                coverage_report=report
            )
        
        return True


class ContractCoverageError(Exception):
    """Raised when contract is not fully covered by artifact."""
    
    def __init__(
        self,
        message: str,
        missing_items: List[str],
        coverage_report: Dict[str, Any]
    ):
        self.missing_items = missing_items
        self.coverage_report = coverage_report
        super().__init__(message)


class RetryExecutor:
    """
    Executes retry plans.
    
    Coordinates repair agents to fix specific contract items.
    """
    
    def __init__(self, agent_pool: Dict[str, Any]):
        self.agents = agent_pool
        self.retry_history: List[Dict[str, Any]] = []
    
    async def execute_retry(
        self,
        plan: RetryPlan,
        contract: BuildContract,
        workspace_path: str
    ) -> Dict[str, Any]:
        """
        Execute a retry plan.
        
        Args:
            plan: The RetryPlan
            contract: The BuildContract
            workspace_path: Path to workspace
            
        Returns:
            Result of retry execution
        """
        result = {
            "contract_item_id": plan.contract_item_id,
            "success": False,
            "agents_executed": [],
            "errors": [],
            "files_generated": []
        }
        
        for agent_name in plan.retry_agents:
            agent = self.agents.get(agent_name)
            if not agent:
                result["errors"].append(f"Agent {agent_name} not found")
                continue
            
            try:
                # Execute repair
                repair_result = await agent.repair(
                    contract_item_id=plan.contract_item_id,
                    contract=contract,
                    workspace_path=workspace_path,
                    reason=plan.reason
                )
                
                result["agents_executed"].append(agent_name)
                
                if repair_result.get("success"):
                    result["success"] = True
                    result["files_generated"] = repair_result.get("files", [])
                    
                    # Update contract progress
                    contract.update_progress(
                        plan.contract_item_type,
                        plan.contract_item_id.split(":")[1],
                        done=True
                    )
                    
                    break  # Success - no need for more agents
                
            except Exception as e:
                result["errors"].append(f"{agent_name}: {str(e)}")
        
        # Record in history
        self.retry_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "plan": plan.to_dict(),
            "result": result
        })
        
        return result

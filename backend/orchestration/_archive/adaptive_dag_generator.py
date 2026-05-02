"""
AdaptiveDAGGenerator - Generates DAG FROM BuildContract.

NO fixed phases.
NO template selection.
Pure synthesis from contract requirements.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from enum import Enum

from .build_contract import BuildContract


class NodeType(Enum):
    """Types of DAG nodes."""
    GENERATE = "generate"
    VERIFY_STATIC = "verify_static"
    VERIFY_RUNTIME = "verify_runtime"
    INTEGRATE = "integrate"
    FINAL_ASSEMBLY = "final_assembly"
    EXPORT_GATE = "export_gate"


@dataclass
class DAGNode:
    """
    A node in the DAG.
    
    CRITICAL: Every node MUST map to a contract item.
    """
    id: str
    type: NodeType
    agent: str  # Which agent executes this
    
    # Contract binding (MANDATORY)
    contract_item_id: str  # e.g., "required_files:client/src/main.tsx"
    contract_item_type: str  # e.g., "required_files", "required_routes"
    
    # Execution
    description: str
    max_retries: int = 3
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    
    # Verification requirements
    requires_syntax_check: bool = False
    requires_import_check: bool = False
    
    # State
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None


@dataclass
class DAG:
    """The generated DAG."""
    nodes: List[DAGNode]
    build_id: str
    contract_version: int
    
    def get_node(self, node_id: str) -> Optional[DAGNode]:
        """Get node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_ready_nodes(self) -> List[DAGNode]:
        """Get nodes whose dependencies are all complete."""
        ready = []
        for node in self.nodes:
            if node.status != "pending":
                continue
            
            deps_complete = all(
                self.get_node(dep).status == "completed"
                for dep in node.depends_on
            )
            if deps_complete:
                ready.append(node)
        return ready
    
    def get_nodes_for_contract_item(self, contract_item_id: str) -> List[DAGNode]:
        """Get all nodes bound to a specific contract item."""
        return [n for n in self.nodes if n.contract_item_id == contract_item_id]
    
    def topological_sort(self) -> List[DAGNode]:
        """Return nodes in dependency order."""
        # Kahn's algorithm
        in_degree = {n.id: len(n.depends_on) for n in self.nodes}
        graph = {n.id: [] for n in self.nodes}
        
        for node in self.nodes:
            for dep in node.depends_on:
                graph[dep].append(node.id)
        
        queue = [n_id for n_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            n_id = queue.pop(0)
            node = self.get_node(n_id)
            if node:
                result.append(node)
            
            for neighbor_id in graph[n_id]:
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)
        
        return result


class AdaptiveDAGGenerator:
    """
    Generates DAG from BuildContract.
    
    Every node maps to a contract requirement.
    No fixed phases - purely adaptive.
    """
    
    def generate(self, contract: BuildContract) -> DAG:
        """
        Generate DAG from contract.
        
        Args:
            contract: The BuildContract
            
        Returns:
            DAG with all nodes bound to contract items
        """
        nodes = []
        node_counter = 0
        
        # Generate nodes for each contract requirement
        
        # 1. REQUIRED FILES
        for file_path in contract.required_files:
            node_id = f"gen_file_{node_counter}"
            node_counter += 1
            
            node = DAGNode(
                id=node_id,
                type=NodeType.GENERATE,
                agent=self._select_agent_for_file(file_path, contract),
                contract_item_id=f"required_files:{file_path}",
                contract_item_type="required_files",
                description=f"Generate {file_path}",
                requires_syntax_check=True,
                requires_import_check=True
            )
            nodes.append(node)
        
        # 2. REQUIRED DATABASE TABLES
        for table in contract.required_database_tables:
            node_id = f"gen_table_{node_counter}"
            node_counter += 1
            
            node = DAGNode(
                id=node_id,
                type=NodeType.GENERATE,
                agent="DatabaseMigrationAgent",
                contract_item_id=f"required_database_tables:{table}",
                contract_item_type="required_database_tables",
                description=f"Generate table: {table}",
                depends_on=self._get_file_nodes_for_pattern(nodes, "backend/db/")
            )
            nodes.append(node)
        
        # 3. REQUIRED ROUTES
        for route in contract.required_routes:
            node_id = f"gen_route_{node_counter}"
            node_counter += 1
            
            # Routes depend on their corresponding page file
            page_file = self._route_to_page_file(route)
            page_node_id = self._find_node_for_file(nodes, page_file)
            
            deps = []
            if page_node_id:
                deps.append(page_node_id)
            
            node = DAGNode(
                id=node_id,
                type=NodeType.GENERATE,
                agent="RoutingAgent",
                contract_item_id=f"required_routes:{route}",
                contract_item_type="required_routes",
                description=f"Wire route: {route}",
                depends_on=deps
            )
            nodes.append(node)
        
        # 4. REQUIRED BACKEND MODULES
        for module in contract.required_backend_modules:
            node_id = f"gen_module_{node_counter}"
            node_counter += 1
            
            node = DAGNode(
                id=node_id,
                type=NodeType.GENERATE,
                agent="BackendModuleAgent",
                contract_item_id=f"required_backend_modules:{module}",
                contract_item_type="required_backend_modules",
                description=f"Generate module: {module}",
                depends_on=self._get_file_nodes_for_pattern(nodes, "backend/")
            )
            nodes.append(node)
        
        # 5. REQUIRED WORKERS
        for worker in contract.required_workers:
            node_id = f"gen_worker_{node_counter}"
            node_counter += 1
            
            node = DAGNode(
                id=node_id,
                type=NodeType.GENERATE,
                agent="WorkerQueueAgent",
                contract_item_id=f"required_workers:{worker}",
                contract_item_type="required_workers",
                description=f"Generate worker: {worker}",
                depends_on=self._get_nodes_for_contract_type(nodes, "required_backend_modules")
            )
            nodes.append(node)
        
        # 6. REQUIRED INTEGRATIONS
        for integration in contract.required_integrations:
            node_id = f"gen_integration_{node_counter}"
            node_counter += 1
            
            node = DAGNode(
                id=node_id,
                type=NodeType.GENERATE,
                agent="IntegrationAdapterAgent",
                contract_item_id=f"required_integrations:{integration}",
                contract_item_type="required_integrations",
                description=f"Generate integration: {integration}"
            )
            nodes.append(node)
        
        # 7. STATIC VERIFICATION (after every 5 generate nodes)
        batch_size = 5
        generate_nodes = [n for n in nodes if n.type == NodeType.GENERATE]
        
        for i in range(0, len(generate_nodes), batch_size):
            batch = generate_nodes[i:i+batch_size]
            node_id = f"verify_static_{i//batch_size}"
            
            verify_node = DAGNode(
                id=node_id,
                type=NodeType.VERIFY_STATIC,
                agent="StaticAnalysisAgent",
                contract_item_id=f"verify:batch_{i//batch_size}",
                contract_item_type="verification",
                description=f"Syntax/import check for batch {i//batch_size}",
                depends_on=[n.id for n in batch]
            )
            nodes.append(verify_node)
        
        # 8. RUNTIME VERIFICATION (contract-driven)
        verification_deps = [n.id for n in nodes if n.type == NodeType.VERIFY_STATIC]
        
        if contract.required_preview_routes:
            node_id = f"verify_preview_{node_counter}"
            node_counter += 1
            
            preview_node = DAGNode(
                id=node_id,
                type=NodeType.VERIFY_RUNTIME,
                agent="PreviewVerifier",
                contract_item_id="verify:preview",
                contract_item_type="verification",
                description="Verify preview renders",
                depends_on=verification_deps
            )
            nodes.append(preview_node)
            verification_deps.append(node_id)
        
        if contract.required_database_tables:
            node_id = f"verify_db_{node_counter}"
            node_counter += 1
            
            db_node = DAGNode(
                id=node_id,
                type=NodeType.VERIFY_RUNTIME,
                agent="DatabaseVerifier",
                contract_item_id="verify:database",
                contract_item_type="verification",
                description="Verify database migrations",
                depends_on=verification_deps
            )
            nodes.append(db_node)
            verification_deps.append(node_id)
        
        # 9. FINAL ASSEMBLY (depends on all verification)
        assembly_node = DAGNode(
            id="final_assembly",
            type=NodeType.FINAL_ASSEMBLY,
            agent="FinalAssemblyAgent",
            contract_item_id="assembly:final",
            contract_item_type="assembly",
            description="Assemble final artifact",
            depends_on=verification_deps,
            max_retries=1  # Don't retry assembly multiple times
        )
        nodes.append(assembly_node)
        
        # 10. EXPORT GATE (depends on assembly)
        export_node = DAGNode(
            id="export_gate",
            type=NodeType.EXPORT_GATE,
            agent="ExportGate",
            contract_item_id="gate:export",
            contract_item_type="export",
            description="Validate export permission",
            depends_on=["final_assembly"],
            max_retries=0  # No retries - this is a gate
        )
        nodes.append(export_node)
        
        return DAG(
            nodes=nodes,
            build_id=contract.build_id,
            contract_version=contract.version
        )
    
    def _select_agent_for_file(self, file_path: str, contract: BuildContract) -> str:
        """Select appropriate agent for file type."""
        if "client/src/pages/" in file_path:
            return "PageComponentAgent"
        elif "client/src/components/" in file_path:
            return "UIComponentAgent"
        elif "backend/routes/" in file_path:
            return "APIRouteAgent"
        elif "backend/models/" in file_path or "db/" in file_path:
            return "DatabaseModelAgent"
        elif file_path.endswith((".tsx", ".jsx", ".ts", ".js")):
            return "FrontendGenerationAgent"
        elif file_path.endswith(".py"):
            return "BackendGenerationAgent"
        elif file_path == "Dockerfile":
            return "DeploymentAgent"
        else:
            return "FileGenerationAgent"
    
    def _route_to_page_file(self, route: str) -> str:
        """Convert route to expected page file path."""
        # Remove leading slash
        route_clean = route.lstrip("/")
        
        if route_clean == "":
            return "client/src/pages/Home.tsx"
        
        # Convert to PascalCase
        parts = route_clean.replace("-", "_").split("/")
        page_name = "".join(p.capitalize() for p in parts)
        
        return f"client/src/pages/{page_name}.tsx"
    
    def _find_node_for_file(self, nodes: List[DAGNode], file_path: str) -> Optional[str]:
        """Find node ID that generates a specific file."""
        for node in nodes:
            if node.contract_item_id == f"required_files:{file_path}":
                return node.id
        return None
    
    def _get_file_nodes_for_pattern(self, nodes: List[DAGNode], pattern: str) -> List[str]:
        """Get node IDs for files matching pattern."""
        return [
            n.id for n in nodes
            if n.contract_item_type == "required_files" and pattern in n.contract_item_id
        ]
    
    def _get_nodes_for_contract_type(self, nodes: List[DAGNode], contract_type: str) -> List[str]:
        """Get all node IDs for a contract item type."""
        return [
            n.id for n in nodes
            if n.contract_item_type == contract_type
        ]


class ContractBoundExecution:
    """
    Enforces that every node execution is bound to a contract item.
    
    If a node has no contract binding, it is REJECTED.
    """
    
    @staticmethod
    def validate_node(node: DAGNode) -> bool:
        """
        Validate that a node is properly bound to a contract item.
        
        Returns True if valid, raises exception if not.
        """
        if not node.contract_item_id:
            raise UnboundNodeError(
                f"Node {node.id} has no contract_item_id. "
                "Every node MUST map to a contract requirement."
            )
        
        if not node.contract_item_type:
            raise UnboundNodeError(
                f"Node {node.id} has no contract_item_type."
            )
        
        return True
    
    @staticmethod
    def get_contract_item_status(node: DAGNode, contract: BuildContract) -> str:
        """
        Get the status of a contract item from progress tracking.
        """
        item_type = node.contract_item_type
        item_id = node.contract_item_id.split(":")[1]  # Remove prefix
        
        if item_type in contract.contract_progress:
            progress = contract.contract_progress[item_type]
            if item_id in progress.get("done", []):
                return "done"
            elif item_id in progress.get("missing", []):
                return "missing"
        
        return "unknown"


class UnboundNodeError(Exception):
    """Raised when a node has no contract binding."""
    pass


class BlockCompletion(Exception):
    """Raised when contract is not satisfied but completion is attempted."""
    
    def __init__(self, reason: str, missing_items: List[str]):
        self.reason = reason
        self.missing_items = missing_items
        super().__init__(f"Contract not satisfied: {reason}")

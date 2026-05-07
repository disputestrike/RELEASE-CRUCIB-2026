"""
BuildContract - The single source of truth for all builds.

This module defines the BuildContract dataclass that controls:
- Generation requirements
- Verification gates
- Repair routing
- Scoring rules
- Export policy

The contract is generated FROM intent, not selected from a list.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import copy
import json


@dataclass
class ContractDelta:
    """
    Immutable record of contract changes.
    Used when repair/replanning requires contract updates.
    """
    delta_id: str
    timestamp: datetime
    previous_version: int
    new_version: int
    changes: List[Dict]  # [{"field": "required_files", "old": [...], "new": [...]}]
    reason: str  # Why the change occurred
    trigger: str  # "repair_failed", "human_request", "replanning"
    approved_by: str  # "agent_X", "human_user", "auto_approved"
    context: Dict  # What was failing that required this change
    
    def to_dict(self) -> Dict:
        return {
            "delta_id": self.delta_id,
            "timestamp": self.timestamp.isoformat(),
            "previous_version": self.previous_version,
            "new_version": self.new_version,
            "changes": self.changes,
            "reason": self.reason,
            "trigger": self.trigger,
            "approved_by": self.approved_by,
            "context": self.context
        }


@dataclass
class BuildContract:
    """
    The central contract that controls the entire build lifecycle.
    
    This is generated FROM intent dimensions, not selected from a template.
    It is versioned and only frozen after explicit approval.
    """
    # Identity & Versioning (REQUIRED - no defaults)
    build_id: str
    build_class: str  # Emergent from intent classification
    product_name: str
    original_goal: str
    
    # Versioning (with defaults - must come after required fields)
    version: int = 1
    status: str = "draft"  # "draft" → "approved" → "frozen"
    
    # Intent Dimensions (with defaults)
    dimensions: Dict[str, Any] = field(default_factory=dict)
    
    # Stack (with defaults)
    stack: Dict[str, str] = field(default_factory=dict)

    # Product Contract Shape (with defaults)
    target_platforms: List[str] = field(default_factory=list)
    users: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    core_workflows: List[str] = field(default_factory=list)
    data_models: List[str] = field(default_factory=list)
    auth_requirements: List[str] = field(default_factory=list)
    billing_requirements: List[str] = field(default_factory=list)
    compliance_requirements: List[str] = field(default_factory=list)
    security_controls: List[str] = field(default_factory=list)
    deployment_target: str = ""
    
    # Required Artifacts (with defaults)
    required_files: List[str] = field(default_factory=list)
    required_folders: List[str] = field(default_factory=list)
    required_routes: List[str] = field(default_factory=list)
    required_pages: List[str] = field(default_factory=list)
    required_backend_modules: List[str] = field(default_factory=list)
    required_api_endpoints: List[str] = field(default_factory=list)
    required_database_tables: List[str] = field(default_factory=list)
    required_migrations: List[str] = field(default_factory=list)
    required_workers: List[str] = field(default_factory=list)
    required_integrations: List[str] = field(default_factory=list)
    required_tests: List[str] = field(default_factory=list)
    required_docs: List[str] = field(default_factory=list)
    
    # Visual QA (with defaults)
    required_preview_routes: List[str] = field(default_factory=list)
    required_visual_checks: List[str] = field(default_factory=list)
    required_mobile_viewports: List[str] = field(default_factory=list)
    required_screenshots: List[str] = field(default_factory=list)
    required_deploy_artifacts: List[str] = field(default_factory=list)
    required_proof_types: List[str] = field(default_factory=list)
    
    # Forbidden (with defaults)
    forbidden_patterns: List[str] = field(default_factory=lambda: [
        "Markdown inside .tsx",
        "placeholder deploy command",
        "hardcoded secrets",
        "client-supplied price"
    ])
    forbidden_providers: List[str] = field(default_factory=lambda: ["Stripe", "Braintree"])
    
    # Verification (with defaults)
    verifiers_required: List[str] = field(default_factory=list)
    verifiers_blocking: List[str] = field(default_factory=list)
    
    # Repair (with defaults)
    repair_routes: Dict[str, List[str]] = field(default_factory=dict)
    
    # Scoring (with defaults)
    scoring_weights: Dict[str, float] = field(default_factory=lambda: {
        "generic_agent_log": 0.0,
        "file_exists": 1.0,
        "syntax_ok": 2.0,
        "import_resolves": 2.0,
        "build_pass": 15.0,
        "preview_pass": 15.0,
        "route_proven": 10.0,
        "database_proven": 10.0,
        "test_pass": 10.0,
        "screenshot_valid": 10.0,
        "visual_check_pass": 10.0,
        "goal_satisfied": 20.0
    })
    minimum_score: int = 85
    hard_cap_rules: List[Dict] = field(default_factory=lambda: [
        {"condition": "build_failed", "max_score": 35},
        {"condition": "preview_failed", "max_score": 40},
        {"condition": "routes_empty", "max_score": 50},
        {"condition": "database_empty_when_required", "max_score": 50},
        {"condition": "blocking_verifier_failed", "success": False},
        {"condition": "export_gate_failed", "success": False},
        {"condition": "generic_proofs_exceed_verified", "confidence": "low"},
        {"condition": "required_contract_item_missing", "cap_by_severity": True}
    ])
    
    # Export Policy (with defaults)
    export_policy: Dict[str, Any] = field(default_factory=lambda: {
        "allow_export_if_failed": False,
        "minimum_score": 85,
        "required_green_gates": [
            "build_pass",
            "preview_pass",
            "required_routes_present",
            "required_database_present"
        ]
    })
    
    # Success Criteria (with defaults)
    goal_success_criteria: List[Dict] = field(default_factory=list)
    
    # Contract Progress (with defaults)
    contract_progress: Dict = field(default_factory=lambda: {
        "required_files": {"done": [], "missing": [], "percent": 0},
        "required_routes": {"done": [], "missing": [], "percent": 0},
        "required_api_endpoints": {"done": [], "missing": [], "percent": 0},
        "required_backend_modules": {"done": [], "missing": [], "percent": 0},
        "required_database_tables": {"done": [], "missing": [], "percent": 0},
        "required_migrations": {"done": [], "missing": [], "percent": 0},
        "required_workers": {"done": [], "missing": [], "percent": 0},
        "required_integrations": {"done": [], "missing": [], "percent": 0},
        "required_tests": {"done": [], "missing": [], "percent": 0},
        "required_docs": {"done": [], "missing": [], "percent": 0},
        "required_preview_routes": {"done": [], "missing": [], "percent": 0}
    })
    
    # Plan Approval Policy (with defaults)
    approval_policy: Dict = field(default_factory=lambda: {
        "auto_approve": False,
        "requires_human_approval": True,
        "approval_checkpoints": ["contract_generated", "before_heavy_generation"],
        "risk_factors": ["payment", "compliance", "multi_tenant", "production_deploy"]
    })
    
    def freeze(self) -> "BuildContract":
        """
        Freeze the contract after approval.
        Prevents silent mutation.
        """
        self.status = "frozen"
        return self
    
    def apply_delta(self, delta: ContractDelta) -> "BuildContract":
        """
        Create new version with changes.
        Does not mutate silently - creates new contract with incremented version.
        """
        new_contract = copy.deepcopy(self)
        new_contract.version = delta.new_version
        new_contract.status = "draft"  # Requires re-approval
        
        # Apply changes
        for change in delta.changes:
            field_name = change.get("field")
            new_value = change.get("new")
            if hasattr(new_contract, field_name):
                setattr(new_contract, field_name, new_value)
        
        return new_contract
    
    def update_progress(self, item_type: str, item_name: str, done: bool = True):
        """
        Update contract progress for a specific item.
        """
        if item_type not in self.contract_progress:
            return
        
        progress = self.contract_progress[item_type]
        required_items = list(getattr(self, item_type, []) or [])
        if not progress.get("missing") and required_items:
            progress["missing"] = [it for it in required_items if it not in progress.get("done", [])]
        
        if done:
            if item_name not in progress["done"]:
                progress["done"].append(item_name)
            if item_name in progress["missing"]:
                progress["missing"].remove(item_name)
        else:
            if item_name not in progress["missing"]:
                progress["missing"].append(item_name)
        
        # Keep missing aligned to the authoritative required list.
        if required_items:
            done_set = set(progress.get("done", []))
            progress["done"] = [it for it in required_items if it in done_set]
            progress["missing"] = [it for it in required_items if it not in done_set]

        # Recalculate percent
        total = len(progress["done"]) + len(progress["missing"])
        if total > 0:
            progress["percent"] = int((len(progress["done"]) / total) * 100)
        else:
            progress["percent"] = 0
    
    def is_satisfied(self) -> bool:
        """
        Check if all required contract items are complete.
        
        This checks both the progress tracking AND the required_* lists
        to ensure all requirements are met.
        """
        # Map required_* lists to their progress tracking keys
        required_checks = [
            ("required_files", self.required_files),
            ("required_routes", self.required_routes),
            ("required_api_endpoints", self.required_api_endpoints),
            ("required_database_tables", self.required_database_tables),
        ]
        
        for progress_key, required_list in required_checks:
            progress = self.contract_progress.get(progress_key, {})
            if not required_list:
                if progress.get("missing"):
                    return False
                continue  # No requirements for this type

            done_items = set(progress.get("done", []))
            
            # Check that ALL required items are in "done"
            for required_item in required_list:
                if required_item not in done_items:
                    return False
        
        return True
    
    def get_missing_items(self) -> Dict[str, List[str]]:
        """
        Get all missing contract items by type.
        """
        missing = {}
        
        required_checks = [
            ("required_files", self.required_files),
            ("required_routes", self.required_routes),
            ("required_api_endpoints", self.required_api_endpoints),
            ("required_database_tables", self.required_database_tables),
            ("required_backend_modules", self.required_backend_modules),
            ("required_migrations", self.required_migrations),
            ("required_workers", self.required_workers),
            ("required_integrations", self.required_integrations),
            ("required_tests", self.required_tests),
            ("required_docs", self.required_docs),
        ]
        
        for progress_key, required_list in required_checks:
            if not required_list:
                continue
            
            progress = self.contract_progress.get(progress_key, {})
            done_items = set(progress.get("done", []))
            
            type_missing = [item for item in required_list if item not in done_items]
            if type_missing:
                missing[progress_key] = type_missing
        
        return missing
    
    def to_dict(self) -> Dict:
        """Serialize contract to dict for persistence."""
        return {
            "build_id": self.build_id,
            "version": self.version,
            "status": self.status,
            "build_class": self.build_class,
            "product_name": self.product_name,
            "original_goal": self.original_goal,
            "dimensions": self.dimensions,
            "stack": self.stack,
            "target_platforms": self.target_platforms,
            "users": self.users,
            "roles": self.roles,
            "permissions": self.permissions,
            "core_workflows": self.core_workflows,
            "data_models": self.data_models,
            "auth_requirements": self.auth_requirements,
            "billing_requirements": self.billing_requirements,
            "compliance_requirements": self.compliance_requirements,
            "security_controls": self.security_controls,
            "deployment_target": self.deployment_target,
            "required_files": self.required_files,
            "required_folders": self.required_folders,
            "required_routes": self.required_routes,
            "required_pages": self.required_pages,
            "required_backend_modules": self.required_backend_modules,
            "required_api_endpoints": self.required_api_endpoints,
            "required_database_tables": self.required_database_tables,
            "required_migrations": self.required_migrations,
            "required_workers": self.required_workers,
            "required_integrations": self.required_integrations,
            "required_tests": self.required_tests,
            "required_docs": self.required_docs,
            "required_preview_routes": self.required_preview_routes,
            "required_visual_checks": self.required_visual_checks,
            "required_mobile_viewports": self.required_mobile_viewports,
            "required_screenshots": self.required_screenshots,
            "required_deploy_artifacts": self.required_deploy_artifacts,
            "required_proof_types": self.required_proof_types,
            "forbidden_patterns": self.forbidden_patterns,
            "forbidden_providers": self.forbidden_providers,
            "verifiers_required": self.verifiers_required,
            "verifiers_blocking": self.verifiers_blocking,
            "repair_routes": self.repair_routes,
            "scoring_weights": self.scoring_weights,
            "hard_cap_rules": self.hard_cap_rules,
            "goal_success_criteria": self.goal_success_criteria,
            "contract_progress": self.contract_progress,
            "minimum_score": self.minimum_score,
            "export_policy": self.export_policy,
            "approval_policy": self.approval_policy
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "BuildContract":
        """Deserialize contract from dict."""
        return cls(
            build_id=data["build_id"],
            version=data.get("version", 1),
            status=data.get("status", "draft"),
            build_class=data["build_class"],
            product_name=data["product_name"],
            original_goal=data["original_goal"],
            dimensions=data.get("dimensions", {}),
            stack=data.get("stack", {}),
            target_platforms=data.get("target_platforms", []),
            users=data.get("users", []),
            roles=data.get("roles", []),
            permissions=data.get("permissions", []),
            core_workflows=data.get("core_workflows", []),
            data_models=data.get("data_models", []),
            auth_requirements=data.get("auth_requirements", []),
            billing_requirements=data.get("billing_requirements", []),
            compliance_requirements=data.get("compliance_requirements", []),
            security_controls=data.get("security_controls", []),
            deployment_target=data.get("deployment_target", ""),
            required_files=data.get("required_files", []),
            required_folders=data.get("required_folders", []),
            required_routes=data.get("required_routes", []),
            required_pages=data.get("required_pages", []),
            required_backend_modules=data.get("required_backend_modules", []),
            required_api_endpoints=data.get("required_api_endpoints", []),
            required_database_tables=data.get("required_database_tables", []),
            required_migrations=data.get("required_migrations", []),
            required_workers=data.get("required_workers", []),
            required_integrations=data.get("required_integrations", []),
            required_tests=data.get("required_tests", []),
            required_docs=data.get("required_docs", []),
            required_preview_routes=data.get("required_preview_routes", []),
            required_visual_checks=data.get("required_visual_checks", []),
            required_mobile_viewports=data.get("required_mobile_viewports", []),
            required_screenshots=data.get("required_screenshots", []),
            required_deploy_artifacts=data.get("required_deploy_artifacts", []),
            required_proof_types=data.get("required_proof_types", []),
            forbidden_patterns=data.get("forbidden_patterns", []),
            forbidden_providers=data.get("forbidden_providers", []),
            verifiers_required=data.get("verifiers_required", []),
            verifiers_blocking=data.get("verifiers_blocking", []),
            repair_routes=data.get("repair_routes", {}),
            scoring_weights=data.get("scoring_weights", {}),
            hard_cap_rules=data.get("hard_cap_rules", []),
            goal_success_criteria=data.get("goal_success_criteria", []),
            contract_progress=data.get("contract_progress", {}),
            minimum_score=data.get("minimum_score", 85),
            export_policy=data.get("export_policy", {}),
            approval_policy=data.get("approval_policy", {})
        )

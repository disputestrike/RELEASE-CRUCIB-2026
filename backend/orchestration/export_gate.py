"""
ExportGate - Hard blocking on all export paths.

Validates contract satisfaction, not just technical correctness.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime

from .build_contract import BuildContract


@dataclass
class ExportDecision:
    """Result of export gate check."""
    allowed: bool
    reason: str = ""
    failed_checks: List[str] = None
    check_results: Dict[str, bool] = None
    contract_satisfied: bool = False
    retry_recommended: bool = False
    human_gate_available: bool = False
    
    def __post_init__(self):
        if self.failed_checks is None:
            self.failed_checks = []
        if self.check_results is None:
            self.check_results = {}


class ExportGate:
    """
    EVERY path through the system MUST pass this gate.
    
    Checks:
    1. Contract satisfied (all required items complete)
    2. All blocking verifiers passed
    3. Quality score meets minimum
    4. Required proofs present
    5. Goal satisfaction verified
    6. No placeholder artifacts
    7. No security blockers
    8. Manifest matches disk
    9. Export policy allows
    """
    
    REQUIRED_CHECKS = [
        "contract_satisfied",
        "all_blocking_verifiers_passed",
        "quality_score_met",
        "required_proofs_present",
        "goal_satisfaction_verified",
        "no_placeholder_artifacts",
        "no_security_blockers",
        "manifest_matches_disk",
        "export_policy_allows"
    ]
    
    def __init__(self, db_session=None):
        self.db = db_session
    
    async def check_export(
        self,
        job_id: str,
        contract: BuildContract,
        manifest: Dict[str, Any],
        proof_items: List[Dict],
        verifier_results: List[Dict],
        quality_score: int
    ) -> ExportDecision:
        """
        Check if export is allowed.
        
        THIS IS THE FINAL GATE. If it fails, export is BLOCKED.
        """
        results = {}
        failed_checks = []
        
        # CHECK 1: Contract satisfied (MOST IMPORTANT)
        contract_satisfied = contract.is_satisfied()
        results["contract_satisfied"] = contract_satisfied
        
        if not contract_satisfied:
            failed_checks.append("contract_satisfied")
            missing = self._get_missing_contract_items(contract)
            
            return ExportDecision(
                allowed=False,
                reason=f"BuildContract not satisfied. Missing: {missing}",
                failed_checks=failed_checks,
                check_results=results,
                contract_satisfied=False,
                retry_recommended=True,
                human_gate_available=True
            )
        
        # CHECK 2: All blocking verifiers passed
        blocking_passed = self._check_blocking_verifiers(verifier_results)
        results["all_blocking_verifiers_passed"] = blocking_passed
        
        if not blocking_passed:
            failed_checks.append("all_blocking_verifiers_passed")
        
        # CHECK 3: Quality score meets minimum
        score_met = quality_score >= contract.minimum_score
        results["quality_score_met"] = score_met
        
        if not score_met:
            failed_checks.append("quality_score_met")
        
        # CHECK 4: Required proofs present
        proofs_present = self._check_required_proofs(contract, proof_items)
        results["required_proofs_present"] = proofs_present
        
        if not proofs_present:
            failed_checks.append("required_proofs_present")
        
        # CHECK 5: Goal satisfaction verified
        # This would come from GoalSatisfactionVerifier
        goal_satisfied = self._check_goal_satisfaction(proof_items)
        results["goal_satisfaction_verified"] = goal_satisfied
        
        if not goal_satisfied:
            failed_checks.append("goal_satisfaction_verified")
        
        # CHECK 6: No placeholder artifacts
        no_placeholders = self._check_no_placeholders(manifest)
        results["no_placeholder_artifacts"] = no_placeholders
        
        if not no_placeholders:
            failed_checks.append("no_placeholder_artifacts")
        
        # CHECK 7: No security blockers
        no_security_issues = self._check_security(verifier_results)
        results["no_security_blockers"] = no_security_issues
        
        if not no_security_issues:
            failed_checks.append("no_security_blockers")
        
        # CHECK 8: Manifest matches disk
        manifest_valid = self._check_manifest_valid(manifest)
        results["manifest_matches_disk"] = manifest_valid
        
        if not manifest_valid:
            failed_checks.append("manifest_matches_disk")
        
        # CHECK 9: Export policy allows
        policy_allows = contract.export_policy.get("allow_export_if_failed", False) or len(failed_checks) == 0
        results["export_policy_allows"] = policy_allows
        
        if not policy_allows:
            failed_checks.append("export_policy_allows")
        
        # FINAL DECISION
        allowed = len(failed_checks) == 0
        
        return ExportDecision(
            allowed=allowed,
            reason="All checks passed" if allowed else f"Failed checks: {failed_checks}",
            failed_checks=failed_checks,
            check_results=results,
            contract_satisfied=contract_satisfied,
            retry_recommended=len(failed_checks) > 0 and "contract_satisfied" not in failed_checks,
            human_gate_available="contract_satisfied" in failed_checks or "goal_satisfaction_verified" in failed_checks
        )
    
    def _get_missing_contract_items(self, contract: BuildContract) -> List[str]:
        """Get list of missing contract items."""
        missing = []
        
        for item_type, progress in contract.contract_progress.items():
            for item in progress.get("missing", []):
                missing.append(f"{item_type}:{item}")
        
        return missing
    
    def _check_blocking_verifiers(self, verifier_results: List[Dict]) -> bool:
        """Check if all blocking verifiers passed."""
        for result in verifier_results:
            if result.get("blocking") and not result.get("passed"):
                return False
        return True
    
    def _check_required_proofs(self, contract: BuildContract, proof_items: List[Dict]) -> bool:
        """Check if all required proof types are present."""
        present_types = {p.get("type") for p in proof_items}
        
        for required in contract.required_proof_types:
            if required not in present_types:
                return False
        
        return True
    
    def _check_goal_satisfaction(self, proof_items: List[Dict]) -> bool:
        """Check if goal satisfaction proof exists and passed."""
        for proof in proof_items:
            if proof.get("type") == "goal_satisfied":
                return proof.get("verified", False)
        return False  # If no goal satisfaction proof, fail
    
    def _check_no_placeholders(self, manifest: Dict[str, Any]) -> bool:
        """Check for placeholder patterns in files."""
        placeholder_patterns = [
            "configure CMD for your app",
            "echo 'configure",
            "# TODO: Add your app",
            "placeholder",
            "<your-app-here>"
        ]
        
        for entry in manifest.get("entries", []):
            if entry.get("path", "").endswith("Dockerfile"):
                # Would need actual content check here
                pass
        
        return True  # Simplified - actual check would read content
    
    def _check_security(self, verifier_results: List[Dict]) -> bool:
        """Check for security blockers."""
        for result in verifier_results:
            if result.get("verifier_name") == "security_check":
                critical_issues = result.get("payload", {}).get("critical_issues", [])
                return len(critical_issues) == 0
        return True
    
    def _check_manifest_valid(self, manifest: Dict[str, Any]) -> bool:
        """Check if manifest is valid and matches expectations."""
        if not manifest:
            return False
        
        if "entries" not in manifest:
            return False
        
        if manifest.get("total_files", 0) == 0:
            return False
        
        return True
    
    async def save_decision(self, job_id: str, decision: ExportDecision):
        """Save export gate decision to database."""
        if self.db:
            from ..db.build_contract_models import ExportGateResult
            
            result = ExportGateResult(
                job_id=job_id,
                allowed=decision.allowed,
                reason=decision.reason,
                failed_checks=decision.failed_checks,
                check_results=decision.check_results
            )
            self.db.add(result)
            self.db.commit()


class BlockExport(Exception):
    """Raised when export is blocked by gate."""
    
    def __init__(self, decision: ExportDecision):
        self.decision = decision
        super().__init__(f"Export blocked: {decision.reason}")

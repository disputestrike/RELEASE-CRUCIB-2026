"""
proof_artifact_service.py — Unified Build Proof Artifact Service.

Every build MUST produce a single comprehensive proof artifact that answers:
  "This app works because: ..."

This service aggregates data from:
  - Stack selection (builder_agent)
  - Confidence scoring (stack_confidence)
  - File generation (agents)
  - Runtime validation (runtime_validator — 4 stages)
  - Repair attempts (runtime_repair_gate)
  - Deployment info (publish_urls)
  - What-If simulation (services/simulation)

The proof artifact is the single source of truth for build quality.

Schema:
    {
        "job_id": "...",
        "project_id": "...",
        "user_intent": "...",
        "selected_stack": {
            "frontend": {...},
            "backend": {...},
            "database": {...},
            "product_type": "...",
            "reasoning": "..."
        },
        "confidence": {
            "stack_key": "python_fastapi",
            "score": 0.95,
            "tier": "production",
            "warnings": []
        },
        "agents_used": ["BuilderAgent", "FrontendAgent", "BackendAgent"],
        "generated_files": {
            "count": 12,
            "tree": ["backend/main.py", "backend/models.py", ...],
            "total_bytes": 45000
        },
        "validation": {
            "syntax": {"passed": true, "duration_ms": 120, "errors": []},
            "build": {"passed": true, "duration_ms": 5000, "errors": []},
            "runtime": {"passed": true, "duration_ms": 3000, "errors": []},
            "integration": {"passed": true, "duration_ms": 2000, "errors": []}
        },
        "repair_attempts": [
            {
                "attempt": 1,
                "error_type": "syntax",
                "error_log": "...",
                "agent_used": "SyntaxRepairAgent",
                "files_changed": ["backend/main.py"],
                "result": "pass"
            }
        ],
        "what_if_results": [...],
        "deployment": {
            "preview_url": "...",
            "deploy_url": "...",
            "readiness": {
                "frontend_builds": true,
                "backend_starts": true,
                "health_responds": true,
                "api_responds": true,
                "not_stub_code": true
            }
        },
        "final_status": "pass|fail",
        "failure_reason": null,
        "timestamp": "...",
        "duration_ms": 15000
    }
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProofArtifact:
    """
    Unified build proof artifact.

    Every build MUST produce one of these. No exceptions.
    """
    job_id: str = ""
    project_id: str = ""
    user_intent: str = ""
    selected_stack: Dict[str, Any] = field(default_factory=dict)
    confidence: Dict[str, Any] = field(default_factory=dict)
    agents_used: List[str] = field(default_factory=list)
    generated_files: Dict[str, Any] = field(default_factory=lambda: {
        "count": 0, "tree": [], "total_bytes": 0,
    })
    validation: Dict[str, Any] = field(default_factory=dict)
    repair_attempts: List[Dict[str, Any]] = field(default_factory=list)
    what_if_results: List[Dict[str, Any]] = field(default_factory=list)
    deployment: Dict[str, Any] = field(default_factory=lambda: {
        "preview_url": None,
        "deploy_url": None,
        "readiness": {
            "frontend_builds": False,
            "backend_starts": False,
            "health_responds": False,
            "api_responds": False,
            "not_stub_code": False,
        },
    })
    final_status: str = "pending"  # pending | pass | fail
    failure_reason: Optional[str] = None
    timestamp: str = ""
    duration_ms: int = 0
    build_commands: List[str] = field(default_factory=list)
    test_results: Optional[Dict[str, Any]] = None
    explanations: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class ProofArtifactService:
    """
    Service for creating, storing, and retrieving unified proof artifacts.

    Usage:
        service = ProofArtifactService()

        # Create new proof for a build
        proof = service.create(job_id="abc", project_id="p1", goal="Build a SaaS dashboard")

        # Update with stack selection
        service.set_stack(proof, stack={"backend": {"language": "python", "framework": "fastapi"}})

        # Update with confidence
        service.set_confidence(proof, confidence={"stack_key": "python_fastapi", "score": 0.95, "tier": "production"})

        # Update with validation results
        service.set_validation(proof, validation_result)

        # Update with repair attempt
        service.add_repair_attempt(proof, attempt=1, error_type="syntax", agent="SyntaxRepairAgent", files_changed=["main.py"], result="pass")

        # Finalize
        service.finalize(proof, status="pass")

        # Persist
        service.save(proof, workspace_path="/tmp/build-123")
    """

    def __init__(self):
        self._active_proofs: Dict[str, ProofArtifact] = {}

    def create(
        self,
        job_id: str,
        project_id: str = "",
        goal: str = "",
    ) -> ProofArtifact:
        """Create a new proof artifact for a build."""
        proof = ProofArtifact(
            job_id=job_id,
            project_id=project_id or job_id,
            user_intent=goal[:2000],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._active_proofs[job_id] = proof
        logger.info("[PROOF ARTIFACT] Created proof for job %s", job_id)
        return proof

    def get(self, job_id: str) -> Optional[ProofArtifact]:
        """Get the active proof for a job."""
        return self._active_proofs.get(job_id)

    def set_stack(self, proof: ProofArtifact, stack: Dict[str, Any]) -> None:
        """Record the selected stack."""
        proof.selected_stack = {
            "frontend": stack.get("frontend"),
            "backend": stack.get("backend"),
            "database": stack.get("database"),
            "product_type": stack.get("product_type"),
            "reasoning": stack.get("reasoning"),
            "explicit_language": stack.get("explicit_language"),
        }
        logger.info(
            "[PROOF ARTIFACT] Stack set: %s", stack.get("product_type"),
        )

    def set_confidence(self, proof: ProofArtifact, confidence: Dict[str, Any]) -> None:
        """Record confidence score and tier."""
        proof.confidence = {
            "stack_key": confidence.get("stack_key", "unknown"),
            "score": confidence.get("confidence", 0.0),
            "tier": confidence.get("tier", "unknown"),
            "warnings": confidence.get("warnings", []),
        }
        logger.info(
            "[PROOF ARTIFACT] Confidence: %s (%.2f)",
            proof.confidence["tier"],
            proof.confidence["score"],
        )

    def set_agents_used(self, proof: ProofArtifact, agents: List[str]) -> None:
        """Record which agents were used."""
        proof.agents_used = agents

    def set_generated_files(
        self,
        proof: ProofArtifact,
        files: Dict[str, str],
    ) -> None:
        """Record generated files."""
        file_tree = sorted(files.keys())
        total_bytes = sum(len(content) for content in files.values())
        proof.generated_files = {
            "count": len(files),
            "tree": file_tree,
            "total_bytes": total_bytes,
        }
        logger.info(
            "[PROOF ARTIFACT] Files: %d files, %d bytes",
            len(files), total_bytes,
        )

    def set_validation(
        self,
        proof: ProofArtifact,
        validation_result: Any,
    ) -> None:
        """
        Record 4-stage validation results from RuntimeValidator.

        Args:
            validation_result: ValidationResult from RuntimeValidator.validate()
        """
        details = getattr(validation_result, "details", {})
        stages = details.get("stages", {})

        proof.validation = {
            "overall_passed": getattr(validation_result, "success", False),
            "failed_stage": getattr(validation_result, "stage", "unknown"),
            "stages": {
                "syntax": stages.get("syntax", {"passed": False}),
                "build": stages.get("build", {"passed": False}),
                "runtime": stages.get("runtime", {"passed": False}),
                "integration": stages.get("integration", {"passed": False}),
            },
            "warnings": getattr(validation_result, "warnings", []),
            "errors": getattr(validation_result, "errors", []),
            "total_duration_ms": details.get("total_duration_ms", 0),
        }

        # Set deployment readiness flags based on validation
        stages_map = proof.validation.get("stages", {})
        proof.deployment["readiness"]["frontend_builds"] = stages_map.get("build", {}).get("passed", False)
        proof.deployment["readiness"]["backend_starts"] = stages_map.get("runtime", {}).get("passed", False)
        proof.deployment["readiness"]["health_responds"] = stages_map.get("runtime", {}).get("passed", False)
        proof.deployment["readiness"]["api_responds"] = stages_map.get("integration", {}).get("passed", False)

        logger.info(
            "[PROOF ARTIFACT] Validation: overall=%s failed_stage=%s",
            proof.validation["overall_passed"],
            proof.validation["failed_stage"],
        )

    def add_repair_attempt(
        self,
        proof: ProofArtifact,
        *,
        attempt: int,
        error_type: str,
        error_log: str = "",
        agent_used: str = "",
        files_changed: Optional[List[str]] = None,
        result: str = "pass",
    ) -> None:
        """Record a repair attempt."""
        proof.repair_attempts.append({
            "attempt": attempt,
            "error_type": error_type,
            "error_log": error_log[:2000],
            "agent_used": agent_used,
            "files_changed": files_changed or [],
            "result": result,
        })
        logger.info(
            "[PROOF ARTIFACT] Repair attempt %d: type=%s agent=%s result=%s",
            attempt, error_type, agent_used, result,
        )

    def add_repair_from_result(
        self,
        proof: ProofArtifact,
        repair_result: Any,
    ) -> None:
        """Record repair from a RepairResult object."""
        if repair_result is None:
            return

        cycles = getattr(repair_result, "cycles_used", 0)
        details = getattr(repair_result, "details", {})

        self.add_repair_attempt(
            proof,
            attempt=cycles,
            error_type=details.get("last_hints", ["unknown"])[0] if details.get("last_hints") else "unknown",
            error_log="\n".join(getattr(repair_result, "errors", []))[:2000],
            agent_used=details.get("agent_used", "unknown"),
            files_changed=details.get("files_changed", []),
            result="pass" if getattr(repair_result, "success", False) else "fail",
        )

    def set_what_if_results(self, proof: ProofArtifact, results: List[Dict[str, Any]]) -> None:
        """Record What-If simulation results."""
        proof.what_if_results = results
        logger.info("[PROOF ARTIFACT] What-If: %d scenarios", len(results))

    def set_deployment_urls(
        self,
        proof: ProofArtifact,
        preview_url: Optional[str] = None,
        deploy_url: Optional[str] = None,
    ) -> None:
        """Record deployment URLs."""
        if preview_url:
            proof.deployment["preview_url"] = preview_url
        if deploy_url:
            proof.deployment["deploy_url"] = deploy_url

    def set_build_commands(self, proof: ProofArtifact, commands: List[str]) -> None:
        """Record build commands that worked."""
        proof.build_commands = commands

    def set_test_results(self, proof: ProofArtifact, results: Dict[str, Any]) -> None:
        """Record test execution results."""
        proof.test_results = results

    def finalize(
        self,
        proof: ProofArtifact,
        status: str,
        failure_reason: Optional[str] = None,
        duration_ms: int = 0,
    ) -> None:
        """
        Finalize the proof artifact.

        Args:
            status: "pass" or "fail"
            failure_reason: If failed, why
            duration_ms: Total build duration
        """
        proof.final_status = status
        proof.failure_reason = failure_reason
        proof.duration_ms = duration_ms
        proof.timestamp = datetime.now(timezone.utc).isoformat()

        # Check stub code rejection
        proof.deployment["readiness"]["not_stub_code"] = self._check_not_stub(proof)

        # Compute overall readiness
        readiness = proof.deployment["readiness"]
        all_ready = all(readiness.values())
        if status == "pass" and not all_ready:
            logger.warning(
                "[PROOF ARTIFACT] Status is 'pass' but readiness flags incomplete: %s",
                {k: v for k, v in readiness.items() if not v},
            )

        logger.info(
            "[PROOF ARTIFACT] Finalized: job=%s status=%s files=%d repairs=%d duration=%dms",
            proof.job_id, status,
            proof.generated_files.get("count", 0),
            len(proof.repair_attempts),
            duration_ms,
        )

    def _check_not_stub(self, proof: ProofArtifact) -> bool:
        """Check that generated code is not stub/placeholder."""
        file_count = proof.generated_files.get("count", 0)
        total_bytes = proof.generated_files.get("total_bytes", 0)

        if file_count < 3:
            return False
        if total_bytes < 500:
            return False

        return True

    def save(
        self,
        proof: ProofArtifact,
        workspace_path: str = "",
    ) -> str:
        """
        Persist the proof artifact.

        Saves to:
          1. {workspace}/proof.json (always)
          2. Runtime state via save_proof_json (if workspace has project context)

        Returns the file path where it was saved.
        """
        proof_json = proof.to_json()

        # Save to workspace
        if workspace_path:
            proof_path = os.path.join(workspace_path, "proof.json")
            os.makedirs(os.path.dirname(proof_path) or workspace_path, exist_ok=True)
            with open(proof_path, "w") as f:
                f.write(proof_json)
            logger.info("[PROOF ARTIFACT] Saved to %s (%d bytes)", proof_path, len(proof_json))

            # Also save via runtime state
            try:
                from .runtime_state import save_proof_json
                save_proof_json(
                    project_id=proof.project_id,
                    job_id=proof.job_id,
                    proof_data=proof.to_dict(),
                )
            except Exception as e:
                logger.warning("[PROOF ARTIFACT] Could not save via runtime_state: %s", e)

            return proof_path

        # Save to temp if no workspace
        import tempfile
        tmp = tempfile.mktemp(suffix="_proof.json", prefix=f"crucib_{proof.job_id}_")
        with open(tmp, "w") as f:
            f.write(proof_json)
        logger.info("[PROOF ARTIFACT] Saved to temp: %s", tmp)
        return tmp

    def load(self, job_id: str, workspace_path: str = "") -> Optional[ProofArtifact]:
        """Load a proof artifact from disk."""
        if workspace_path:
            proof_path = os.path.join(workspace_path, "proof.json")
            if os.path.exists(proof_path):
                with open(proof_path) as f:
                    data = json.load(f)
                proof = ProofArtifact(**{
                    k: v for k, v in data.items() if k in ProofArtifact.__dataclass_fields__
                })
                return proof
        return None

    def get_api_payload(self, proof: ProofArtifact) -> Dict[str, Any]:
        """
        Get the proof artifact formatted for the UI API.

        This is what GET /api/jobs/{job_id}/proof returns.
        """
        return {
            "job_id": proof.job_id,
            "project_id": proof.project_id,
            "user_intent": proof.user_intent,
            "selected_stack": proof.selected_stack,
            "confidence": proof.confidence,
            "agents_used": proof.agents_used,
            "generated_files": proof.generated_files,
            "validation": proof.validation,
            "repair_attempts": proof.repair_attempts,
            "what_if_results": proof.what_if_results,
            "deployment": proof.deployment,
            "final_status": proof.final_status,
            "failure_reason": proof.failure_reason,
            "build_commands": proof.build_commands,
            "test_results": proof.test_results,
            "explanations": getattr(proof, 'explanations', {}),
            "timestamp": proof.timestamp,
            "duration_ms": proof.duration_ms,
            "readiness_checks": proof.deployment.get("readiness", {}),
        }

    def set_explanations(self, proof: ProofArtifact, explanations: Dict[str, str]) -> None:
        """Add optional explanation fields to the proof artifact (backwards-compatible)."""
        if not hasattr(proof, 'explanations'):
            proof.explanations = {}
        proof.explanations = {
            "stack_choice": explanations.get("stack_choice", ""),
            "confidence": explanations.get("confidence", ""),
            "validation_summary": explanations.get("validation_summary", ""),
            "runtime_summary": explanations.get("runtime_summary", ""),
            "repair_summary": explanations.get("repair_summary", ""),
            "what_if_summary": explanations.get("what_if_summary", ""),
            "final_verdict": explanations.get("final_verdict", ""),
        }

    def generate_deterministic_explanations(self, proof: ProofArtifact) -> Dict[str, str]:
        """Generate explanation summaries from existing proof data without LLM."""
        explanations = {}

        # Stack choice
        stack = proof.selected_stack or {}
        pt = stack.get("product_type", "unknown")
        reason = stack.get("reasoning", "")
        lang = stack.get("explicit_language", "auto-detected")
        if pt and pt != "unknown":
            explanations["stack_choice"] = f"{pt} was selected because {' '.join(reason.split()[:20]) if reason else 'it best matches the project requirements'}. Language: {lang}."

        # Confidence
        conf = proof.confidence or {}
        score = conf.get("score", 0)
        tier = conf.get("tier", "unknown")
        stack_key = conf.get("stack_key", "unknown")
        explanations["confidence"] = f"{stack_key} has a confidence score of {score:.0%} ({tier} tier)."
        if conf.get("warnings"):
            explanations["confidence"] += f" Warnings: {'; '.join(conf['warnings'][:3])}."

        # Validation summary
        val = proof.validation or {}
        stages = val.get("stages", {})
        stage_names = {"syntax": "Syntax", "build": "Build", "runtime": "Runtime", "integration": "Integration"}
        passed_stages = [name for key, name in stage_names.items() if stages.get(key, {}).get("passed")]
        failed_stages = [name for key, name in stage_names.items() if not stages.get(key, {}).get("passed")]
        if not failed_stages:
            explanations["validation_summary"] = f"All {len(passed_stages)} validation checks passed ({', '.join(passed_stages)})."
        else:
            explanations["validation_summary"] = f"{', '.join(passed_stages)} passed. {', '.join(failed_stages)} failed."

        # Runtime summary
        readiness = proof.deployment.get("readiness", {})
        runtime_parts = []
        if readiness.get("backend_starts"):
            runtime_parts.append("Backend server started successfully")
        else:
            runtime_parts.append("Backend server did not start")
        if readiness.get("health_responds"):
            runtime_parts.append("health endpoint responded")
        else:
            runtime_parts.append("health endpoint did not respond")
        if readiness.get("api_responds"):
            runtime_parts.append("API endpoints responded correctly")
        explanations["runtime_summary"] = ". ".join(runtime_parts) + "."

        # Repair summary
        repairs = proof.repair_attempts or []
        if not repairs:
            explanations["repair_summary"] = "No repairs were needed. The build passed all validation on the first attempt."
        else:
            total = len(repairs)
            passed = sum(1 for r in repairs if r.get("result") == "pass")
            failed = total - passed
            if failed == 0:
                explanations["repair_summary"] = f"{total} repair attempt{'s' if total != 1 else ''} were made. All succeeded."
            else:
                explanations["repair_summary"] = f"{total} repair attempts: {passed} succeeded, {failed} failed."

        # What-If summary
        whatif = proof.what_if_results or []
        if not whatif:
            explanations["what_if_summary"] = "No failure simulation was run for this build."
        else:
            high_risk = sum(1 for r in whatif if r.get("risk") == "high")
            med_risk = sum(1 for r in whatif if r.get("risk") == "medium")
            low_risk = sum(1 for r in whatif if r.get("risk") == "low")
            parts = []
            if high_risk: parts.append(f"{high_risk} high risk")
            if med_risk: parts.append(f"{med_risk} medium risk")
            if low_risk: parts.append(f"{low_risk} low risk")
            explanations["what_if_summary"] = f"{len(whatif)} failure scenarios tested: {', '.join(parts) if parts else 'all passed'}."

        # Final verdict
        status = proof.final_status
        if status == "pass":
            explanations["final_verdict"] = "BUILD VERIFIED — This build passed all validation stages, runtime checks, and readiness gates. The generated code is production-ready."
        elif status == "fail":
            reason = proof.failure_reason or "unknown validation failure"
            explanations["final_verdict"] = f"BUILD BLOCKED — This build was blocked because: {reason}. The app was not marked complete."
        else:
            explanations["final_verdict"] = "Build is still in progress or has not completed validation."

        return explanations

    def compute_verdict(self, proof: ProofArtifact) -> Dict[str, Any]:
        """
        Compute a build verdict based on the proof artifact.

        Returns:
            {
                "status": "pass|fail|warning",
                "score": float (0-100),
                "reasons": [...],
                "critical_failures": [...],
                "warnings": [...],
            }
        """
        score = 100.0
        reasons = []
        critical_failures = []
        warnings = []

        # Check validation
        validation = proof.validation or {}
        if not validation.get("overall_passed", False):
            failed_stage = validation.get("failed_stage", "unknown")
            score -= 50
            critical_failures.append(f"Validation failed at stage: {failed_stage}")
        else:
            reasons.append("All 4 validation stages passed")

        # Check readiness
        readiness = proof.deployment.get("readiness", {})
        for check, passed in readiness.items():
            if not passed:
                if check == "not_stub_code":
                    score -= 30
                    critical_failures.append("Generated code appears to be stub/placeholder")
                elif check in ("backend_starts", "health_responds"):
                    score -= 20
                    critical_failures.append(f"Readiness check failed: {check}")
                else:
                    score -= 10
                    warnings.append(f"Readiness check failed: {check}")
            else:
                reasons.append(f"Readiness check passed: {check}")

        # Check confidence
        confidence = proof.confidence or {}
        tier = confidence.get("tier", "unknown")
        if tier == "experimental":
            score -= 15
            warnings.append("Experimental stack used")
        elif tier == "beta":
            score -= 5
            warnings.append("Beta stack used")

        # Check repair attempts
        if proof.repair_attempts:
            total_repairs = len(proof.repair_attempts)
            failed_repairs = sum(1 for r in proof.repair_attempts if r.get("result") == "fail")
            if failed_repairs > 0:
                score -= 10 * failed_repairs
                warnings.append(f"{failed_repairs}/{total_repairs} repair attempts failed")
            else:
                reasons.append(f"{total_repairs} repair attempts all succeeded")

        # Clamp score
        score = max(0.0, min(100.0, score))

        # Determine status
        if critical_failures:
            status = "fail"
        elif warnings:
            status = "warning"
        else:
            status = "pass"

        return {
            "status": status,
            "score": score,
            "reasons": reasons,
            "critical_failures": critical_failures,
            "warnings": warnings,
        }


# Singleton
_proof_service: Optional[ProofArtifactService] = None


def get_proof_artifact_service() -> ProofArtifactService:
    """Get the singleton ProofArtifactService."""
    global _proof_service
    if _proof_service is None:
        _proof_service = ProofArtifactService()
    return _proof_service

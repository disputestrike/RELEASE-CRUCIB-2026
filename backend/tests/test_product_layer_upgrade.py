"""
test_product_layer_upgrade.py

Tests for the product-layer upgrade to the proof artifact system.

Covers:
  1. Proof endpoint returns existing proof artifact (get_api_payload fields)
  2. Explanations are added without breaking old payloads
  3. generate_deterministic_explanations returns all 7 fields
  4. Explanation for failed build mentions failure reason
  5. RepairFromProofRequest model validates correctly
  6. ReplayBuildRequest model validates correctly
  7. compute_verdict returns correct status (pass / warning / fail)
"""

import sys
from pathlib import Path

import pytest

# Ensure the repo root is on sys.path so `backend.*` imports resolve.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.orchestration.proof_artifact_service import (
    ProofArtifact,
    ProofArtifactService,
    get_proof_artifact_service,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_full_proof() -> ProofArtifact:
    """Create a ProofArtifact with all fields populated."""
    proof = ProofArtifact(
        job_id="job-abc-123",
        project_id="proj-1",
        user_intent="Build a SaaS dashboard",
        selected_stack={
            "frontend": {"framework": "react", "library": "vite"},
            "backend": {"language": "python", "framework": "fastapi"},
            "database": {"engine": "postgresql"},
            "product_type": "SaaS Dashboard",
            "reasoning": "SaaS dashboard detected from user intent",
            "explicit_language": None,
        },
        confidence={
            "stack_key": "python_fastapi",
            "score": 0.95,
            "tier": "production",
            "warnings": [],
        },
        agents_used=["BuilderAgent", "FrontendAgent", "BackendAgent", "RuntimeValidator"],
        generated_files={
            "count": 12,
            "tree": ["backend/main.py", "backend/models.py", "frontend/src/App.jsx", "package.json"],
            "total_bytes": 45000,
        },
        validation={
            "overall_passed": True,
            "failed_stage": None,
            "stages": {
                "syntax": {"passed": True, "duration_ms": 120, "errors": []},
                "build": {"passed": True, "duration_ms": 5000, "errors": []},
                "runtime": {"passed": True, "duration_ms": 3000, "errors": []},
                "integration": {"passed": True, "duration_ms": 2000, "errors": []},
            },
            "warnings": [],
            "errors": [],
            "total_duration_ms": 10320,
        },
        repair_attempts=[],
        what_if_results=[],
        deployment={
            "preview_url": None,
            "deploy_url": None,
            "readiness": {
                "frontend_builds": True,
                "backend_starts": True,
                "health_responds": True,
                "api_responds": True,
                "not_stub_code": True,
            },
        },
        final_status="pass",
        failure_reason=None,
        explanations={},
        build_commands=["pip install -r requirements.txt", "python main.py"],
        test_results=None,
        timestamp="2026-05-01T00:00:00Z",
        duration_ms=15000,
    )
    return proof


# ---------------------------------------------------------------------------
# 1. Proof endpoint returns existing proof artifact
# ---------------------------------------------------------------------------

class TestGetApiPayload:
    """get_api_payload must include all expected fields."""

    def test_payload_includes_all_expected_fields(self):
        svc = ProofArtifactService()
        proof = _make_full_proof()
        payload = svc.get_api_payload(proof)

        expected_keys = {
            "job_id",
            "project_id",
            "user_intent",
            "selected_stack",
            "confidence",
            "agents_used",
            "generated_files",
            "validation",
            "repair_attempts",
            "what_if_results",
            "deployment",
            "final_status",
            "failure_reason",
            "build_commands",
            "test_results",
            "explanations",
            "timestamp",
            "duration_ms",
            "readiness_checks",
        }
        assert expected_keys.issubset(payload.keys()), (
            f"Missing keys in payload: {expected_keys - set(payload.keys())}"
        )

        # Spot-check values
        assert payload["job_id"] == "job-abc-123"
        assert payload["final_status"] == "pass"
        assert payload["confidence"]["score"] == 0.95


# ---------------------------------------------------------------------------
# 2. Explanations are added without breaking old payloads
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """A ProofArtifact created without explanations must still serialise correctly."""

    def test_missing_explanations_defaults_to_empty_dict(self):
        svc = ProofArtifactService()
        # Create a proof that never had explanations set
        proof = ProofArtifact(
            job_id="old-job",
            final_status="pass",
        )
        payload = svc.get_api_payload(proof)
        # Must exist and be a dict (empty or not)
        assert "explanations" in payload
        assert isinstance(payload["explanations"], dict)

    def test_set_explanations_preserves_existing_payload(self):
        svc = ProofArtifactService()
        proof = _make_full_proof()
        svc.set_explanations(proof, {
            "stack_choice": "Chose React + FastAPI",
            "confidence": "High confidence",
            "validation_summary": "All passed",
            "runtime_summary": "Backend started",
            "repair_summary": "No repairs",
            "what_if_summary": "No simulations",
            "final_verdict": "BUILD VERIFIED",
        })
        payload = svc.get_api_payload(proof)
        assert payload["explanations"]["stack_choice"] == "Chose React + FastAPI"
        # Core fields still intact
        assert payload["job_id"] == "job-abc-123"
        assert payload["final_status"] == "pass"


# ---------------------------------------------------------------------------
# 3. generate_deterministic_explanations returns all 7 fields
# ---------------------------------------------------------------------------

class TestDeterministicExplanations:
    """The deterministic explanation generator must produce all 7 keys."""

    REQUIRED_KEYS = {
        "stack_choice",
        "confidence",
        "validation_summary",
        "runtime_summary",
        "repair_summary",
        "what_if_summary",
        "final_verdict",
    }

    def test_returns_all_7_keys(self):
        svc = ProofArtifactService()
        proof = _make_full_proof()
        explanations = svc.generate_deterministic_explanations(proof)

        assert set(explanations.keys()) == self.REQUIRED_KEYS, (
            f"Missing explanation keys: {self.REQUIRED_KEYS - set(explanations.keys())}"
        )

    def test_each_value_is_non_empty_string(self):
        svc = ProofArtifactService()
        proof = _make_full_proof()
        explanations = svc.generate_deterministic_explanations(proof)

        for key in self.REQUIRED_KEYS:
            assert isinstance(explanations[key], str), f"{key} is not a string"
            assert len(explanations[key]) > 0, f"{key} is empty"


# ---------------------------------------------------------------------------
# 4. Explanation for failed build mentions failure reason
# ---------------------------------------------------------------------------

class TestFailedBuildExplanation:
    """When final_status is 'fail', the final_verdict must mention BLOCKED."""

    def test_fail_status_verdict_contains_blocked(self):
        svc = ProofArtifactService()
        proof = _make_full_proof()
        proof.final_status = "fail"
        proof.failure_reason = "Runtime validation failed"

        explanations = svc.generate_deterministic_explanations(proof)
        verdict = explanations["final_verdict"]

        assert "BLOCKED" in verdict, f"Expected 'BLOCKED' in verdict, got: {verdict}"

    def test_fail_verdict_includes_failure_reason(self):
        svc = ProofArtifactService()
        proof = _make_full_proof()
        proof.final_status = "fail"
        proof.failure_reason = "Syntax errors in 3 files"

        explanations = svc.generate_deterministic_explanations(proof)
        verdict = explanations["final_verdict"]

        assert "Syntax errors in 3 files" in verdict


# ---------------------------------------------------------------------------
# 5. RepairFromProofRequest model validates correctly
# ---------------------------------------------------------------------------

class TestRepairFromProofRequest:
    """RepairFromProofRequest Pydantic model must accept valid data."""

    def test_valid_repair_request(self):
        try:
            from backend.routes.jobs import RepairFromProofRequest
        except ImportError:
            pytest.skip("Route models not importable outside app context", allow_module_level=True)

        req = RepairFromProofRequest(
            job_id="job-123",
            proof_snapshot={"final_status": "fail"},
            error_context="Build failed at runtime",
            selected_repair_target="runtime",
        )
        assert req.job_id == "job-123"
        assert req.selected_repair_target == "runtime"

    def test_default_values(self):
        try:
            from backend.routes.jobs import RepairFromProofRequest
        except ImportError:
            pytest.skip("Route models not importable outside app context", allow_module_level=True)

        req = RepairFromProofRequest()
        assert req.job_id == ""
        assert req.proof_snapshot == {}
        assert req.error_context == ""
        assert req.selected_repair_target == "validation"


# ---------------------------------------------------------------------------
# 6. ReplayBuildRequest model validates correctly
# ---------------------------------------------------------------------------

class TestReplayBuildRequest:
    """ReplayBuildRequest Pydantic model must accept valid data."""

    def test_valid_replay_request(self):
        try:
            from backend.routes.jobs import ReplayBuildRequest
        except ImportError:
            pytest.skip("Route models not importable outside app context", allow_module_level=True)

        req = ReplayBuildRequest(
            goal="Rebuild the dashboard",
            stack_override="python_fastapi",
        )
        assert req.goal == "Rebuild the dashboard"
        assert req.stack_override == "python_fastapi"

    def test_default_values_are_none(self):
        try:
            from backend.routes.jobs import ReplayBuildRequest
        except ImportError:
            pytest.skip("Route models not importable outside app context", allow_module_level=True)

        req = ReplayBuildRequest()
        assert req.goal is None
        assert req.stack_override is None


# ---------------------------------------------------------------------------
# 7. compute_verdict returns correct status
# ---------------------------------------------------------------------------

class TestComputeVerdict:
    """compute_verdict must return pass / warning / fail based on proof data."""

    def test_all_pass_returns_pass_status(self):
        svc = ProofArtifactService()
        proof = _make_full_proof()
        # _make_full_proof has all stages passed and all readiness true
        verdict = svc.compute_verdict(proof)

        assert verdict["status"] == "pass"
        assert len(verdict["critical_failures"]) == 0
        assert len(verdict["warnings"]) == 0

    def test_warnings_returns_warning_status(self):
        svc = ProofArtifactService()
        proof = _make_full_proof()
        # Set an experimental tier to generate a warning
        proof.confidence["tier"] = "experimental"

        verdict = svc.compute_verdict(proof)

        assert verdict["status"] == "warning"
        assert len(verdict["warnings"]) > 0
        assert any("Experimental" in w for w in verdict["warnings"])

    def test_critical_failure_returns_fail_status(self):
        svc = ProofArtifactService()
        proof = _make_full_proof()
        # Force validation failure
        proof.validation["overall_passed"] = False
        proof.validation["failed_stage"] = "runtime"

        verdict = svc.compute_verdict(proof)

        assert verdict["status"] == "fail"
        assert len(verdict["critical_failures"]) > 0
        assert any("runtime" in f for f in verdict["critical_failures"])

    def test_score_clamped_between_0_and_100(self):
        svc = ProofArtifactService()
        proof = _make_full_proof()
        proof.validation["overall_passed"] = False
        proof.validation["failed_stage"] = "syntax"
        # Fail multiple readiness checks to push score very low
        proof.deployment["readiness"]["frontend_builds"] = False
        proof.deployment["readiness"]["backend_starts"] = False
        proof.deployment["readiness"]["health_responds"] = False
        proof.deployment["readiness"]["api_responds"] = False
        proof.deployment["readiness"]["not_stub_code"] = False

        verdict = svc.compute_verdict(proof)

        assert 0 <= verdict["score"] <= 100

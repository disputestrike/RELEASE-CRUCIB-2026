"""Proof bundle truth vs job + verification rows (§11 alignment)."""
from backend.proof.proof_service import compute_build_verdict


def test_completed_clean_is_verified_high_score():
    q, ok = compute_build_verdict(
        quality_score_raw=88.0,
        verification_failed_count=0,
        step_exception_count=0,
        job_status="completed",
    )
    assert ok is True
    assert q == 88.0


def test_preview_failures_cap_score_and_unverify():
    q, ok = compute_build_verdict(
        quality_score_raw=78.0,
        verification_failed_count=1,
        step_exception_count=0,
        job_status="completed",
    )
    assert ok is False
    assert q <= 40.0


def test_failed_job_unverified_even_without_proof_rows():
    q, ok = compute_build_verdict(
        quality_score_raw=90.0,
        verification_failed_count=0,
        step_exception_count=0,
        job_status="failed",
    )
    assert ok is False
    assert q <= 40.0

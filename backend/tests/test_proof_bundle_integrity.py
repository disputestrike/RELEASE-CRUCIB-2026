"""Proof bundle integrity hash (Fifty-point #23)."""

import pytest

from proof import proof_service


@pytest.mark.golden
def test_bundle_sha256_stable_for_same_payload():
    rows = [{"id": "a", "title": "t", "payload": {"k": 1}}]
    h1 = proof_service.compute_bundle_integrity_sha256(rows)
    h2 = proof_service.compute_bundle_integrity_sha256(rows)
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.golden
def test_bundle_sha256_empty():
    assert proof_service.compute_bundle_integrity_sha256(
        []
    ) == proof_service.compute_bundle_integrity_sha256([])

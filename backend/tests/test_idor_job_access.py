"""Job owner checks (Fifty-point #6) — pure unit tests for `_assert_job_owner_match`."""

import pytest
from fastapi import HTTPException

from server import _assert_job_owner_match


@pytest.mark.golden
def test_job_owner_match_blocks_legacy_guest_job():
    for owner_id, user_payload in (
        (None, None),
        ("", {"id": "u1"}),
        (None, {"id": "u1"}),
    ):
        with pytest.raises(HTTPException) as exc:
            _assert_job_owner_match(owner_id, user_payload)
        assert exc.value.status_code == 403


@pytest.mark.golden
def test_job_owner_match_allows_owner():
    _assert_job_owner_match("user-a", {"id": "user-a", "email": "a@x.com"})


@pytest.mark.golden
def test_job_owner_match_blocks_anon_for_owned_job():
    with pytest.raises(HTTPException) as exc:
        _assert_job_owner_match("user-a", None)
    assert exc.value.status_code == 403


@pytest.mark.golden
def test_job_owner_match_blocks_wrong_user():
    with pytest.raises(HTTPException) as exc:
        _assert_job_owner_match("user-a", {"id": "user-b"})
    assert exc.value.status_code == 403


@pytest.mark.golden
@pytest.mark.parametrize(
    "owner_id,user_payload",
    [
        (
            "550e8400-e29b-41d4-a716-446655440000",
            {"id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8", "email": "x@y.com"},
        ),
        ("job_owner_99", {"id": "job_owner_00", "email": "other@y.com"}),
    ],
)
def test_job_owner_match_rejects_mismatched_ids(owner_id, user_payload):
    with pytest.raises(HTTPException) as exc:
        _assert_job_owner_match(owner_id, user_payload)
    assert exc.value.status_code == 403

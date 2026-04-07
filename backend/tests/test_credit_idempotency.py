"""Credit usage idempotency (fifty-point #17)."""
import pytest

from credit_tracker import CreditTracker


class _FakeUsageLog:
    def __init__(self):
        self.by_id = {}

    async def find_one(self, query):
        _id = query.get("_id")
        if _id is None:
            return None
        return self.by_id.get(_id)

    async def insert_one(self, doc):
        _id = doc["_id"]
        if _id in self.by_id:
            raise Exception("E11000 duplicate key error")
        self.by_id[_id] = doc


class _FakeUsers:
    def __init__(self, balance):
        self.balance = balance

    async def find_one(self, query, projection=None):
        uid = query.get("id")
        if uid == "u1":
            return {"id": "u1", "credit_balance": self.balance}
        return None

    async def update_one(self, query, update):
        inc = (update.get("$inc") or {}).get("credit_balance", 0)
        self.balance += inc


class _FakeDB:
    def __init__(self, start_balance: int = 100):
        self.usage_log = _FakeUsageLog()
        self.users = _FakeUsers(start_balance)


@pytest.mark.asyncio
async def test_record_usage_idempotent_second_call_no_double_deduct():
    db = _FakeDB(start_balance=100)
    key = "pay-req-abc"
    r1 = await CreditTracker.record_usage(
        db,
        "u1",
        "haiku",
        1000,
        "builder",
        "agent",
        "proj1",
        idempotency_key=key,
    )
    assert r1.get("replay") is not True
    assert r1["credits_deducted"] >= 0
    bal_after_first = r1["remaining_credits"]

    r2 = await CreditTracker.record_usage(
        db,
        "u1",
        "haiku",
        1000,
        "builder",
        "agent",
        "proj1",
        idempotency_key=key,
    )
    assert r2.get("replay") is True
    assert r2["credits_deducted"] == 0.0
    assert r2["remaining_credits"] == bal_after_first


@pytest.mark.asyncio
async def test_record_usage_without_key_uses_distinct_ids():
    db = _FakeDB(start_balance=500)
    a = await CreditTracker.record_usage(db, "u1", "llama", 100, "free", "a", "p")
    b = await CreditTracker.record_usage(db, "u1", "llama", 100, "free", "a", "p")
    assert a["usage_id"] != b["usage_id"]


@pytest.mark.asyncio
async def test_duplicate_insert_race_returns_replay():
    """Stale read (find misses) but insert loses race → duplicate key → replay, no double deduct."""

    class _StaleFindDupInsert(_FakeUsageLog):
        async def find_one(self, query):
            return None

        async def insert_one(self, doc):
            raise Exception("E11000 duplicate key error collection: usage_log index: _id_")

    db = _FakeDB()
    db.usage_log = _StaleFindDupInsert()

    r = await CreditTracker.record_usage(
        db, "u1", "haiku", 1000, "builder", "agent", "p", idempotency_key="race-key"
    )
    assert r.get("replay") is True
    assert r["credits_deducted"] == 0.0
    assert r["remaining_credits"] == 100

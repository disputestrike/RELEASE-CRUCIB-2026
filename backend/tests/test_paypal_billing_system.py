from __future__ import annotations

import pytest

from backend.services.paypal_billing import (
    billing_overview,
    ensure_catalog,
    process_webhook,
    user_has_access,
)


class Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, key, direction=1):
        self.rows.sort(key=lambda row: row.get(key, ""), reverse=direction == -1)
        return self

    async def to_list(self, length=None):
        return list(self.rows[:length] if length else self.rows)


class Collection:
    def __init__(self):
        self.rows = []

    def _matches(self, row, query):
        return all(row.get(k) == v for k, v in (query or {}).items())

    async def find_one(self, query=None, projection=None, sort=None):
        rows = [row for row in self.rows if self._matches(row, query)]
        if sort:
            for key, direction in reversed(sort):
                rows.sort(key=lambda row: row.get(key, ""), reverse=direction == -1)
        return dict(rows[0]) if rows else None

    def find(self, query=None, projection=None):
        return Cursor([dict(row) for row in self.rows if self._matches(row, query)])

    async def insert_one(self, doc):
        self.rows.append(dict(doc))
        return {"inserted_id": doc.get("id")}

    async def update_one(self, query, update):
        for row in self.rows:
            if self._matches(row, query):
                row.update(update.get("$set") or {})
                for key, value in (update.get("$inc") or {}).items():
                    row[key] = row.get(key, 0) + value
                return {"matched_count": 1, "modified_count": 1}
        return {"matched_count": 0, "modified_count": 0}


class Db:
    def __getattr__(self, name):
        col = Collection()
        setattr(self, name, col)
        return col


@pytest.mark.asyncio
async def test_paypal_catalog_uses_approved_pricing():
    db = Db()
    catalog = await ensure_catalog(db)
    prices = await db.prices.find({}).sort("amount", 1).to_list(50)

    assert catalog["product"]["name"] == "CrucibAI Credits"
    assert {p["id"] for p in prices} >= {
        "price_builder_one_time",
        "price_pro_one_time",
        "price_scale_one_time",
        "price_teams_one_time",
    }
    pro_price = await db.prices.find_one({"id": "price_pro_one_time"})
    assert pro_price["amount"] == 30.0


@pytest.mark.asyncio
async def test_paypal_successful_order_grants_access():
    db = Db()
    await ensure_catalog(db)
    await db.users.insert_one({"id": "u1", "email": "u@example.com"})
    await db.orders.insert_one(
        {
            "id": "ord_1",
            "user_id": "u1",
            "product_id": "prod_crucibai_credits",
            "payment_type": "one_time",
            "status": "success",
        }
    )

    assert await user_has_access(db, "u1", "prod_crucibai_credits") is True


@pytest.mark.asyncio
async def test_paypal_webhook_processing_is_idempotent():
    db = Db()
    event = {"id": "WH-1", "event_type": "CHECKOUT.ORDER.APPROVED"}

    first = await process_webhook(db, event, headers={})
    second = await process_webhook(db, event, headers={})

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"
    assert len(db.billing_events.rows) == 1


@pytest.mark.asyncio
async def test_paypal_billing_overview_exposes_provider(monkeypatch):
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "client")
    db = Db()
    await db.users.insert_one({"id": "u1", "email": "u@example.com"})

    overview = await billing_overview(db, {"id": "u1"})

    assert overview["provider"] == "paypal"
    assert overview["paypal_client_id"] == "client"
    assert overview["products"][0]["name"] == "CrucibAI Credits"

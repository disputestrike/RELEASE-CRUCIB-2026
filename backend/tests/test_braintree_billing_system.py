from __future__ import annotations

import pytest

from backend.services.braintree_billing import (
    BillingError,
    billing_overview,
    change_subscription_plan,
    create_one_time_checkout,
    create_subscription_checkout,
    process_webhook,
    update_default_payment_method,
    user_has_access,
)


class Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, key, direction=1):
        reverse = direction == -1
        self.rows.sort(key=lambda row: row.get(key, ""), reverse=reverse)
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

    async def update_many(self, query, update):
        count = 0
        for row in self.rows:
            if self._matches(row, query):
                row.update(update.get("$set") or {})
                count += 1
        return {"matched_count": count, "modified_count": count}


class Db:
    def __getattr__(self, name):
        col = Collection()
        setattr(self, name, col)
        return col


class Result:
    def __init__(self, success=True, **kwargs):
        self.is_success = success
        self.errors = "rejected" if not success else None
        for key, value in kwargs.items():
            setattr(self, key, value)


class Obj:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Gateway:
    def __init__(self):
        self.customer = Obj(create=lambda payload=None: Result(True, customer=Obj(id="bt_cust_1")))
        self.payment_method = Obj(create=lambda payload: Result(True, payment_method=Obj(
            token="pm_token_1",
            card_type="Visa",
            last_4="1111",
            expiration_month="12",
            expiration_year="2030",
        )))
        self.transaction = Obj(sale=lambda payload: Result(True, transaction=Obj(
            id="txn_1",
            status="submitted_for_settlement",
            amount=payload["amount"],
            currency_iso_code="USD",
        )))
        self.subscription = Obj(
            create=lambda payload: Result(True, subscription=Obj(
                id="sub_bt_1",
                status="Active",
                billing_period_end_date="2026-05-27",
                transactions=[Obj(id="sub_txn_1", status="submitted_for_settlement", amount=payload.get("price", "15.00"), currency_iso_code="USD")],
            )),
            update=lambda sub_id, payload: Result(True, subscription=Obj(
                id=sub_id,
                status="Active",
                billing_period_end_date="2026-06-27",
            )),
            cancel=lambda sub_id: Result(True),
        )


@pytest.mark.asyncio
async def test_one_time_checkout_uses_server_price_and_grants_access():
    db = Db()
    await db.users.insert_one({"id": "u1", "email": "u@example.com", "credit_balance": 0, "token_balance": 0})

    result = await create_one_time_checkout(
        db,
        Gateway(),
        {"id": "u1", "email": "u@example.com"},
        product_id=None,
        price_id="price_builder_one_time",
        payment_method_nonce="fake-valid-nonce",
        idempotency_key="idem-1",
    )

    assert result["status"] == "success"
    assert result["order"]["amount"] == 15.0
    user = await db.users.find_one({"id": "u1"})
    assert user["credit_balance"] == 500
    assert await user_has_access(db, "u1", result["order"]["product_id"]) is True


@pytest.mark.asyncio
async def test_subscription_creation_requires_braintree_plan_mapping(monkeypatch):
    monkeypatch.delenv("BRAINTREE_PLAN_BUILDER_MONTHLY", raising=False)
    db = Db()
    await db.users.insert_one({"id": "u1", "email": "u@example.com"})

    with pytest.raises(BillingError) as exc:
        await create_subscription_checkout(
            db,
            Gateway(),
            {"id": "u1", "email": "u@example.com"},
            product_id=None,
            price_id="price_builder_monthly",
            payment_method_nonce="nonce",
        )

    assert exc.value.code == "missing_braintree_plan_id"


@pytest.mark.asyncio
async def test_subscription_update_cancel_and_billing_overview(monkeypatch):
    monkeypatch.setenv("BRAINTREE_PLAN_BUILDER_MONTHLY", "bt_builder_monthly")
    monkeypatch.setenv("BRAINTREE_PLAN_PRO_MONTHLY", "bt_pro_monthly")
    db = Db()
    await db.users.insert_one({"id": "u1", "email": "u@example.com"})
    gateway = Gateway()

    created = await create_subscription_checkout(
        db,
        gateway,
        {"id": "u1", "email": "u@example.com"},
        product_id=None,
        price_id="price_builder_monthly",
        payment_method_nonce="nonce",
    )
    sub = created["subscription"]

    update_pm = await update_default_payment_method(
        db,
        gateway,
        {"id": "u1", "email": "u@example.com"},
        payment_method_nonce="nonce-2",
    )
    assert sub["id"] in update_pm["subscriptions_updated"]

    changed = await change_subscription_plan(
        db,
        gateway,
        {"id": "u1"},
        subscription_id=sub["id"],
        new_price_id="price_pro_monthly",
    )
    assert changed["subscription"]["price_id"] == "price_pro_monthly"

    overview = await billing_overview(db, {"id": "u1"})
    assert overview["customer"]["braintree_customer_id"] == "bt_cust_1"
    assert overview["default_payment_method"]["last4"] == "1111"
    assert overview["active_subscriptions"]


@pytest.mark.asyncio
async def test_webhook_processing_is_idempotent(monkeypatch):
    monkeypatch.setenv("BRAINTREE_PLAN_BUILDER_MONTHLY", "bt_builder_monthly")
    db = Db()
    await db.users.insert_one({"id": "u1", "email": "u@example.com"})
    created = await create_subscription_checkout(
        db,
        Gateway(),
        {"id": "u1", "email": "u@example.com"},
        product_id=None,
        price_id="price_builder_monthly",
        payment_method_nonce="nonce",
    )
    sub = created["subscription"]
    notification = Obj(
        kind="subscription_charged_successfully",
        subscription=Obj(
            id=sub["braintree_subscription_id"],
            status="Active",
            billing_period_end_date="2026-06-27",
            transactions=[Obj(id="renewal_txn_1", status="submitted_for_settlement", amount="15.00", currency_iso_code="USD")],
        ),
    )

    first = await process_webhook(db, notification, signature="sig", payload="payload")
    second = await process_webhook(db, notification, signature="sig", payload="payload")

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"
    renewal_orders = [row for row in db.orders.rows if row.get("braintree_transaction_id") == "renewal_txn_1"]
    assert len(renewal_orders) == 1

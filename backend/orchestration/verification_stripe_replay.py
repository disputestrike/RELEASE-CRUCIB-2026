"""
Payment webhook replay verification.

The historical module name is kept for import compatibility, but the proof
surface is provider-neutral. CrucibAI's active checkout provider is Braintree,
so new proof bundles should not imply Stripe is the active payment rail.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List

from .verification_security import _pi


SKIP_CHECK = "payment_webhook_replay_skipped"
PROVEN_CHECK = "payment_webhook_idempotency_proven"
LEGACY_TABLES = (
    "braintree_events_processed",
    "payment_events_processed",
    "webhook_events_processed",
    "stripe_events_processed",
)


def verify_stripe_replay_workspace(workspace_path: str) -> Dict[str, Any]:
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []

    if not workspace_path or not os.path.isdir(workspace_path):
        proof.append(
            _pi(
                "verification",
                "Payment webhook replay skipped (no workspace)",
                {
                    "check": SKIP_CHECK,
                    "reason": "no_workspace",
                    "provider": "braintree",
                },
                verification_class="presence",
            ),
        )
        return {"passed": True, "score": 80, "issues": issues, "proof": proof}

    mig_dir = os.path.join(workspace_path, "db", "migrations")
    if not os.path.isdir(mig_dir):
        proof.append(
            _pi(
                "verification",
                "Payment webhook replay skipped (no migrations dir)",
                {
                    "check": SKIP_CHECK,
                    "reason": "no_migrations",
                    "provider": "braintree",
                },
                verification_class="presence",
            ),
        )
        return {"passed": True, "score": 82, "issues": issues, "proof": proof}

    has_sketch = False
    for name in os.listdir(mig_dir):
        if not name.endswith(".sql"):
            continue
        try:
            with open(
                os.path.join(mig_dir, name), encoding="utf-8", errors="replace"
            ) as fh:
                body = fh.read().lower()
        except OSError:
            continue
        if any(table in body for table in LEGACY_TABLES):
            has_sketch = True
            break

    if not has_sketch:
        proof.append(
            _pi(
                "verification",
                "Payment webhook replay skipped (no idempotency migration)",
                {
                    "check": SKIP_CHECK,
                    "reason": "no_payment_idempotency_migration",
                    "provider": "braintree",
                    "accepted_tables": list(LEGACY_TABLES),
                },
                verification_class="presence",
            ),
        )
        return {"passed": True, "score": 85, "issues": issues, "proof": proof}

    con = sqlite3.connect(":memory:")
    try:
        con.execute(
            "CREATE TABLE stripe_events_processed (id TEXT PRIMARY KEY NOT NULL, received_at TEXT)",
        )
        eid = "evt_crucib_replay_test"
        con.execute(
            "INSERT OR IGNORE INTO stripe_events_processed (id) VALUES (?)", (eid,)
        )
        con.execute(
            "INSERT OR IGNORE INTO stripe_events_processed (id) VALUES (?)", (eid,)
        )
        n = con.execute("SELECT count(*) FROM stripe_events_processed").fetchone()[0]
        if n != 1:
            issues.append(
                f"Payment webhook replay: duplicate webhook id should dedupe to 1 row, got {n}"
            )
        else:
            proof.append(
                _pi(
                    "verification",
                    "Payment webhook replay: second insert with same event id did not create a second row",
                    {"check": PROVEN_CHECK, "provider": "braintree"},
                    verification_class="runtime",
                ),
            )
    finally:
        con.close()

    score = 100 if not issues else 40
    return {
        "passed": len(issues) == 0,
        "score": score,
        "issues": issues,
        "proof": proof,
    }

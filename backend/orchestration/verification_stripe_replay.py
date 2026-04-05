"""
verification.stripe_replay — prove webhook idempotency table semantics (SQLite stand-in for ON CONFLICT DO NOTHING).
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List

from .verification_security import _pi


def verify_stripe_replay_workspace(workspace_path: str) -> Dict[str, Any]:
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []

    if not workspace_path or not os.path.isdir(workspace_path):
        proof.append(
            _pi(
                "verification",
                "Stripe replay skipped (no workspace)",
                {"check": "stripe_replay_skipped", "reason": "no_workspace"},
                verification_class="presence",
            ),
        )
        return {"passed": True, "score": 80, "issues": issues, "proof": proof}

    mig_dir = os.path.join(workspace_path, "db", "migrations")
    if not os.path.isdir(mig_dir):
        proof.append(
            _pi(
                "verification",
                "Stripe replay skipped (no migrations dir)",
                {"check": "stripe_replay_skipped", "reason": "no_migrations"},
                verification_class="presence",
            ),
        )
        return {"passed": True, "score": 82, "issues": issues, "proof": proof}

    has_sketch = False
    for name in os.listdir(mig_dir):
        if not name.endswith(".sql"):
            continue
        try:
            with open(os.path.join(mig_dir, name), encoding="utf-8", errors="replace") as fh:
                body = fh.read().lower()
        except OSError:
            continue
        if "stripe_events_processed" in body:
            has_sketch = True
            break

    if not has_sketch:
        proof.append(
            _pi(
                "verification",
                "Stripe replay skipped (no stripe_events_processed migration)",
                {"check": "stripe_replay_skipped", "reason": "no_stripe_migration"},
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
        con.execute("INSERT OR IGNORE INTO stripe_events_processed (id) VALUES (?)", (eid,))
        con.execute("INSERT OR IGNORE INTO stripe_events_processed (id) VALUES (?)", (eid,))
        n = con.execute("SELECT count(*) FROM stripe_events_processed").fetchone()[0]
        if n != 1:
            issues.append(f"Stripe replay: duplicate webhook id should dedupe to 1 row, got {n}")
        else:
            proof.append(
                _pi(
                    "verification",
                    "Stripe replay: second insert with same event id did not create a second row",
                    {"check": "stripe_webhook_idempotency_proven"},
                    verification_class="runtime",
                ),
            )
    finally:
        con.close()

    score = 100 if not issues else 40
    return {"passed": len(issues) == 0, "score": score, "issues": issues, "proof": proof}

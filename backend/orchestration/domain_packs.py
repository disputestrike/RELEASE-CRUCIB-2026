"""
Domain intent from user goal — drives optional SQL/API sketches (not full codegen).
"""

from __future__ import annotations

import re
from typing import Any, Dict


def _g(job_or_goal: Any) -> str:
    if isinstance(job_or_goal, str):
        return (job_or_goal or "").lower()
    return (job_or_goal.get("goal") or "").lower()


def multitenant_intent(job_or_goal: Dict[str, Any] | str) -> bool:
    g = _g(job_or_goal)
    return bool(
        re.search(
            r"\b(multi[\s-]?tenant|multitenant|tenant isolation|row[\s-]?level|rls|saas platform)\b",
            g,
        )
    )


def payment_intent(job_or_goal: Dict[str, Any] | str) -> bool:
    g = _g(job_or_goal)
    return bool(re.search(r"\b(paypal|checkout|subscription|billing webhook|payments?)\b", g))


from .multiregion_terraform_sketch import multiregion_terraform_intent
from .observability_workspace_pack import observability_intent


def fintech_intent(job_or_goal: Dict[str, Any] | str) -> bool:
    """Payments, lending, banking, wallets — drives fintech schema / compliance sketch hooks."""
    g = _g(job_or_goal)
    return bool(
        re.search(
            r"\b(fintech|neobank|banking|lending|underwriting|kyc|aml|ledger|"
            r"payment processor|wallet|treasury|forex|remittance)\b",
            g,
        )
    )


def healthcare_intent(job_or_goal: Dict[str, Any] | str) -> bool:
    """Clinical / PHI-adjacent products — drives HIPAA-oriented checklist + schema hints."""
    g = _g(job_or_goal)
    return bool(
        re.search(
            r"\b(healthcare|ehr|emr|telehealth|clinical|phi\b|hipaa|"
            r"patient portal|prior auth|claims)\b",
            g,
        )
    )


def marketplace_intent(job_or_goal: Dict[str, Any] | str) -> bool:
    """Multi-sided listings, orders, payouts — marketplace schema pack."""
    g = _g(job_or_goal)
    return bool(
        re.search(
            r"\b(marketplace|multi[\s-]?vendor|buyer|seller|listing|"
            r"escrow|payout|commission|cart|checkout)\b",
            g,
        )
    )


# Pre-verified vertical schema notes + minimal DDL sketches (expand per product).
VERTICAL_SCHEMA_PACKS: Dict[str, Dict[str, str]] = {
    "fintech": {
        "summary": "Accounts, ledger entries, idempotent payment events, audit trail.",
        "ddl_stub": (
            "-- accounts(id, org_id, currency), ledger_lines(id, account_id, amount_cents, idem_key UNIQUE), "
            "payment_events(id, provider_ref UNIQUE, status)"
        ),
    },
    "healthcare": {
        "summary": "Patient pseudonym IDs, encounters, consent records, access audit.",
        "ddl_stub": (
            "-- patients(id, external_ref_hash), encounters(id, patient_id, started_at), "
            "consents(id, patient_id, purpose, recorded_at), phi_access_log(id, actor_id, patient_id, action)"
        ),
    },
    "marketplace": {
        "summary": "Sellers, listings, carts, orders, payouts, disputes.",
        "ddl_stub": (
            "-- sellers(id, user_id), listings(id, seller_id, status), orders(id, buyer_id, total_cents), "
            "order_items(id, order_id, listing_id), payouts(id, seller_id, idem_key UNIQUE)"
        ),
    },
}


def compliance_regulated_intent(job_or_goal: Dict[str, Any] | str) -> bool:
    """
    Goals that imply regulated data, healthcare, or financial compliance — triggers checklist artifact only.
    """
    g = _g(job_or_goal)
    return bool(
        re.search(
            r"\b(fintech|pci[\s-]?dss|pci\b|hipaa|soc\s*2|soc2|gdpr|glba|"
            r"regulated|financial services|healthcare|phi\b|banking|lending|insurtech)\b",
            g,
        )
    )

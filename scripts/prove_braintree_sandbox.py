#!/usr/bin/env python3
"""Run a real Braintree sandbox transaction when credentials are present.

Without credentials this exits successfully in skipped mode so CI can prove the
hook exists. Use ``--require-live`` in release verification to fail unless a real
sandbox transaction is executed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED = (
    "BRAINTREE_MERCHANT_ID",
    "BRAINTREE_PUBLIC_KEY",
    "BRAINTREE_PRIVATE_KEY",
)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, val in value.items():
            if "key" in key.lower() or "secret" in key.lower() or "private" in key.lower():
                out[key] = "<redacted>"
            else:
                out[key] = redact(val)
        return out
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def emit(payload: Dict[str, Any], report_path: str = "") -> None:
    safe = redact(payload)
    print(json.dumps(safe, indent=2, sort_keys=True))
    if report_path:
        path = Path(report_path)
        if not path.is_absolute():
            path = ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(safe, indent=2, sort_keys=True), encoding="utf-8")


def missing_env() -> list[str]:
    missing = [key for key in REQUIRED if not os.environ.get(key)]
    if not os.environ.get("BRAINTREE_MERCHANT_ACCOUNT_ID"):
        missing.append("BRAINTREE_MERCHANT_ACCOUNT_ID")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amount", default="1.00")
    parser.add_argument("--nonce", default="fake-valid-nonce")
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument("--allow-production", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    missing = missing_env()
    env_name = (os.environ.get("BRAINTREE_ENVIRONMENT") or "sandbox").lower()
    if missing:
        payload = {
            "status": "skipped_missing_credentials",
            "required_live": args.require_live,
            "environment": env_name,
            "missing": missing,
            "message": "Set Braintree sandbox credentials and rerun with --require-live to execute a real transaction proof.",
        }
        emit(payload, args.report_path)
        return 2 if args.require_live else 0

    if env_name == "production" and not args.allow_production:
        payload = {
            "status": "blocked_production_environment",
            "environment": env_name,
            "message": "Sandbox proof refuses production credentials unless --allow-production is supplied.",
        }
        emit(payload, args.report_path)
        return 2

    try:
        from backend.services.braintree_billing import make_gateway

        gateway = make_gateway()
        payload: Dict[str, Any] = {
            "amount": args.amount,
            "payment_method_nonce": args.nonce,
            "options": {"submit_for_settlement": True},
            "order_id": f"crucibai-proof-{int(time.time())}",
        }
        merchant_account_id = os.environ.get("BRAINTREE_MERCHANT_ACCOUNT_ID")
        if merchant_account_id:
            payload["merchant_account_id"] = merchant_account_id
        result = gateway.transaction.sale(payload)
        tx = getattr(result, "transaction", None)
        success = bool(getattr(result, "is_success", False))
        proof = {
            "status": "live_pass" if success else "live_fail",
            "environment": env_name,
            "transaction": {
                "id": getattr(tx, "id", None),
                "status": getattr(tx, "status", None),
                "amount": str(getattr(tx, "amount", args.amount)),
                "currency_iso_code": getattr(tx, "currency_iso_code", None),
            },
            "errors": str(getattr(result, "errors", "") or ""),
            "message": "Braintree sandbox transaction executed.",
        }
        emit(proof, args.report_path)
        return 0 if success else 1
    except Exception as exc:
        emit({"status": "live_exception", "environment": env_name, "error": repr(exc)}, args.report_path)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

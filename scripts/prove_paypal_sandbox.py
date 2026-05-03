from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="PayPal sandbox readiness proof")
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    required = ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"]
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    payload = {
        "provider": "paypal",
        "mode": os.environ.get("PAYPAL_MODE", "sandbox"),
        "configured": not missing,
        "missing": missing,
        "required_live": bool(args.require_live),
    }
    if missing:
        payload["status"] = "missing_credentials" if args.require_live else "skipped_missing_credentials"
        output = json.dumps(payload, sort_keys=True)
        if args.report_path:
            path = Path(args.report_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output + "\n", encoding="utf-8")
        print(output)
        return 2 if args.require_live else 0

    payload["status"] = "configured"
    output = json.dumps(payload, sort_keys=True)
    if args.report_path:
        path = Path(args.report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

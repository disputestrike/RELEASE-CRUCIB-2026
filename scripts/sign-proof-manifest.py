#!/usr/bin/env python
"""Create a signed proof manifest for an output directory."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.proof_manifest import build_signed_manifest_for_directory  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create signed proof manifest for a benchmark/report directory.")
    parser.add_argument("--input-dir", required=True, help="Directory containing proof artifacts")
    parser.add_argument("--output-file", default="proof_manifest.json", help="Manifest filename written under input-dir")
    parser.add_argument("--project-id", default="benchmark-project")
    parser.add_argument("--run-id", default=None, help="Defaults to input-dir name")
    parser.add_argument("--manifest-id", default=None)
    parser.add_argument("--secret-env", default="CRUCIB_PROOF_HMAC_SECRET")
    args = parser.parse_args(argv)

    input_dir = Path(args.input_dir).resolve()
    if not input_dir.is_dir():
        print(json.dumps({"ok": False, "error": f"input_dir_not_found: {input_dir}"}, indent=2))
        return 2

    secret = (os.environ.get(args.secret_env) or "").strip()
    if not secret:
        print(json.dumps({"ok": False, "error": f"missing_secret_env:{args.secret_env}"}, indent=2))
        return 2

    run_id = (args.run_id or input_dir.name).strip()
    manifest_id = (args.manifest_id or f"{run_id}-{int(time.time())}").strip()
    output_name = Path(args.output_file).name

    manifest = build_signed_manifest_for_directory(
        directory=input_dir,
        secret=secret,
        manifest_id=manifest_id,
        project_id=str(args.project_id),
        run_id=run_id,
        metadata={"source": "scripts/sign-proof-manifest.py"},
        exclude_names={output_name},
    )

    target = input_dir / output_name
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "manifest_path": str(target),
                "manifest_id": manifest.get("manifest_id"),
                "payload_sha256": manifest.get("payload_sha256"),
                "artifact_count": len(manifest.get("artifacts") or []),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

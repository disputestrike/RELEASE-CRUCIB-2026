#!/usr/bin/env python3
"""Pre-push local evidence gate: invokes run_local_evidence_pack.py with --strict."""
import subprocess
import sys
from pathlib import Path


def main() -> int:
    script = Path(__file__).resolve().parent / "run_local_evidence_pack.py"
    cmd = [sys.executable, str(script), "--strict", *sys.argv[1:]]
    return int(subprocess.call(cmd))


if __name__ == "__main__":
    raise SystemExit(main())

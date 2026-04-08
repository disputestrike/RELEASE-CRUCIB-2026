#!/usr/bin/env python
"""CLI wrapper for the CrucibAI repeatability benchmark."""
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from benchmarks.repeatability_scorecard import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

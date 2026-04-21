"""Write proof/CONTINUATION_BLUEPRINT.md when a job cannot complete successfully."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def write_continuation_blueprint(
    workspace_path: str,
    *,
    job_id: str,
    goal: str,
    reason: str,
    failed_step_keys: Optional[List[str]] = None,
    open_gates: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> bool:
    if not workspace_path or not os.path.isdir(workspace_path):
        return False
    proof_dir = os.path.join(workspace_path, "proof")
    os.makedirs(proof_dir, exist_ok=True)
    path = os.path.join(proof_dir, "CONTINUATION_BLUEPRINT.md")
    ts = datetime.now(timezone.utc).isoformat()
    body = f"""# Continuation blueprint

Generated: `{ts}`
Job id: `{job_id}`

## Status

**Reason run did not fully complete:** {reason}

## Goal (reference)

```
{(goal or "").strip()[:8000]}
```

## What to do next

1. Fix blockers listed below (implementation, verification, or environment).
2. Re-run from workspace (Resume) or start a new plan with a **Continuation** block in the UI describing deltas.
3. Re-check `proof/DELIVERY_CLASSIFICATION.md` and `proof/ELITE_EXECUTION_DIRECTIVE.md`.

## Failed or blocked steps

{chr(10).join(f"- {x}" for x in failed_step_keys) if failed_step_keys else "- (none listed)"}

## Open gates / verification

{chr(10).join(f"- {x}" for x in open_gates) if open_gates else "- (see job events and proof panel)"}

## Operator notes

{notes or "None."}

## Suggested commands (adjust for your OS)

```bash
# From job workspace root
cd <workspace>
# Run compile gate locally
npm run build
# Or Python checks
python -m compileall backend
```
"""
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return True
    except OSError:
        return False

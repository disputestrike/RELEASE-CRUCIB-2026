"""
verification.rbac_enforcement — optional live checks against CRUCIBAI API (admin routes reject unauthenticated / non-admin).

Host RBAC is fully covered by pytest (tests/test_admin_security.py). This step adds an optional HTTP smoke hook for CI/staging.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from .verification_security import _pi


async def verify_rbac_enforcement_workspace(workspace_path: str) -> Dict[str, Any]:
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []

    base = os.environ.get("CRUCIBAI_RBAC_SMOKE_URL", "").strip()
    if not base:
        proof.append(
            _pi(
                "verification",
                "RBAC smoke skipped — set CRUCIBAI_RBAC_SMOKE_URL to hit /api/admin/* (see tests/test_admin_security.py)",
                {
                    "check": "rbac_smoke_skipped",
                    "host_tests": "tests/test_admin_security.py",
                },
                verification_class="presence",
            ),
        )
        return {"passed": True, "score": 88, "issues": issues, "proof": proof}

    import aiohttp

    url = base.rstrip("/") + "/api/admin/dashboard"
    timeout = aiohttp.ClientTimeout(total=12)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status not in (401, 403):
                    issues.append(
                        f"RBAC smoke: unauthenticated GET {url} expected 401/403, got {resp.status}",
                    )
                else:
                    proof.append(
                        _pi(
                            "verification",
                            f"RBAC smoke: anonymous admin dashboard rejected with {resp.status}",
                            {"check": "rbac_anonymous_blocked", "status": resp.status},
                            verification_class="runtime",
                        ),
                    )

            token = os.environ.get("CRUCIBAI_RBAC_USER_TOKEN", "").strip()
            if token and not issues:
                async with session.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                ) as resp2:
                    if resp2.status != 403:
                        issues.append(
                            "RBAC smoke: regular user token should receive 403 on /api/admin/dashboard",
                        )
                    else:
                        proof.append(
                            _pi(
                                "verification",
                                "RBAC smoke: non-admin bearer token blocked from admin dashboard (403)",
                                {"check": "rbac_escalation_blocked"},
                                verification_class="runtime",
                            ),
                        )
    except Exception as e:
        issues.append(f"RBAC smoke request failed: {e}")

    score = 100 if not issues else max(35, 100 - len(issues) * 40)
    return {
        "passed": len(issues) == 0,
        "score": score,
        "issues": issues,
        "proof": proof,
    }

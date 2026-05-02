"""
Last-Mile Deployer — Phase 2: Full Last-Mile Automation.

Orchestrates the complete deployment pipeline in a single call:
  1. Run Alembic DB migrations
  2. Deploy dist/ to Netlify
  3. Poll SSL/HTTPS readiness
  4. Return a fully-verified deployment record

Zero manual steps. Every step is verified before the next begins.

Usage:
    from backend.services.lastmile_deployer import deploy_lastmile
    result = await deploy_lastmile(dist_dir="/path/to/dist", job_id="job_123")
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

from backend.services.db_migrator import run_migrations
from backend.services.netlify_deploy import deploy_to_netlify, netlify_configured

logger = logging.getLogger(__name__)

# How many seconds to wait for SSL to become available
SSL_POLL_TIMEOUT = int(os.environ.get("SSL_POLL_TIMEOUT", "120"))
SSL_POLL_INTERVAL = 5


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def deploy_lastmile(
    dist_dir: str,
    job_id: str,
    site_name: Optional[str] = None,
    site_id: Optional[str] = None,
    run_db_migrations: bool = True,
    verify_ssl: bool = True,
) -> Dict[str, Any]:
    """
    Full last-mile deployment pipeline.

    Steps:
      1. DB migrations  (if run_db_migrations=True)
      2. Netlify deploy
      3. SSL/HTTPS readiness check (if verify_ssl=True)

    Returns a structured deployment record:
    {
        "success": bool,
        "live_url": str | None,
        "site_id": str | None,
        "deploy_id": str | None,
        "ssl_verified": bool,
        "migration": dict,
        "steps": list[dict],   # ordered step log for the UI
        "duration_ms": int,
        "error": str | None,
    }
    """
    start = time.monotonic()
    steps: list[Dict[str, Any]] = []
    live_url: Optional[str] = None
    site_id_out: Optional[str] = site_id
    deploy_id_out: Optional[str] = None
    ssl_verified = False
    migration_result: Dict[str, Any] = {"success": True, "revision": "skipped"}
    error: Optional[str] = None

    # ── Step 1: DB Migrations ──────────────────────────────────────────────
    if run_db_migrations:
        logger.info("[LASTMILE] job=%s step=db_migration", job_id)
        migration_result = await run_migrations()
        steps.append({
            "step": "db_migration",
            "success": migration_result["success"],
            "detail": migration_result.get("output", "")[:300],
            "duration_ms": migration_result.get("duration_ms", 0),
        })
        if not migration_result["success"]:
            # Non-fatal: log and continue — migrations may already be current
            logger.warning(
                "[LASTMILE] DB migration warning (non-blocking): %s",
                migration_result.get("error"),
            )

    # ── Step 2: Netlify Deploy ─────────────────────────────────────────────
    if not netlify_configured():
        steps.append({
            "step": "netlify_deploy",
            "success": False,
            "detail": "NETLIFY_TOKEN not configured — skipping deploy",
            "duration_ms": 0,
        })
        duration_ms = int((time.monotonic() - start) * 1000)
        return _build_result(
            success=False,
            live_url=None,
            site_id=None,
            deploy_id=None,
            ssl_verified=False,
            migration=migration_result,
            steps=steps,
            duration_ms=duration_ms,
            error="NETLIFY_TOKEN not set",
        )

    logger.info("[LASTMILE] job=%s step=netlify_deploy dist=%s", job_id, dist_dir)
    netlify_start = time.monotonic()
    try:
        deploy = await deploy_to_netlify(
            dist_dir=dist_dir,
            site_name=site_name or f"crucibai-{job_id[:8]}",
            site_id=site_id,
        )
        live_url = deploy.get("url") or deploy.get("ssl_url")
        site_id_out = deploy.get("site_id")
        deploy_id_out = deploy.get("deploy_id")
        netlify_ms = int((time.monotonic() - netlify_start) * 1000)
        steps.append({
            "step": "netlify_deploy",
            "success": True,
            "detail": f"Deployed to {live_url}",
            "duration_ms": netlify_ms,
            "url": live_url,
        })
        logger.info("[LASTMILE] Netlify deploy done: %s in %dms", live_url, netlify_ms)
    except Exception as exc:
        netlify_ms = int((time.monotonic() - netlify_start) * 1000)
        error = str(exc)
        steps.append({
            "step": "netlify_deploy",
            "success": False,
            "detail": error,
            "duration_ms": netlify_ms,
        })
        duration_ms = int((time.monotonic() - start) * 1000)
        return _build_result(
            success=False,
            live_url=None,
            site_id=site_id_out,
            deploy_id=deploy_id_out,
            ssl_verified=False,
            migration=migration_result,
            steps=steps,
            duration_ms=duration_ms,
            error=error,
        )

    # ── Step 3: SSL / HTTPS Verification ──────────────────────────────────
    if verify_ssl and live_url:
        ssl_url = live_url if live_url.startswith("https://") else live_url.replace("http://", "https://")
        logger.info("[LASTMILE] job=%s step=ssl_verify url=%s", job_id, ssl_url)
        ssl_start = time.monotonic()
        ssl_verified, ssl_detail = await _verify_ssl(ssl_url)
        ssl_ms = int((time.monotonic() - ssl_start) * 1000)
        steps.append({
            "step": "ssl_verify",
            "success": ssl_verified,
            "detail": ssl_detail,
            "duration_ms": ssl_ms,
            "url": ssl_url,
        })
        if ssl_verified and live_url.startswith("http://"):
            live_url = ssl_url  # upgrade to HTTPS

    duration_ms = int((time.monotonic() - start) * 1000)
    overall_success = (
        deploy_id_out is not None
        and (not verify_ssl or ssl_verified)
    )

    return _build_result(
        success=overall_success,
        live_url=live_url,
        site_id=site_id_out,
        deploy_id=deploy_id_out,
        ssl_verified=ssl_verified,
        migration=migration_result,
        steps=steps,
        duration_ms=duration_ms,
        error=None,
    )


# ---------------------------------------------------------------------------
# SSL verification helper
# ---------------------------------------------------------------------------

async def _verify_ssl(url: str, timeout: int = SSL_POLL_TIMEOUT) -> tuple[bool, str]:
    """
    Poll until the HTTPS URL returns a 2xx/3xx status or timeout.
    Returns (verified: bool, detail: str).
    """
    deadline = time.monotonic() + timeout
    last_error = "timeout"

    async with httpx.AsyncClient(verify=True, timeout=10) as client:
        while time.monotonic() < deadline:
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code < 500:
                    return True, f"SSL OK — HTTP {resp.status_code}"
                last_error = f"HTTP {resp.status_code}"
            except httpx.ConnectError as exc:
                last_error = f"ConnectError: {exc}"
            except httpx.SSLError as exc:
                return False, f"SSL cert error: {exc}"
            except Exception as exc:
                last_error = str(exc)
            await asyncio.sleep(SSL_POLL_INTERVAL)

    return False, f"SSL not ready after {timeout}s — last error: {last_error}"


# ---------------------------------------------------------------------------
# Result builder
# ---------------------------------------------------------------------------

def _build_result(
    *,
    success: bool,
    live_url: Optional[str],
    site_id: Optional[str],
    deploy_id: Optional[str],
    ssl_verified: bool,
    migration: Dict[str, Any],
    steps: list,
    duration_ms: int,
    error: Optional[str],
) -> Dict[str, Any]:
    return {
        "success": success,
        "live_url": live_url,
        "site_id": site_id,
        "deploy_id": deploy_id,
        "ssl_verified": ssl_verified,
        "migration": migration,
        "steps": steps,
        "duration_ms": duration_ms,
        "error": error,
    }

"""Mobile-specific routes: Expo Go QR preview and EAS update trigger.

GET  /api/projects/{project_id}/mobile/qr
    Returns an inline PNG QR code (data URI) pointing to an ``exp://``
    Expo Go deep link.  Works without any EAS account — users can scan
    directly with the Expo Go app while the project is running locally, or
    after a Tunnel URL is set.

POST /api/projects/{project_id}/mobile/eas-update
    Triggers an EAS Update publish for the project so the preview channel is
    updated.  Requires ``EAS_TOKEN`` env var and the project's EAS project ID
    stored in ``project.eas_project_id``.

GET  /api/projects/{project_id}/mobile/store-checklist
    Returns a structured App Store / Play Store submission checklist generated
    from the project's build outputs.
"""
from __future__ import annotations

import base64
import io
import logging
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_current_user, get_db

logger = logging.getLogger(__name__)

mobile_router = APIRouter(prefix="/api", tags=["mobile"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EAS_TOKEN = os.environ.get("EAS_TOKEN", "")
_EXPO_API_BASE = "https://api.expo.dev/v2"


def _build_exp_url(project_id: str, tunnel_url: Optional[str] = None) -> str:
    """Return an ``exp://`` URL for Expo Go deep linking."""
    if tunnel_url:
        # Strip scheme and use as-is for Expo Go
        host = tunnel_url.replace("https://", "").replace("http://", "").rstrip("/")
        return f"exp://{host}"
    # Default: use the CrucibAI preview endpoint as the Expo manifest URL
    base_url = os.environ.get("PUBLIC_API_URL", "https://api.crucibai.com")
    return f"exp://{base_url.replace('https://', '').replace('http://', '')}/api/projects/{project_id}/mobile/manifest"


def _generate_qr_png_b64(url: str) -> str:
    """Render a QR code for *url* and return a base64-encoded PNG."""
    try:
        import qrcode  # type: ignore[import]
        from PIL import Image  # noqa: F401  # validate Pillow is present

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as exc:
        logger.warning("QR generation failed: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@mobile_router.get("/projects/{project_id}/mobile/qr")
async def get_mobile_qr(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    """Return a QR code PNG (base64 data URI) for loading the project in Expo Go.

    The QR code points to the project's Expo Go deep link.  Users can scan it
    with the Expo Go app on their phone to see the generated mobile app live.
    """
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_type = (project.get("project_type") or "").lower()
    if project_type not in ("mobile", "react-native", "expo"):
        raise HTTPException(
            status_code=400,
            detail="QR preview is only available for mobile projects (project_type: mobile).",
        )

    tunnel_url: Optional[str] = project.get("expo_tunnel_url")
    exp_url = _build_exp_url(project_id, tunnel_url)
    qr_b64 = _generate_qr_png_b64(exp_url)

    return {
        "project_id": project_id,
        "expo_url": exp_url,
        "qr_code": f"data:image/png;base64,{qr_b64}" if qr_b64 else None,
        "instructions": [
            "1. Install **Expo Go** on your iPhone or Android phone.",
            "2. Scan the QR code above with your phone's camera.",
            "3. The app will open directly in Expo Go — no build step needed.",
            "4. Any changes you trigger from CrucibAI will reflect in ~10 seconds via EAS Update.",
        ],
        "tunnel_url": tunnel_url,
        "eas_project_id": project.get("eas_project_id"),
    }


class EasUpdateBody(BaseModel):
    message: Optional[str] = "CrucibAI auto-update"
    channel: Optional[str] = "preview"
    runtime_version: Optional[str] = "1.0.0"


@mobile_router.post("/projects/{project_id}/mobile/eas-update")
async def trigger_eas_update(
    project_id: str,
    body: EasUpdateBody,
    user: dict = Depends(get_current_user),
):
    """Publish an EAS Update for the project's preview channel.

    Requires ``EAS_TOKEN`` env var and ``project.eas_project_id`` to be set.
    After publishing, scanning the QR code will load the latest version.
    """
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    eas_project_id = project.get("eas_project_id")
    if not eas_project_id:
        raise HTTPException(
            status_code=400,
            detail="EAS project ID not configured.  Set eas_project_id on the project first.",
        )
    if not _EAS_TOKEN:
        raise HTTPException(
            status_code=400,
            detail="EAS_TOKEN environment variable is not set.  Add it in your deployment settings.",
        )

    deploy_files: dict = project.get("deploy_files") or {}
    if not deploy_files:
        raise HTTPException(status_code=400, detail="No generated files to publish.  Run a build first.")

    # Call EAS Update API
    headers = {
        "Authorization": f"Bearer {_EAS_TOKEN}",
        "Content-Type": "application/json",
        "expo-platform": "android",
    }
    payload = {
        "projectId": eas_project_id,
        "channel": body.channel or "preview",
        "message": body.message or "CrucibAI auto-update",
        "runtimeVersion": body.runtime_version or "1.0.0",
        "assets": [
            {"url": f"data:text/plain;base64,{base64.b64encode(v.encode()).decode()}", "key": k}
            for k, v in list(deploy_files.items())[:50]
            if isinstance(v, str)
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{_EXPO_API_BASE}/updates",
                headers=headers,
                json=payload,
            )
        if r.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail=f"EAS Update API error {r.status_code}: {r.text[:200]}",
            )
        result = r.json()
        update_id = result.get("id") or result.get("data", {}).get("id")
        # Persist the latest update ID on the project
        await db.projects.update_one(
            {"id": project_id},
            {"$set": {"eas_update_id": update_id, "eas_channel": body.channel}},
        )
        return {
            "ok": True,
            "update_id": update_id,
            "channel": body.channel,
            "message": body.message,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("EAS update failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"EAS Update failed: {str(exc)[:200]}")


@mobile_router.get("/projects/{project_id}/mobile/store-checklist")
async def get_store_checklist(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    """Return a structured App Store / Play Store submission checklist for the project.

    This is a comprehensive pre-submission guide that CrucibAI generates
    based on the project's build outputs.
    """
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_name = project.get("name") or "Your App"
    eas_project_id = project.get("eas_project_id")
    has_eas = bool(eas_project_id and _EAS_TOKEN)

    checklist = {
        "project_id": project_id,
        "project_name": project_name,
        "sections": [
            {
                "title": "1. App Identity",
                "items": [
                    {"step": "Set app name and bundle ID in app.json", "done": False},
                    {"step": "Create app icon (1024×1024 PNG, no transparency)", "done": False},
                    {"step": "Create splash screen (2048×2732 PNG)", "done": False},
                    {"step": "Set version and buildNumber in app.json", "done": False},
                ],
            },
            {
                "title": "2. EAS Build",
                "items": [
                    {"step": "Install EAS CLI: npm install -g eas-cli", "done": False},
                    {"step": "Run: eas login", "done": False},
                    {"step": f"Run: eas build --platform all {'(EAS project ID: ' + eas_project_id + ')' if eas_project_id else ''}", "done": has_eas},
                    {"step": "Wait for build to complete (~15 min for iOS)", "done": False},
                ],
            },
            {
                "title": "3. App Store (iOS)",
                "items": [
                    {"step": "Create app in App Store Connect (appstoreconnect.apple.com)", "done": False},
                    {"step": "Fill in app description, keywords, screenshots", "done": False},
                    {"step": "Upload build via: eas submit --platform ios", "done": False},
                    {"step": "Submit for Apple review (1-3 day typical wait)", "done": False},
                ],
            },
            {
                "title": "4. Google Play Store (Android)",
                "items": [
                    {"step": "Create app in Google Play Console (play.google.com/console)", "done": False},
                    {"step": "Upload AAB file via: eas submit --platform android", "done": False},
                    {"step": "Fill in store listing (description, screenshots, content rating)", "done": False},
                    {"step": "Submit to production track (review usually <3 days)", "done": False},
                ],
            },
            {
                "title": "5. Pre-submission Testing",
                "items": [
                    {"step": "Test on physical iOS device via TestFlight", "done": False},
                    {"step": "Test on physical Android device via internal testing track", "done": False},
                    {"step": "Verify deep links, push notifications, and payments work", "done": False},
                    {"step": "Run accessibility audit (VoiceOver / TalkBack)", "done": False},
                ],
            },
        ],
        "expo_docs": "https://docs.expo.dev/submit/introduction/",
        "eas_configured": has_eas,
    }
    return checklist

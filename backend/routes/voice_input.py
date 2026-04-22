"""CF27 — /api/voice endpoints for voice input mode.

Adapted from clawspring/voice/. Stub returns a placeholder transcription;
real STT wires in later via services/voice/stt_service.py.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/voice", tags=["voice"])

_TRANSCRIPTS: Dict[str, Dict[str, Any]] = {}


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    language: Optional[str] = Form("auto"),
):
    """Real speech-to-text via OpenAI Whisper when OPENAI_API_KEY is set.

    The original implementation returned placeholder text like
    "[voice capture 1234 bytes]"; this replaces it with an actual STT call
    using the user's existing OpenAI credentials. Falls back to a clear
    HTTP 503 with instructions when no STT provider is configured, so the
    frontend surfaces a useful error instead of pasting garbage into the
    prompt field.
    """
    import os as _os
    if audio.content_type and not audio.content_type.startswith(
        ("audio/", "application/octet-stream", "video/")
    ):
        raise HTTPException(
            status_code=415,
            detail=f"unsupported content-type: {audio.content_type}",
        )
    body = await audio.read()
    size = len(body)
    if size < 100:
        raise HTTPException(status_code=400, detail="audio clip too short")
    transcript_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    filename = audio.filename or "recording.webm"

    text: Optional[str] = None
    provider = None
    openai_key = _os.getenv("OPENAI_API_KEY") or _os.getenv("OPENAI_KEY")
    if openai_key:
        try:
            import httpx
            form = {
                "model": (None, "whisper-1"),
                "file": (filename, body, audio.content_type or "audio/webm"),
            }
            if language and language != "auto":
                form["language"] = (None, language)
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    files=form,
                )
            if resp.status_code == 200:
                data = resp.json()
                text = (data.get("text") or "").strip() or None
                provider = "openai-whisper"
            else:
                logger.warning(
                    "whisper STT failed: %s %s", resp.status_code, resp.text[:200]
                )
        except Exception as exc:
            logger.warning("whisper STT error: %s", exc)

    if text is None:
        # No provider wired (or the call failed). Tell the client explicitly
        # so the UI can show an actionable error instead of a placeholder.
        raise HTTPException(
            status_code=503,
            detail=(
                "Speech-to-text is not configured. Set OPENAI_API_KEY in the "
                "backend environment (used for Whisper) or wire another STT "
                "provider in backend/routes/voice_input.py."
            ),
        )

    _TRANSCRIPTS[transcript_id] = {
        "transcript_id": transcript_id,
        "session_id": session_id,
        "language": language,
        "bytes": size,
        "text": text,
        "provider": provider,
        "created_at": now,
    }
    return {
        "transcript_id": transcript_id,
        "text": text,
        "language": language,
        "duration_bytes": size,
        "provider": provider,
        "created_at": now,
    }


@router.get("/transcript/{transcript_id}")
def get_transcript(transcript_id: str):
    t = _TRANSCRIPTS.get(transcript_id)
    if not t:
        raise HTTPException(status_code=404, detail="transcript not found")
    return t


@router.get("/keyterms")
def keyterms():
    """Voice activation keyterms — words that trigger wake/stop."""
    return {"wake": ["crucib", "hey crucib"], "stop": ["stop", "cancel"], "run": ["go", "run", "execute"]}

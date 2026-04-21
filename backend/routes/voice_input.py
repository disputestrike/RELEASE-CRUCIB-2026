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
    if audio.content_type and not audio.content_type.startswith(("audio/", "application/octet-stream")):
        raise HTTPException(status_code=415, detail=f"unsupported content-type: {audio.content_type}")
    body = await audio.read()
    size = len(body)
    transcript_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    # Placeholder transcription — real implementation wires to an STT provider.
    text = f"[voice capture {size} bytes, lang={language}]"
    _TRANSCRIPTS[transcript_id] = {
        "transcript_id": transcript_id, "session_id": session_id,
        "language": language, "bytes": size, "text": text, "created_at": now,
    }
    return {"transcript_id": transcript_id, "text": text, "language": language, "duration_bytes": size, "created_at": now}


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

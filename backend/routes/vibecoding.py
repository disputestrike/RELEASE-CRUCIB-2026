"""Vibecoding routes — vibe analysis and code generation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["vibecoding"])


def _get_auth():
    from ..server import get_current_user

    return get_current_user


def _get_optional_user():
    from ..server import get_optional_user

    return get_optional_user


def _get_db():
    from .. import server

    return server.db


class VibeAnalyzeRequest(BaseModel):
    text: str
    context: Optional[str] = None


class VibeGenerateRequest(BaseModel):
    prompt: str
    language: Optional[str] = None
    framework: Optional[str] = None
    vibe_analysis: Optional[Dict[str, Any]] = None


class VibeAnalyzeAudioRequest(BaseModel):
    transcript: Optional[str] = (
        None  # if audio not provided, use transcript for vibe analysis
    )
    audio_base64: Optional[str] = None


class VibeDetectFrameworksRequest(BaseModel):
    text: Optional[str] = None
    project_id: Optional[str] = None


@router.post("/vibecoding/analyze")
async def vibecoding_analyze(body: VibeAnalyzeRequest):
    """Analyze natural language to detect vibe (style, frameworks, complexity)."""
    try:
        from ..vibe_analysis import vibe_analyzer

        vibe = vibe_analyzer.analyze(body.text)
        return {
            "status": "success",
            "vibe": vibe.to_dict(),
            "confidence": vibe.confidence_score,
        }
    except Exception as e:
        logger.warning("vibecoding_analyze failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vibecoding/generate")
async def vibecoding_generate(body: VibeGenerateRequest):
    """Generate code from prompt using vibe analysis."""
    try:
        from ..vibe_analysis import vibe_analyzer
        from ..vibe_code_generator import vibe_code_generator

        vibe_obj = vibe_analyzer.analyze(body.prompt)
        gen = vibe_code_generator.generate(vibe_obj, body.prompt, body.language)
        return {
            "status": "success",
            "language": gen.language,
            "framework": gen.framework,
            "code": gen.code,
            "style": gen.style,
            "structure": gen.structure,
            "explanation": gen.explanation,
        }
    except Exception as e:
        logger.warning("vibecoding_generate failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vibecoding/analyze-audio")
async def vibecoding_analyze_audio(body: VibeAnalyzeAudioRequest):
    """Analyze vibe from transcript or from audio (transcribe then analyze). When transcript provided, runs vibe analysis."""
    try:
        from ..vibe_analysis import vibe_analyzer

        text = body.transcript or ""
        if body.audio_base64 and not text:
            # Stub: no server-side transcription here; caller should use /voice/transcribe then pass transcript
            return {
                "status": "error",
                "detail": "Provide transcript or transcribe audio via /voice/transcribe first",
            }
        if not text:
            return {"status": "error", "detail": "transcript required"}
        vibe = vibe_analyzer.analyze(text)
        return {
            "status": "success",
            "vibe": vibe.to_dict(),
            "confidence": vibe.confidence_score,
        }
    except Exception as e:
        logger.warning("vibecoding_analyze_audio failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vibecoding/detect-frameworks")
async def vibecoding_detect_frameworks(
    body: VibeDetectFrameworksRequest, user: dict = Depends(_get_optional_user())
):
    """Detect frameworks and languages from text (or from project description when project_id given)."""
    try:
        from ..vibe_analysis import vibe_analyzer

        db = _get_db()
        text = body.text or ""
        if body.project_id and not text:
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            proj = await db.projects.find_one(
                {"id": body.project_id, "user_id": user["id"]},
                {"description": 1, "requirements": 1},
            )
            if not proj:
                raise HTTPException(status_code=404, detail="Project not found")
            if proj:
                req = proj.get("requirements") or {}
                text = (
                    req.get("prompt")
                    or req.get("description")
                    or proj.get("description")
                    or ""
                )
        if not text:
            return {"status": "success", "frameworks": [], "languages": []}
        vibe = vibe_analyzer.analyze(text)
        return {
            "status": "success",
            "frameworks": vibe.detected_frameworks,
            "languages": vibe.detected_languages,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("vibecoding_detect_frameworks failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

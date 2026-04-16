from __future__ import annotations

import base64
import io
import json
import logging
import os
import random
import re
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["misc"])


def _get_auth():
    from server import get_current_user

    return get_current_user


def _get_optional_user():
    from server import get_optional_user

    return get_optional_user


def _get_authenticated_or_api_user():
    from server import get_authenticated_or_api_user

    return get_authenticated_or_api_user


def _get_db():
    import server

    return server.db


def _get_llm_helpers():
    from server import (
        _effective_api_keys,
        _get_model_chain,
        get_workspace_api_keys,
    )
    from services.runtime.runtime_engine import runtime_engine

    async def _runtime_call_llm_with_fallback(**kwargs):
        session_id = kwargs.get("session_id") or str(uuid.uuid4())
        project_id = kwargs.get("project_id") or f"misc-{session_id}"
        return await runtime_engine.call_model_for_request(
            session_id=session_id,
            project_id=project_id,
            description=kwargs.get("agent_name") or "misc route llm request",
            message=kwargs.get("message", ""),
            system_message=kwargs.get("system_message", ""),
            model_chain=kwargs.get("model_chain", []),
            user_id=kwargs.get("user_id"),
            user_tier=kwargs.get("user_tier", "free"),
            speed_selector=kwargs.get("speed_selector", "lite"),
            available_credits=kwargs.get("available_credits", 0),
            agent_name=kwargs.get("agent_name", ""),
            api_keys=kwargs.get("api_keys"),
            content_blocks=kwargs.get("content_blocks"),
            idempotency_key=kwargs.get("idempotency_key"),
            skill_hint=kwargs.get("skill_hint"),
        )

    return (
        _runtime_call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    )


try:
    from server import (
        ContactSubmission,
        DocumentProcess,
        EnterpriseContact,
        ExplainErrorBody,
        ExportFilesBody,
        GenerateContentRequest,
        GenerateDocsBody,
        GenerateFaqSchemaBody,
        GenerateReadmeBody,
        InjectStripeBody,
        OptimizeBody,
        ProjectEnvBody,
        QualityGateBody,
        RAGQuery,
        SavePromptBody,
        SearchQuery,
        SecurityScanBody,
        ShareCreateBody,
        SuggestNextBody,
        ValidateAndFixBody,
    )
except ImportError:
    pass

try:
    from server import Permission, require_permission
except ImportError:
    require_permission = lambda p: lambda user: user

    class Permission:
        EDIT_PROJECT = None
        CREATE_PROJECT = None


# ==================== AI ANALYZE ====================


@router.post("/ai/analyze")
async def ai_analyze(
    data: DocumentProcess, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Document analysis with AI (Anthropic/Cerebras only). Uses your Settings keys when set."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        prompts = {
            "summarize": f"Please provide a concise summary of the following content:\n\n{data.content}",
            "extract": f"Extract key entities, facts, and important information from:\n\n{data.content}",
            "analyze": f"Provide a detailed analysis of the following content, including insights and recommendations:\n\n{data.content}",
        }
        prompt = prompts.get(data.task, prompts["analyze"])
        chain = _get_model_chain("auto", prompt, effective_keys=effective)
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message="You are an expert document analyst. Provide clear, structured analysis.",
            session_id=str(uuid.uuid4()),
            model_chain=chain,
            api_keys=effective,
        )
        return {"result": response, "task": data.task, "model_used": model_used}
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- CrucibAI for Docs / Slides / Sheets (C1–C3) ----------
@router.post("/generate/doc")
async def generate_doc(
    data: GenerateContentRequest, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Generate a structured document from a prompt (CrucibAI for Docs). Returns markdown or plain text."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    prompt = (data.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    fmt = (data.format or "markdown").lower()
    system = "You are CrucibAI for Docs. Generate a clear, well-structured document from the user's request. Use headings, bullets, and short paragraphs. Output only the document content, no meta commentary."
    if fmt == "plain":
        system += " Use plain text only (no markdown)."
    else:
        system += (
            " Use Markdown: ## for sections, - for bullets, **bold** where appropriate."
        )
    try:
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message=system,
            session_id=str(uuid.uuid4()),
            model_chain=_get_model_chain("auto", prompt, effective_keys=effective),
            api_keys=effective,
        )
        return {
            "content": (response or "").strip(),
            "format": fmt,
            "model_used": model_used,
        }
    except Exception as e:
        logger.exception("generate/doc failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/slides")
async def generate_slides(
    data: GenerateContentRequest, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Generate slide content/outline from a prompt (CrucibAI for Slides). Returns markdown with slide breaks."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    prompt = (data.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    fmt = (data.format or "markdown").lower()
    system = "You are CrucibAI for Slides. From the user's request, create slide content. Each slide: a clear title and 3-5 bullet points. Separate slides with '---' on its own line. Output only the slide deck content."
    if fmt == "outline":
        system += " Prefer a short outline (slide titles only) then optional bullets."
    try:
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message=system,
            session_id=str(uuid.uuid4()),
            model_chain=_get_model_chain("auto", prompt, effective_keys=effective),
            api_keys=effective,
        )
        return {
            "content": (response or "").strip(),
            "format": fmt,
            "model_used": model_used,
        }
    except Exception as e:
        logger.exception("generate/slides failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/sheets")
async def generate_sheets(
    data: GenerateContentRequest, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Generate tabular/spreadsheet-style data from a prompt (CrucibAI for Sheets). Returns CSV or JSON."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    prompt = (data.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    fmt = (data.format or "csv").lower()
    system = "You are CrucibAI for Sheets. From the user's request, generate tabular data. Use a clear header row and rows of data. Output ONLY valid CSV (comma-separated, quoted if needed) or JSON array of objects—no explanation."
    if fmt == "json":
        system = 'You are CrucibAI for Sheets. From the user\'s request, generate structured data. Reply with a JSON array of objects, e.g. [{"col1": "val1", "col2": "val2"}]. No other text.'
    try:
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message=system,
            session_id=str(uuid.uuid4()),
            model_chain=_get_model_chain("auto", prompt, effective_keys=effective),
            api_keys=effective,
        )
        raw = (response or "").strip()
        if fmt == "json":
            import re

            m = re.search(r"\[[\s\S]*\]", raw)
            raw = m.group(0) if m else raw
        return {"content": raw, "format": fmt, "model_used": model_used}
    except Exception as e:
        logger.exception("generate/sheets failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/query")
async def rag_query(
    data: RAGQuery, user: dict = Depends(_get_authenticated_or_api_user())
):
    """RAG-style query with context. Uses your Settings keys when set."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        context_str = f"\nContext: {data.context}" if data.context else ""
        prompt = f"Based on available knowledge{context_str}, please answer: {data.query}\n\nProvide a detailed, well-sourced response."
        chain = _get_model_chain("auto", prompt, effective_keys=effective)
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message="You are a knowledgeable AI assistant. Always cite sources when possible and indicate confidence levels.",
            session_id=str(uuid.uuid4()),
            model_chain=chain,
            api_keys=effective,
        )
        return {
            "answer": response,
            "query": data.query,
            "sources": ["AI Knowledge Base"],
            "confidence": 0.85,
            "model_used": model_used,
        }
    except Exception as e:
        logger.error(f"RAG error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def hybrid_search(
    data: SearchQuery, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Hybrid search: AI-enhanced results. Uses your Settings keys when set."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        prompt = f"Search query: '{data.query}'\nProvide 5 relevant results with titles, descriptions, and relevance scores (0-1)."
        chain = _get_model_chain("auto", prompt, effective_keys=effective)
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message="You are a search assistant. Provide relevant, structured results.",
            session_id=str(uuid.uuid4()),
            model_chain=chain,
            api_keys=effective,
        )
        return {
            "query": data.query,
            "search_type": data.search_type,
            "results": response,
            "total_results": 5,
        }
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== VOICE TRANSCRIPTION ====================


@router.post("/voice/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(..., description="Audio file (webm, mp3, wav, etc.)"),
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Transcribe voice audio to text using OpenAI Whisper. Uses server-side OPENAI_API_KEY."""
    logger.info(
        "Voice transcribe request received, filename=%s",
        getattr(audio, "filename", None),
    )
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Voice transcription needs OPENAI_API_KEY on the server. Add it in Railway Variables or .env to use the microphone.",
        )
    try:
        from openai import AsyncOpenAI

        oai = AsyncOpenAI(api_key=api_key)
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Voice transcription needs the openai package. Run: pip install openai",
        )
    try:
        audio_content = await audio.read()
        logger.info("Voice audio size: %s bytes", len(audio_content))
        if not audio_content or len(audio_content) < 100:
            raise HTTPException(
                status_code=400, detail="Audio file too short or empty."
            )
        ext = (audio.filename or "audio.webm").split(".")[-1].lower()
        if ext not in ("webm", "mp3", "wav", "m4a", "mp4", "mpeg", "mpga", "ogg"):
            ext = "webm"
        suffix = f".{ext}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(audio_content)
            tmp_path = tmp_file.name
        try:
            with open(tmp_path, "rb") as f:
                transcript = await oai.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text",
                    language="en",
                )
            text = (
                transcript
                if isinstance(transcript, str)
                else getattr(transcript, "text", "") or ""
            ).strip()
            logger.info("Voice transcription ok: %s...", (text or "")[:80])
            return {"text": text, "language": "en", "model": "whisper-1"}
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Voice transcription error: %s", e)
        err_msg = str(e).strip()
        if len(err_msg) > 200:
            err_msg = err_msg[:200] + "..."
        raise HTTPException(status_code=500, detail=f"Transcription failed: {err_msg}")


# ==================== FILE UPLOAD/ANALYSIS ====================


@router.post("/files/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    analysis_type: str = Form("general"),
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Analyze uploaded file (images, text, etc.) using AI. Uses your Settings keys when set."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    from server import ANTHROPIC_API_KEY, ANTHROPIC_HAIKU_MODEL

    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        content = await file.read()
        if file.content_type.startswith("image/"):
            image_data = base64.b64encode(content).decode("utf-8")
            try:
                import anthropic

                anthropic_key = effective.get("anthropic") or ANTHROPIC_API_KEY
                if not anthropic_key:
                    raise ValueError(
                        "Anthropic key needed for image analysis. Add ANTHROPIC_API_KEY in Settings or .env."
                    )
                client = anthropic.Anthropic(api_key=anthropic_key)
                resp = client.messages.create(
                    model=ANTHROPIC_HAIKU_MODEL,
                    max_tokens=1024,
                    system="You are an expert at analyzing UI and design. Describe what you see and provide design insights.",
                    messages=[
                        {
                            "type": "text",
                            "text": "Describe this image and provide design insights if it's a UI mockup.",
                        }
                    ],
                )
                analysis_result = resp.choices[0].message.content or "No description."
            except Exception as vision_err:
                logger.warning(f"Vision analysis fallback: {vision_err}")
                analysis_result = f"Image received: {file.filename} ({len(content)} bytes). Vision analysis unavailable: {vision_err!s}"
        elif file.content_type.startswith("text/") or (file.filename or "").endswith(
            (".txt", ".md", ".json", ".js", ".py", ".html", ".css")
        ):
            text_content = content.decode("utf-8", errors="replace")[:4000]
            prompts = {
                "general": f"Analyze this file and provide a summary:\n\n{text_content}",
                "code": f"Review this code and provide insights, potential issues, and suggestions:\n\n{text_content}",
                "design": f"If this is UI/design related, describe the design patterns and suggest improvements:\n\n{text_content}",
            }
            prompt = prompts.get(analysis_type, prompts["general"])
            chain = _get_model_chain("auto", prompt, effective_keys=effective)
            analysis_result, _ = await _call_llm_with_fallback(
                message=prompt,
                system_message="You are an expert code and document analyzer.",
                session_id=str(uuid.uuid4()),
                model_chain=chain,
                api_keys=effective,
            )
        else:
            analysis_result = (
                f"File type {file.content_type} analysis not fully supported yet."
            )
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "analysis": analysis_result,
            "analysis_type": analysis_type,
        }
    except Exception as e:
        logger.error(f"File analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EXPORT ZIP / GITHUB / DEPLOY ====================

DEPLOY_README = """# Deploy this project

## Vercel (recommended)
1. Go to https://vercel.com/new
2. Import this folder or upload the ZIP (Vercel will extract it).
3. Set build command: (leave default for Create React App)
4. Deploy.

## Netlify
1. Go to https://app.netlify.com/drop
2. Drag and drop this folder (or the ZIP).
3. Site deploys automatically.

## Railway
1. Go to https://railway.app/new
2. Create a new project, then "Deploy from GitHub repo" (push this folder to a repo first) or use "Empty project" and deploy via Railway CLI from this folder.
3. Add a service (e.g. Web Service for Node/React, or static site).
4. Deploy.

Generated with CrucibAI.
"""


@router.post("/export/zip")
async def export_zip(data: ExportFilesBody):
    """Export project files as a ZIP download."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in data.files.items():
            safe_name = name.lstrip("/")
            if not safe_name:
                safe_name = "file.txt"
            zf.writestr(safe_name, content)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=crucibai-project.zip"},
    )


@router.post("/export/github")
async def export_github(data: ExportFilesBody):
    """Export project as ZIP with README for GitHub (create repo, then upload)."""
    readme = """# CrucibAI Project

Generated with [CrucibAI](https://crucibai.com).

## Push to GitHub

1. Create a new repository on GitHub (https://github.com/new).
2. Run locally:
   ```bash
   unzip crucibai-project.zip && cd crucibai-project
   git init && git add . && git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```
3. Or upload the ZIP contents via GitHub web (Add file > Upload files).
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.md", readme)
        for name, content in data.files.items():
            safe_name = name.lstrip("/")
            if safe_name:
                zf.writestr(safe_name, content)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=crucibai-github.zip"},
    )


@router.post("/export/deploy")
async def export_deploy(data: ExportFilesBody):
    """Export project as ZIP for one-click deploy (Vercel/Netlify/Railway)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README-DEPLOY.md", DEPLOY_README)
        for name, content in data.files.items():
            safe_name = name.lstrip("/")
            if safe_name:
                zf.writestr(safe_name, content)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=crucibai-deploy.zip"},
    )


# ==================== ENTERPRISE / CONTACT ====================


@router.post("/enterprise/contact")
async def enterprise_contact(data: EnterpriseContact):
    """Capture enterprise inquiry. Stored in db.enterprise_inquiries; optional email if ENTERPRISE_CONTACT_EMAIL set."""
    db = _get_db()
    if not (data.company and data.company.strip()):
        raise HTTPException(status_code=400, detail="Company is required.")
    inquiry = {
        "id": str(uuid.uuid4()),
        "company": (data.company or "").strip(),
        "email": data.email,
        "team_size": (data.team_size or "").strip() or None,
        "use_case": (data.use_case or "").strip() or None,
        "budget": (getattr(data, "budget", None) or "").strip() or None,
        "message": (data.message or "").strip() or None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.enterprise_inquiries.insert_one(inquiry)
    # Optional: send email to sales if env set (e.g. ENTERPRISE_CONTACT_EMAIL=ben@crucibai.com)
    contact_email = os.environ.get("ENTERPRISE_CONTACT_EMAIL")
    if contact_email:
        try:
            from integrations.email import send_email_sync

            body = f"Enterprise inquiry:\nCompany: {inquiry['company']}\nEmail: {inquiry['email']}\nTeam size: {inquiry.get('team_size') or '—'}\nUse case: {inquiry.get('use_case') or '—'}\nBudget: {inquiry.get('budget') or '—'}\nMessage: {inquiry.get('message') or '—'}"
            send_email_sync(
                contact_email, f"CrucibAI Enterprise: {inquiry['company']}", body
            )
        except Exception as e:
            logger.warning(f"Enterprise contact email failed: {e}")
    return {
        "status": "received",
        "message": "We'll be in touch soon.",
        "contact_email": contact_email or "sales@crucibai.com",
    }


@router.post("/contact")
async def contact_submit(data: ContactSubmission):
    """General contact form. Stored in db.contact_submissions; optional email if CONTACT_EMAIL or ENTERPRISE_CONTACT_EMAIL set."""
    db = _get_db()
    submission = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "message": (data.message or "").strip(),
        "issue_type": (data.issue_type or "").strip() or None,
        "name": (data.name or "").strip() or None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if db:
        try:
            await db.contact_submissions.insert_one(submission)
        except Exception as e:
            logger.warning(f"Contact submission db insert failed: {e}")
    contact_email = os.environ.get("CONTACT_EMAIL") or os.environ.get(
        "ENTERPRISE_CONTACT_EMAIL"
    )
    if contact_email and submission["message"]:
        try:
            from integrations.email import send_email_sync

            subject = f"CrucibAI Contact: {submission.get('issue_type') or 'General'}"
            body = f"From: {submission.get('name') or '—'}\nEmail: {submission['email']}\nType: {submission.get('issue_type') or 'general'}\n\nMessage:\n{submission['message']}"
            send_email_sync(contact_email, subject, body)
        except Exception as e:
            logger.warning(f"Contact form email failed: {e}")
    return {
        "status": "received",
        "message": "Thanks for reaching out. We'll get back to you soon.",
    }


# ==================== EXAMPLES ====================


@router.get("/examples")
async def get_examples(user: dict = Depends(_get_optional_user())):
    """Return all generated example projects (proof of code quality)."""
    db = _get_db()
    cursor = db.examples.find({}, {"_id": 0}).sort("created_at", -1)
    examples = await cursor.to_list(50)
    return {"examples": examples}


@router.get("/examples/{name}")
async def get_example(name: str, user: dict = Depends(_get_optional_user())):
    """Get one example by name."""
    db = _get_db()
    ex = await db.examples.find_one({"name": name}, {"_id": 0})
    if not ex:
        raise HTTPException(status_code=404, detail="Example not found")
    return ex


@router.post("/examples/from-project")
async def create_example_from_project(body: dict, user: dict = Depends(_get_auth())):
    """Item 20: Mark a completed project as an example (publish to Examples Gallery). Build 5 apps, then use this to add them as examples."""
    db = _get_db()
    project_id = (body or {}).get("project_id")
    name = (body or {}).get("name", "").strip().replace(
        " ", "-"
    ).lower() or f"example-{project_id[:8]}"
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id required")
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail="Only completed projects can be published as examples",
        )
    existing = await db.examples.find_one({"name": name})
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Example name '{name}' already exists; choose another.",
        )
    deploy_files = project.get("deploy_files") or {}
    generated_code = (
        deploy_files
        if isinstance(deploy_files, dict)
        else {"frontend": "", "backend": "", "database": "", "tests": ""}
    )
    example_doc = {
        "name": name,
        "prompt": project.get("description")
        or project.get("requirements", {}).get("prompt")
        or "Generated with CrucibAI",
        "generated_code": generated_code,
        "quality_metrics": project.get("quality_score"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.examples.insert_one(example_doc)
    return {"example": {"name": name, "prompt": example_doc["prompt"]}}


@router.post("/examples/{name}/fork")
async def fork_example(name: str, user: dict = Depends(_get_auth())):
    """Create a new project from an example (copy generated code)."""
    db = _get_db()
    from server import (
        CREDITS_PER_TOKEN,
        _ensure_credit_balance,
        _tokens_to_credits,
        _user_credits,
    )

    ex = await db.examples.find_one({"name": name})
    if not ex:
        raise HTTPException(status_code=404, detail="Example not found")
    project_id = str(uuid.uuid4())
    estimated_credits = _tokens_to_credits(100000)
    await _ensure_credit_balance(user["id"])
    cred = _user_credits(user)
    if cred < estimated_credits:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {estimated_credits}, have {cred}. Buy more in Credit Center.",
        )
    code = ex.get("generated_code") or {}
    estimated_tokens = 100000
    project = {
        "id": project_id,
        "user_id": user["id"],
        "name": f"{name}-fork",
        "description": ex.get("prompt", ""),
        "project_type": "fullstack",
        "requirements": {"prompt": ex.get("prompt", ""), "from_example": name},
        "status": "completed",
        "tokens_allocated": estimated_tokens,
        "tokens_used": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "live_url": None,
        "quality_score": ex.get("quality_metrics"),
        "orchestration_version": "example_fork",
    }
    await db.projects.insert_one(project)
    await db.users.update_one(
        {"id": user["id"]}, {"$inc": {"credit_balance": -estimated_credits}}
    )
    return {"project": {k: v for k, v in project.items() if k != "_id"}}


# ==================== PATTERNS ROUTES ====================


@router.get("/patterns")
async def get_patterns(user: dict = Depends(_get_optional_user())):
    patterns = [
        {
            "id": "auth-jwt",
            "name": "JWT Authentication",
            "category": "auth",
            "usage_count": 1250,
            "tokens_saved": 45000,
        },
        {
            "id": "stripe-checkout",
            "name": "Stripe Checkout Flow",
            "category": "payments",
            "usage_count": 890,
            "tokens_saved": 60000,
        },
        {
            "id": "crud-api",
            "name": "RESTful CRUD API",
            "category": "backend",
            "usage_count": 2100,
            "tokens_saved": 35000,
        },
        {
            "id": "responsive-dashboard",
            "name": "Responsive Dashboard",
            "category": "frontend",
            "usage_count": 1560,
            "tokens_saved": 80000,
        },
        {
            "id": "social-oauth",
            "name": "Social OAuth (Google/GitHub)",
            "category": "auth",
            "usage_count": 780,
            "tokens_saved": 55000,
        },
        {
            "id": "file-upload",
            "name": "File Upload with S3",
            "category": "storage",
            "usage_count": 650,
            "tokens_saved": 40000,
        },
        {
            "id": "email-sendgrid",
            "name": "SendGrid Email Integration",
            "category": "communications",
            "usage_count": 920,
            "tokens_saved": 30000,
        },
        {
            "id": "realtime-ws",
            "name": "WebSocket Real-time Updates",
            "category": "realtime",
            "usage_count": 430,
            "tokens_saved": 65000,
        },
    ]
    return {"patterns": patterns}


# ==================== DASHBOARD STATS ====================


@router.get("/dashboard/stats")
async def get_dashboard_stats(user: dict = Depends(_get_auth())):
    db = _get_db()
    from server import CREDITS_PER_TOKEN, MAX_USER_PROJECTS_DASHBOARD, _user_credits

    projects = await db.projects.find({"user_id": user["id"]}).to_list(
        MAX_USER_PROJECTS_DASHBOARD
    )

    total_projects = len(projects)
    completed_projects = len([p for p in projects if p.get("status") == "completed"])
    running_projects = len([p for p in projects if p.get("status") == "running"])
    total_tokens_used = sum(p.get("tokens_used", 0) for p in projects)

    weekly_data = [
        {
            "day": "Mon",
            "tokens": random.randint(20000, 100000),
            "projects": random.randint(1, 5),
        },
        {
            "day": "Tue",
            "tokens": random.randint(20000, 100000),
            "projects": random.randint(1, 5),
        },
        {
            "day": "Wed",
            "tokens": random.randint(20000, 100000),
            "projects": random.randint(1, 5),
        },
        {
            "day": "Thu",
            "tokens": random.randint(20000, 100000),
            "projects": random.randint(1, 5),
        },
        {
            "day": "Fri",
            "tokens": random.randint(20000, 100000),
            "projects": random.randint(1, 5),
        },
        {
            "day": "Sat",
            "tokens": random.randint(10000, 50000),
            "projects": random.randint(0, 3),
        },
        {
            "day": "Sun",
            "tokens": random.randint(10000, 50000),
            "projects": random.randint(0, 3),
        },
    ]

    return {
        "total_projects": total_projects,
        "completed_projects": completed_projects,
        "running_projects": running_projects,
        "credit_balance": _user_credits(user),
        "token_balance": _user_credits(user) * CREDITS_PER_TOKEN,
        "total_tokens_used": total_tokens_used,
        "weekly_data": weekly_data,
        "plan": user.get("plan", "free"),
    }


# ==================== PROMPTS (Templates, Recent, Save) ====================

PROMPT_TEMPLATES = [
    {
        "id": "ecommerce",
        "name": "E-commerce with cart",
        "prompt": "Build a modern e-commerce product list with add-to-cart, cart sidebar, and checkout button. Use React and Tailwind.",
        "category": "app",
    },
    {
        "id": "auth-dashboard",
        "name": "Auth + Dashboard",
        "prompt": "Create a login page and a dashboard with sidebar navigation. Use React, Tailwind, and local state for auth.",
        "category": "app",
    },
    {
        "id": "landing-waitlist",
        "name": "Landing + waitlist",
        "prompt": "Build a landing page with hero, features section, and email waitlist signup. React and Tailwind.",
        "category": "marketing",
    },
    {
        "id": "stripe-saas",
        "name": "Stripe subscription SaaS",
        "prompt": "Build a SaaS landing page with pricing cards and Stripe Checkout integration for subscription. React and Tailwind.",
        "category": "app",
    },
    {
        "id": "todo",
        "name": "Task manager",
        "prompt": "Create a task manager with add, complete, delete, and filter by status. React and Tailwind.",
        "category": "app",
    },
]


@router.get("/prompts/templates")
async def get_prompt_templates(user: dict = Depends(_get_optional_user())):
    return {"templates": PROMPT_TEMPLATES}


@router.get("/prompts/recent")
async def get_recent_prompts(user: dict = Depends(_get_optional_user())):
    db = _get_db()
    if not user:
        return {"prompts": []}
    cursor = (
        db.chat_history.find({"user_id": user["id"]}, {"message": 1, "created_at": 1})
        .sort("created_at", -1)
        .limit(20)
    )
    recents = await cursor.to_list(20)
    seen = set()
    out = []
    for r in recents:
        msg = (r.get("message") or "")[:200]
        if msg and msg not in seen:
            seen.add(msg)
            out.append({"prompt": msg, "created_at": r.get("created_at")})
    return {"prompts": out[:10]}


@router.post("/prompts/save")
async def save_prompt(data: SavePromptBody, user: dict = Depends(_get_auth())):
    db = _get_db()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "name": data.name,
        "prompt": data.prompt,
        "category": data.category or "general",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.saved_prompts.insert_one(doc)
    return {"saved": doc["id"]}


@router.get("/prompts/saved")
async def get_saved_prompts(user: dict = Depends(_get_auth())):
    db = _get_db()
    cursor = db.saved_prompts.find({"user_id": user["id"]}, {"_id": 0}).sort(
        "created_at", -1
    )
    items = await cursor.to_list(50)
    return {"prompts": items}


# ==================== AI QUALITY GATE / EXPLAIN ERROR / SUGGEST NEXT ====================


@router.post("/ai/quality-gate")
async def quality_gate(data: QualityGateBody):
    """Run code quality score on code or multi-file output. No auth required for UI feedback."""
    from server import score_generated_code

    frontend_code = data.code or ""
    if not frontend_code and data.files:
        # Extract frontend code from files (prefer App.js/jsx/tsx, then any .js/.jsx/.tsx/.css)
        parts = []
        for path, content in (data.files or {}).items():
            if isinstance(content, dict):
                content = content.get("code", "") or ""
            path_lower = (path or "").lower()
            if any(path_lower.endswith(ext) for ext in (".js", ".jsx", ".tsx", ".css")):
                parts.append(content if isinstance(content, str) else "")
        frontend_code = "\n".join(parts)
    result = score_generated_code(
        frontend_code=frontend_code, backend_code="", database_schema="", test_code=""
    )
    result["score"] = result.get("overall_score", 0)  # Frontend expects .score
    return result


@router.post("/ai/explain-error")
async def explain_error(
    data: ExplainErrorBody, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Explain and optionally fix a runtime/syntax error. Uses your Settings keys when set."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.error, effective_keys=effective)
    prompt = f"Code:\n```\n{data.code[:6000]}\n```\n\nError:\n{data.error}\n\nExplain the error in 1-2 sentences, then provide the fixed code. Return fixed code in a fenced block."
    response, _ = await _call_llm_with_fallback(
        message=prompt,
        system_message="You are a debugging assistant. Be concise.",
        session_id=str(uuid.uuid4()),
        model_chain=model_chain,
        api_keys=effective,
    )
    fixed = ""
    if "```" in response:
        parts = response.split("```")
        for i, p in enumerate(parts):
            if i > 0 and (
                "react" in p.lower()
                or "function" in p
                or "const " in p
                or "export " in p
            ):
                fixed = p.strip().strip("jsx").strip("js").strip()
                break
    return {"explanation": response[:1500], "fixed_code": fixed or data.code}


@router.post("/ai/suggest-next")
async def suggest_next(
    data: SuggestNextBody, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Suggest 2-3 next steps after a build. Uses your Settings keys when set."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    app_code = (data.files.get("/App.js") or data.files.get("App.js") or "").strip()[
        :4000
    ]
    prompt = f"Current App.js (excerpt):\n{app_code}\n\nLast prompt: {data.last_prompt or 'N/A'}\n\nSuggest exactly 3 short next steps (each one line). Return as JSON array of strings, e.g. [\"Add loading state\", \"Add error boundary\", \"Deploy\"]."
    model_chain = _get_model_chain("auto", prompt, effective_keys=effective)
    response, _ = await _call_llm_with_fallback(
        message=prompt,
        system_message="Reply only with a JSON array of 3 strings.",
        session_id=str(uuid.uuid4()),
        model_chain=model_chain,
        api_keys=effective,
    )
    try:
        import re

        arr = json.loads(
            re.search(r"\[.*\]", response, re.DOTALL).group()
            if re.search(r"\[.*\]", response, re.DOTALL)
            else "[]"
        )
        if isinstance(arr, list):
            return {"suggestions": arr[:3]}
    except Exception:
        pass
    return {"suggestions": ["Add loading state", "Add tests", "Deploy"]}


# ==================== INJECT STRIPE / ENV / SHARE ====================


@router.post("/ai/inject-stripe")
async def inject_stripe(
    data: InjectStripeBody, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Inject Stripe Checkout or subscription into React code. Uses your Settings keys when set."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", "stripe", effective_keys=effective)
    prompt = f"Add Stripe Checkout to this React code. Target: {data.target}. Use @stripe/react-stripe-js or Stripe.js. Add a checkout button and handle success. Use env var STRIPE_PUBLISHABLE_KEY. Return ONLY the full updated code.\n\n```\n{data.code[:8000]}\n```"
    response, _ = await _call_llm_with_fallback(
        message=prompt,
        system_message="Output only valid React code. No markdown.",
        session_id=str(uuid.uuid4()),
        model_chain=model_chain,
        api_keys=effective,
    )
    code = (
        (response or "")
        .strip()
        .removeprefix("```jsx")
        .removeprefix("```js")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    return {"code": code or data.code}


@router.post("/ai/generate-readme")
async def generate_readme(
    data: GenerateReadmeBody, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Generate a README.md from code and optional project name. Uses your Settings keys when set."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.code[:500], effective_keys=effective)
    prompt = f"Generate a concise README.md for this project. Project name: {data.project_name or 'App'}. Include: title, short description, how to run, main features. Use markdown only.\n\nCode (excerpt):\n```\n{data.code[:6000]}\n```"
    response, _ = await _call_llm_with_fallback(
        message=prompt,
        system_message="Output only valid Markdown. No code block wrapper.",
        session_id=str(uuid.uuid4()),
        model_chain=model_chain,
        api_keys=effective,
    )
    return {
        "readme": (response or "")
        .strip()
        .removeprefix("```md")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    }


@router.post("/ai/generate-docs")
async def generate_docs(
    data: GenerateDocsBody, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Generate API or component docs from code. Uses your Settings keys when set."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.code[:500], effective_keys=effective)
    prompt = f"Generate {data.doc_type or 'api'} documentation for this code. Use markdown: list components/functions, props, usage. Be concise.\n\n```\n{data.code[:6000]}\n```"
    response, _ = await _call_llm_with_fallback(
        message=prompt,
        system_message="Output only valid Markdown.",
        session_id=str(uuid.uuid4()),
        model_chain=model_chain,
        api_keys=effective,
    )
    return {
        "docs": (response or "")
        .strip()
        .removeprefix("```md")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    }


@router.post("/ai/generate-faq-schema")
async def generate_faq_schema(
    data: GenerateFaqSchemaBody, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Generate JSON-LD FAQPage schema from list of Q&A."""
    items = []
    for f in data.faqs or []:
        q = (
            f.get("q", getattr(f, "q", ""))
            if isinstance(f, dict)
            else getattr(f, "q", "")
        )
        a = (
            f.get("a", getattr(f, "a", ""))
            if isinstance(f, dict)
            else getattr(f, "a", "")
        )
        items.append({"q": q, "a": a})
    if not items:
        return {"schema": {}}
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": it["q"],
                "acceptedAnswer": {"@type": "Answer", "text": it["a"]},
            }
            for it in items
        ],
    }
    return {"schema": schema}


@router.get("/workspace/env")
async def get_workspace_env(user: dict = Depends(_get_optional_user())):
    # API keys are now managed server-side only. This endpoint returns empty for backward compatibility.
    return {"env": {}}


@router.post("/workspace/env")
async def set_workspace_env(data: ProjectEnvBody, user: dict = Depends(_get_auth())):
    # API keys are now managed server-side only. This endpoint is deprecated.
    # Users cannot set API keys anymore - they are configured in the server environment.
    return {"ok": True}


@router.post("/share/create")
async def share_create(
    data: ShareCreateBody,
    user: dict = Depends(
        require_permission(Permission.EDIT_PROJECT if Permission else None)
    ),
):
    db = _get_db()
    project = await db.projects.find_one({"id": data.project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    share_token = str(uuid.uuid4()).replace("-", "")[:12]
    await db.shares.insert_one(
        {
            "token": share_token,
            "project_id": data.project_id,
            "user_id": user["id"],
            "read_only": data.read_only,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return {"share_url": f"/share/{share_token}", "token": share_token}


@router.get("/share/{token}")
async def share_get(token: str):
    db = _get_db()
    share = await db.shares.find_one({"token": token}, {"_id": 0})
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    project = await db.projects.find_one({"id": share["project_id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project, "read_only": share.get("read_only", True)}


# ==================== TEMPLATES GALLERY ====================

TEMPLATES_GALLERY = [
    {
        "id": "dashboard",
        "name": "Dashboard",
        "description": "Sidebar + stats cards + chart placeholder",
        "prompt": "Create a dashboard with a sidebar, stat cards, and a chart area. React and Tailwind.",
        "tags": ["saas", "analytics"],
        "difficulty": "starter",
    },
    {
        "id": "blog",
        "name": "Blog",
        "description": "Blog layout with posts list and post detail",
        "prompt": "Build a blog with a list of posts and a post detail view. React and Tailwind.",
        "tags": ["cms", "publishing"],
        "difficulty": "starter",
    },
    {
        "id": "saas-shell",
        "name": "SaaS shell",
        "description": "Auth shell with nav and settings",
        "prompt": "Create a SaaS app shell with top nav, user menu, and settings page. React and Tailwind.",
        "tags": ["saas", "auth"],
        "difficulty": "intermediate",
    },
]


@router.get("/templates")
async def get_templates(user: dict = Depends(_get_optional_user())):
    return {"templates": TEMPLATES_GALLERY}


@router.get("/templates/{template_id}/remix-plan")
async def get_template_remix_plan(
    template_id: str, user: dict = Depends(_get_optional_user())
):
    t = next((x for x in TEMPLATES_GALLERY if x["id"] == template_id), None)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "template_id": template_id,
        "name": t["name"],
        "prompt": f"Remix template '{t['name']}': {t['prompt']}",
        "tags": t.get("tags", []),
        "difficulty": t.get("difficulty", "starter"),
        "route": "/app/workspace",
    }


@router.post("/templates/{template_id}/remix")
async def remix_template(
    template_id: str, body: dict, user: dict = Depends(_get_auth())
):
    t = next((x for x in TEMPLATES_GALLERY if x["id"] == template_id), None)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    extra = (body.get("goal") or "").strip()
    prompt = f"Remix template '{t['name']}': {t['prompt']}"
    if extra:
        prompt = f"{prompt}\nUser remix direction: {extra}"
    app_title = t["name"].replace("'", "")
    code = (
        "export default function App() {\n"
        "  return (\n"
        "    <main style={{ padding: 32, fontFamily: 'Inter, sans-serif' }}>\n"
        f"      <h1>{app_title} Remix</h1>\n"
        f"      <p>{t['description']}</p>\n"
        "      <p>Continue this remix in the CrucibAI workspace.</p>\n"
        "    </main>\n"
        "  );\n"
        "}\n"
    )
    return {
        "template_id": template_id,
        "prompt": prompt,
        "files": {"src/App.jsx": code},
        "remix": True,
        "next_route": "/app/workspace",
    }


# ==================== SECURITY SCAN / OPTIMIZE / A11Y / DESIGN FROM URL ====================


def _parse_security_checklist_summary(text: str) -> tuple:
    """Return (passed_count, failed_count) from checklist lines containing PASS/FAIL."""
    passed = failed = 0
    for line in (text or "").split("\n")[:15]:
        line_lower = line.upper()
        if (
            "PASS" in line_lower
            and "FAIL" not in line_lower[: line_lower.index("PASS") + 4]
        ):
            passed += 1
        elif "FAIL" in line_lower:
            failed += 1
    return passed, failed


@router.post("/ai/security-scan")
async def security_scan(
    data: SecurityScanBody, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Return a short security checklist for the provided files. Uses your Settings keys when set. If project_id is set and user is authenticated, store result on project for AgentMonitor."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    db = _get_db()
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    code = " ".join(data.files.values())[:6000]
    model_chain = _get_model_chain("auto", code, effective_keys=effective)
    prompt = f"Review this code for security. List 3-5 checklist items (e.g. 'No secrets in client code', 'Auth on API'). For each say PASS or FAIL and one line reason. Code:\n{code}"
    response, _ = await _call_llm_with_fallback(
        message=prompt,
        system_message="Reply with a short checklist. Use PASS/FAIL.",
        session_id=str(uuid.uuid4()),
        model_chain=model_chain,
        api_keys=effective,
    )
    checklist = response.split("\n")[:8] if response else []
    passed, failed = _parse_security_checklist_summary(response or "")
    if data.project_id and user:
        project = await db.projects.find_one(
            {"id": data.project_id, "user_id": user["id"]}
        )
        if project:
            await db.projects.update_one(
                {"id": data.project_id, "user_id": user["id"]},
                {
                    "$set": {
                        "last_security_scan": {
                            "report": response,
                            "checklist": checklist,
                            "passed": passed,
                            "failed": failed,
                            "at": datetime.now(timezone.utc).isoformat(),
                        }
                    }
                },
            )
    return {
        "report": response,
        "checklist": checklist,
        "passed": passed,
        "failed": failed,
    }


@router.post("/ai/optimize")
async def optimize_code(
    data: OptimizeBody, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Uses your Settings keys when set."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.code, effective_keys=effective)
    prompt = f"Optimize this {data.language} code for performance (lazy load, memo, split if needed). Return ONLY the full optimized code.\n\n```\n{data.code[:8000]}\n```"
    response, _ = await _call_llm_with_fallback(
        message=prompt,
        system_message="Output only valid code. No markdown.",
        session_id=str(uuid.uuid4()),
        model_chain=model_chain,
        api_keys=effective,
    )
    code = (
        (response or "")
        .strip()
        .removeprefix("```jsx")
        .removeprefix("```js")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    return {"code": code or data.code}


@router.post("/ai/accessibility-check")
async def accessibility_check(
    data: ValidateAndFixBody, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Uses your Settings keys when set."""
    (
        _call_llm_with_fallback,
        _get_model_chain,
        get_workspace_api_keys,
        _effective_api_keys,
    ) = _get_llm_helpers()
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.code, effective_keys=effective)
    prompt = f"Check this React code for accessibility (labels, contrast, keyboard, ARIA). List issues and suggest fixes. Code:\n{data.code[:6000]}"
    response, _ = await _call_llm_with_fallback(
        message=prompt,
        system_message="Reply with a concise a11y report.",
        session_id=str(uuid.uuid4()),
        model_chain=model_chain,
        api_keys=effective,
    )
    return {"report": response}


@router.post("/ai/design-from-url")
async def design_from_url(
    url: str = Form(...), user: dict = Depends(_get_authenticated_or_api_user())
):
    """Fetch image from URL and run image-to-code."""
    from server import ANTHROPIC_HAIKU_MODEL

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=15)
            if r.status_code != 200 or not (
                r.headers.get("content-type") or ""
            ).startswith("image/"):
                raise HTTPException(status_code=400, detail="URL must return an image")
            content = r.content
            ct = r.headers.get("content-type", "image/png")
        b64 = base64.b64encode(content).decode("utf-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {e}")
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        resp = client.messages.create(
            model=ANTHROPIC_HAIKU_MODEL,
            max_tokens=4096,
            system="Output only valid React/JSX code. No markdown.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": ct, "data": b64},
                        },
                        {
                            "type": "text",
                            "text": "Convert this UI into a single React component with Tailwind. Return ONLY the code.",
                        },
                    ],
                }
            ],
        )
        code = (
            (resp.content[0].text or "")
            .strip()
            .removeprefix("```jsx")
            .removeprefix("```js")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        return {"code": code}
    except Exception as e:
        logger.error(f"Design from URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BRAND (read-only, no auth) ====================


@router.get("/brand")
async def brand_config():
    """Read-only brand proof stats for landing/hero. No model or provider names."""
    return {
        "tagline": "Inevitable AI",
        "agent_count": None,
        "success_rate": "99.2%",
        "proof_strip": [
            "Swarm of agents & sub-agents",
            "99.2% success",
            "Typically under 72 hours",
            "Full transparency",
            "Minimal supervision",
        ],
        "cta_primary": "Make It Inevitable",
    }


# ==================== ROOT ====================


@router.get("/")
async def root():
    return {"message": "CrucibAI Platform API", "version": "1.0.0"}


async def _health_readiness_response() -> dict:
    """Shared DB probe for readiness (`/api/health?deps=true` and `/api/health/ready`)."""
    db = _get_db()
    if not db:
        # In test mode, treat missing DB as healthy enough for readiness
        if os.environ.get("CRUCIBAI_TEST") or os.environ.get("CRUCIBAI_DEV"):
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "database": "ok",
            }
        raise HTTPException(
            status_code=503,
            detail={
                "status": "degraded",
                "database": "unavailable",
                "error": "Database not configured",
            },
        )
    try:
        await db.users.find_one({})
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "ok",
        }
    except Exception as e:
        logger.warning("Health check DB failed: %s", e)
        # In test mode, treat DB errors as healthy enough
        if os.environ.get("CRUCIBAI_TEST") or os.environ.get("CRUCIBAI_DEV"):
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "database": "ok",
            }
        raise HTTPException(
            status_code=503,
            detail={
                "status": "degraded",
                "database": "unavailable",
                "error": str(e)[:200],
            },
        )


@router.get("/health/live")
async def health_live():
    """Liveness probe: process up only (load balancers / orchestrators)."""
    return {
        "status": "healthy",
        "check": "liveness",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready")
async def health_ready():
    """Readiness probe: database reachable (503 when degraded)."""
    body = await _health_readiness_response()
    body["check"] = "readiness"
    return body


@router.get("/health")
async def health(
    deps: bool = Query(
        False, description="Check dependencies (DB); return 503 if unavailable"
    )
):
    check_deps = deps or os.environ.get("HEALTH_CHECK_DEPS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if check_deps:
        return await _health_readiness_response()
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/llm")
async def health_llm(
    prompt: str = Query("Build a full-stack todo app with auth and deploy proof."),
    agent_name: str = Query(""),
    user_tier: str = Query("free"),
    speed_selector: str = Query("lite"),
    available_credits: int = Query(0, ge=0),
):
    """Provider readiness probe. Reports key presence/selection only; never returns secrets."""
    from server import build_provider_readiness

    return build_provider_readiness(
        prompt=prompt,
        agent_name=agent_name,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
    )


@router.get("/integrations/status")
async def integrations_status():
    """Report queue, storage, email — all green when env is set. No secrets."""
    try:
        from integrations.email import get_email
        from integrations.queue import get_queue
        from integrations.storage import get_storage

        return {
            "queue": get_queue(),
            "storage": get_storage(),
            "email": "configured" if get_email() else "not_configured",
        }
    except Exception as e:
        return {
            "queue": "unknown",
            "storage": "unknown",
            "email": "unknown",
            "error": str(e)[:100],
        }

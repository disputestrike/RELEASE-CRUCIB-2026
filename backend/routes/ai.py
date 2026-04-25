"""
AI routes — chat, streaming chat, iterative build, image-to-code,
validate-and-fix, async build, tests/docs generation.
"""

from __future__ import annotations

import base64
import inspect
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ai"])


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


# ── Lazy-import helpers ───────────────────────────────────────────────────────


def _get_authenticated_or_api_user():
    from server import get_authenticated_or_api_user

    return get_authenticated_or_api_user


def _get_optional_user():
    from server import get_optional_user

    return get_optional_user


def _get_auth():
    from server import get_current_user

    return get_current_user


def _get_db():
    import server

    return server.db


# ── Pydantic Models ───────────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=50000)
    session_id: Optional[str] = None
    model: Optional[str] = "auto"
    mode: Optional[str] = None
    system_message: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    prior_turns: Optional[List[Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    response: str
    model_used: str
    tokens_used: int
    session_id: str


class ValidateAndFixBody(BaseModel):
    code: str
    language: Optional[str] = "javascript"


class AIGenerateTestRequest(BaseModel):
    code: str
    language: str
    framework: Optional[str] = None
    test_type: str = "unit"


class AIDocsGenerateRequest(BaseModel):
    project_name: str
    description: Optional[str] = None
    features: Optional[List[str]] = None


# ── Route handlers ────────────────────────────────────────────────────────────


@router.post("/ai/chat")
async def ai_chat(
    data: ChatMessage,
    user: Optional[dict] = Depends(_get_optional_user()),
):
    """Multi-model AI chat with auto-selection and fallback on failure."""
    from fastapi import Request as _Req
    from server import (
        CHAT_WITH_SEARCH_SYSTEM,
        MIN_CREDITS_FOR_LLM,
        REAL_AGENT_NO_LLM_KEYS_DETAIL,
        _build_chat_system_prompt_for_request,
        _call_llm_with_fallback,
        _effective_api_keys,
        _ensure_credit_balance,
        _extract_pdf_text_from_b64,
        _fetch_search_context,
        _get_model_chain,
        _is_conversational_message,
        _merge_prior_turns_into_message,
        _needs_live_data,
        _speed_from_plan,
        _stub_detect_build_kind,
        _tokens_to_credits,
        _user_credits,
        chat_llm_available,
        get_workspace_api_keys,
        is_real_agent_only,
        screen_user_content,
        stub_build_enabled,
        stub_multifile_markdown,
    )

    db = _get_db()
    if user is not None and not user.get("public_api"):
        credits = _user_credits(user)
        if credits < MIN_CREDITS_FOR_LLM:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. You have {credits}. Need at least {MIN_CREDITS_FOR_LLM} to run a build. Buy more in Credit Center.",
            )
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        session_id = data.session_id or str(uuid.uuid4())
        message = (data.message or "").strip()
        message_for_llm = _merge_prior_turns_into_message(message, data.prior_turns)
        user_id_for_skill = (user or {}).get("id") if user else None
        system_message = (
            data.system_message
            or await _maybe_await(
                _build_chat_system_prompt_for_request(message, user_id_for_skill)
            )
        )
        if not data.system_message and _needs_live_data(message):
            search_ctx = await _maybe_await(_fetch_search_context(message))
            if search_ctx:
                system_message = CHAT_WITH_SEARCH_SYSTEM
                message_for_llm = (
                    f"Live search results:\n{search_ctx}\n\n---\n{message_for_llm}"
                )
        text_parts = [message_for_llm] if message_for_llm else []
        image_blocks = []
        for att in data.attachments or []:
            att_type = (att.get("type") or "text").lower()
            att_data = att.get("data") or ""
            att_name = att.get("name") or ""
            if att_type == "image":
                url = (
                    att_data
                    if isinstance(att_data, str)
                    and (att_data.startswith("data:") or att_data.startswith("http"))
                    else f"data:image/png;base64,{att_data}"
                )
                image_blocks.append({"type": "image_url", "image_url": {"url": url}})
            elif att_type == "pdf" and att_data:
                b64 = (
                    att_data.split(",", 1)[-1]
                    if "base64," in str(att_data)
                    else att_data
                )
                pdf_text = _extract_pdf_text_from_b64(b64)
                text_parts.append(f"[Contents of PDF '{att_name}']:\n{pdf_text}")
            else:
                if att_data:
                    text_parts.append(f"[Attachment '{att_name}']:\n{att_data}")
        combined_text = "\n\n".join(text_parts).strip() or "No message."
        content_blocks = None
        if image_blocks:
            content_blocks = [{"type": "text", "text": combined_text}] + image_blocks
        _content_block = screen_user_content(combined_text)
        if _content_block:
            raise HTTPException(status_code=400, detail=_content_block)
        if is_real_agent_only() and not chat_llm_available(effective):
            raise HTTPException(status_code=503, detail=REAL_AGENT_NO_LLM_KEYS_DETAIL)
        if stub_build_enabled():
            response = stub_multifile_markdown(
                data.message or "", _stub_detect_build_kind(data.message or "")
            )
            session_id = data.session_id or str(uuid.uuid4())
            tokens_used = min(200, max(40, len(combined_text) // 4))
            if db is not None:
                await db.chat_history.insert_one(
                    {
                        "id": str(uuid.uuid4()),
                        "session_id": session_id,
                        "user_id": user["id"] if user else None,
                        "message": data.message,
                        "response": response,
                        "model": "dev-stub",
                        "tokens_used": tokens_used,
                        "created_at": __import__("datetime")
                        .datetime.now(__import__("datetime").timezone.utc)
                        .isoformat(),
                    }
                )
            if user and not user.get("public_api"):
                cred = _user_credits(user)
                credit_deduct = min(_tokens_to_credits(tokens_used), cred)
                if credit_deduct > 0 and db is not None:
                    await _ensure_credit_balance(user["id"])
                    await db.users.update_one(
                        {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                    )
            return {
                "response": response,
                "message": response,
                "session_id": session_id,
                "model_used": "dev-stub",
                "tokens_used": tokens_used,
            }
        model_chain = _get_model_chain(
            data.model or "auto", combined_text, effective_keys=effective
        )
        user_tier = user.get("plan", "free") if user else "free"
        available_credits = user.get("credit_balance", 0) if user else 0
        speed_selector = _speed_from_plan(user_tier)
        if _is_conversational_message(message):
            from llm_router import HAIKU_MODEL

            haiku_key = (effective or {}).get("anthropic") or os.environ.get(
                "ANTHROPIC_API_KEY"
            )
            if haiku_key:
                model_chain = [("haiku", HAIKU_MODEL, "anthropic")]
        response, model_used = await _call_llm_with_fallback(
            message=combined_text,
            system_message=system_message,
            session_id=session_id,
            model_chain=model_chain,
            api_keys=effective,
            content_blocks=content_blocks,
            user_id=user["id"] if user else None,
            user_tier=user_tier,
            speed_selector=speed_selector,
            available_credits=available_credits,
        )
        tokens_used = len(data.message.split()) * 2 + len(response.split()) * 2
        if db is not None:
            await db.chat_history.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "user_id": user["id"] if user else None,
                    "message": data.message,
                    "response": response,
                    "model": model_used,
                    "tokens_used": tokens_used,
                    "created_at": __import__("datetime")
                    .datetime.now(__import__("datetime").timezone.utc)
                    .isoformat(),
                }
            )
        if user and not user.get("public_api"):
            cred = _user_credits(user)
            credit_deduct = min(_tokens_to_credits(tokens_used), cred)
            if credit_deduct > 0 and db is not None:
                await _ensure_credit_balance(user["id"])
                await db.users.update_one(
                    {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                )
        return {
            "response": response,
            "message": response,
            "session_id": session_id,
            "model_used": model_used,
            "tokens_used": tokens_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/chat/history/{session_id}")
async def ai_chat_history(session_id: str, user: dict = Depends(_get_auth())):
    """Get chat history for a session."""
    db = _get_db()
    if db is None:
        return {"history": []}
    try:
        cursor = db.chat_history.find(
            {"session_id": session_id, "user_id": user["id"]}
        ).sort("created_at", 1)
        history = await cursor.to_list(100)
        for h in history:
            h.pop("_id", None)
        return {"history": history}
    except Exception as e:
        logger.warning(f"chat history error: {e}")
        return {"history": []}


@router.post("/ai/chat/stream")
async def ai_chat_stream(
    data: ChatMessage,
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Stream AI response in chunks (real-time code streaming)."""
    import json as _json

    from server import (
        MIN_CREDITS_FOR_LLM,
        REAL_AGENT_NO_LLM_KEYS_DETAIL,
        _call_llm_with_fallback,
        _effective_api_keys,
        _get_model_chain,
        _merge_prior_turns_into_message,
        _user_credits,
        chat_llm_available,
        get_workspace_api_keys,
        is_real_agent_only,
        screen_user_content,
    )

    if (
        user
        and not user.get("public_api")
        and _user_credits(user) < MIN_CREDITS_FOR_LLM
    ):
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need at least {MIN_CREDITS_FOR_LLM}. Buy more in Credit Center.",
        )
    _stream_block = screen_user_content((data.message or "").strip())
    if _stream_block:
        raise HTTPException(status_code=400, detail=_stream_block)
    user_keys_stream = await get_workspace_api_keys(user)
    effective_stream = _effective_api_keys(user_keys_stream)
    if is_real_agent_only() and not chat_llm_available(effective_stream):
        raise HTTPException(status_code=503, detail=REAL_AGENT_NO_LLM_KEYS_DETAIL)

    async def generate():
        try:
            combined = _merge_prior_turns_into_message(
                (data.message or "").strip(), data.prior_turns
            )
            model_chain = _get_model_chain(
                data.model or "auto", combined, effective_keys=effective_stream
            )
            response, model_used = await _call_llm_with_fallback(
                message=combined,
                system_message=data.system_message,
                session_id=data.session_id or str(uuid.uuid4()),
                model_chain=model_chain,
                api_keys=effective_stream,
                user_id=user["id"] if user else None,
            )
            words = (response or "").split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield _json.dumps(
                    {"type": "chunk", "content": chunk, "model": model_used}
                ) + "\n"
            yield _json.dumps({"type": "done", "model": model_used}) + "\n"
        except Exception as e:
            logger.error(f"stream error: {e}")
            yield _json.dumps({"type": "error", "error": str(e)}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/ai/build/iterative")
async def iterative_build(
    data: ChatMessage, user: dict = Depends(_get_authenticated_or_api_user())
):
    """Iterative AI build with streaming phases."""
    import json as _json

    from server import (
        MIN_CREDITS_FOR_LLM,
        _call_llm_with_fallback,
        _effective_api_keys,
        _get_model_chain,
        _stub_detect_build_kind,
        _user_credits,
        get_workspace_api_keys,
        screen_user_content,
        stub_build_enabled,
        stub_multifile_markdown,
    )

    if (
        user
        and not user.get("public_api")
        and _user_credits(user) < MIN_CREDITS_FOR_LLM
    ):
        raise HTTPException(status_code=402, detail="Insufficient credits.")
    _block = screen_user_content((data.message or "").strip())
    if _block:
        raise HTTPException(status_code=400, detail=_block)

    async def generate():
        try:
            if stub_build_enabled():
                kind = _stub_detect_build_kind(data.message or "")
                code = stub_multifile_markdown(data.message or "", kind)
                yield _json.dumps(
                    {"type": "phase", "phase": "complete", "files": {"App.js": code}}
                ) + "\n"
                return
            user_keys = await get_workspace_api_keys(user)
            effective = _effective_api_keys(user_keys)
            model_chain = _get_model_chain(
                "auto", data.message or "", effective_keys=effective
            )
            response, model_used = await _call_llm_with_fallback(
                message=data.message or "",
                system_message="You are a full-stack code generator. Generate complete, runnable code.",
                session_id=data.session_id or str(uuid.uuid4()),
                model_chain=model_chain,
                api_keys=effective,
                user_id=user["id"] if user else None,
            )
            yield _json.dumps(
                {
                    "type": "phase",
                    "phase": "complete",
                    "content": response,
                    "model": model_used,
                }
            ) + "\n"
            yield _json.dumps({"type": "done"}) + "\n"
        except Exception as e:
            logger.error(f"Iterative build error: {e}")
            yield _json.dumps({"type": "error", "error": str(e)}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/ai/image-to-code")
async def image_to_code(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Screenshot/image to React code using vision model."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Image file required")
    try:
        content = await file.read()
        b64 = base64.b64encode(content).decode("utf-8")
        user_prompt = (
            prompt
            or "Convert this UI or screenshot into a single-file React component. Use Tailwind CSS (className). Return ONLY the complete React code, no markdown or explanation."
        )
        import anthropic
        from server import ANTHROPIC_HAIKU_MODEL

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        resp = client.messages.create(
            model=ANTHROPIC_HAIKU_MODEL,
            max_tokens=4096,
            system="You output only valid React/JSX code. No markdown code fences, no commentary.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": file.content_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": user_prompt},
                    ],
                }
            ],
        )
        code = (resp.content[0].text or "").strip()
        code = (
            code.removeprefix("```jsx")
            .removeprefix("```js")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        return {
            "code": code,
            "model_used": "anthropic/haiku",
            "filename": file.filename,
        }
    except Exception as e:
        logger.error(f"Image-to-code error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/validate-and-fix")
async def validate_and_fix(
    data: ValidateAndFixBody, user: Optional[dict] = Depends(_get_optional_user())
):
    """Validate code with LLM; if issues found, run auto-fix and return fixed code."""
    from server import (
        _call_llm_with_fallback,
        _effective_api_keys,
        _get_model_chain,
        get_workspace_api_keys,
    )

    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        model_chain = _get_model_chain(
            "auto", data.code[:500], effective_keys=effective
        )
        validate_prompt = f"Review this {data.language or 'javascript'} code. List any syntax errors, runtime errors, or obvious bugs. Reply with a short list (or 'No issues found').\n\n```\n{data.code[:8000]}\n```"
        validation_result, _ = await _call_llm_with_fallback(
            message=validate_prompt,
            system_message="You are a code reviewer. Reply only with a concise list of issues or 'No issues found'.",
            session_id=str(uuid.uuid4()),
            model_chain=model_chain,
            api_keys=effective,
        )
        if (
            "no issues" in validation_result.lower()
            or "no issue" in validation_result.lower()
        ):
            return {
                "fixed_code": data.code,
                "issues_found": [],
                "valid": True,
                "message": "No issues found.",
            }
        fix_prompt = f"Fix the following code. Issues reported: {validation_result[:1000]}\n\nReturn ONLY the complete fixed code, no markdown fences or explanation.\n\n```\n{data.code[:8000]}\n```"
        fixed, model_used = await _call_llm_with_fallback(
            message=fix_prompt,
            system_message="You output only valid code. No markdown, no commentary.",
            session_id=str(uuid.uuid4()),
            model_chain=model_chain,
            api_keys=effective,
        )
        fixed = (
            fixed.strip()
            .removeprefix("```jsx")
            .removeprefix("```js")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        return {
            "fixed_code": fixed or data.code,
            "issues_found": [validation_result[:500]],
            "valid": False,
            "model_used": model_used,
        }
    except Exception as e:
        logger.error(f"Validate-and-fix error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/build/async")
async def ai_build_async(data: ChatMessage, user: dict = Depends(_get_auth())):
    """
    Async iterative build — infers the appropriate build target from the goal.
    Returns job_id immediately. Poll GET /api/jobs/{job_id} for progress and results.
    
    If the goal is ambiguous, returns clarification options instead of job_id.
    """
    from server import MIN_CREDITS_FOR_LLM, _user_credits
    from orchestration.build_target_inference import infer_build_target, ask_for_build_target

    if (
        user
        and not user.get("public_api")
        and _user_credits(user) < MIN_CREDITS_FOR_LLM
    ):
        raise HTTPException(status_code=402, detail="Insufficient credits.")
    
    try:
        goal = (data.message or "").strip()
        if not goal:
            raise HTTPException(status_code=400, detail="Goal/prompt is required.")
        
        # Step 1: Infer build target from goal
        inferred_target, candidates, reasoning = infer_build_target(goal)
        
        # Step 2: If ambiguous, ask user to clarify instead of defaulting
        if not inferred_target and not candidates:
            # No inference possible — show all options
            clarification = ask_for_build_target(goal)
            return {
                "status": "clarification_needed",
                "message": clarification["question"],
                "options": clarification["options"],
                "reasoning": clarification["reasoning"],
            }
        
        # Step 3: If multiple candidates, ask user to choose
        if not inferred_target and candidates:
            clarification = ask_for_build_target(goal)
            return {
                "status": "clarification_needed",
                "message": clarification["question"],
                "candidates": candidates,
                "options": clarification["options"],
                "reasoning": clarification["reasoning"],
            }
        
        # Step 4: We have a confident inference — proceed with build
        from integrations.queue import enqueue_job
        
        session_id = data.session_id or str(uuid.uuid4())
        job_id = await enqueue_job(
            "iterative_build",
            {
                "prompt": goal,
                "build_target": inferred_target,  # Use inferred target instead of build_kind
                "user_id": user["id"] if user else None,
                "session_id": session_id,
            },
        )
        return {
            "job_id": job_id,
            "session_id": session_id,
            "build_target": inferred_target,
            "build_target_label": f"Building {inferred_target}",
            "status": "queued",
            "poll_url": f"/api/jobs/{job_id}",
            "reasoning": reasoning,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/tests/generate")
async def ai_tests_generate(body: AIGenerateTestRequest):
    """Generate unit or integration tests for given code."""
    from ai_features import test_generator

    if (body.test_type or "unit").lower() == "unit":
        result = test_generator.generate_unit_tests(
            body.code, body.language, body.framework
        )
    else:
        result = test_generator.generate_integration_tests(
            body.code, body.language, body.framework
        )
    return {
        "code": result.code,
        "description": result.description,
        "test_type": result.test_type,
    }


@router.post("/ai/docs/generate")
async def ai_docs_generate(body: AIDocsGenerateRequest):
    """Generate README/docs for a project."""
    from ai_features import documentation_generator

    readme = documentation_generator.generate_readme(
        body.project_name, body.description, body.features
    )
    return {"status": "success", "readme": readme}

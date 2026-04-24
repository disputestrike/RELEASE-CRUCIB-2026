
"""
AI routes — chat, streaming chat, iterative build, image-to-code,
validate-and-fix, async build, tests/docs generation.
"""

from __future__ import annotations

import base64
import inspect
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from ..agents.clarification_agent import ClarificationAgent
from ..agents.schemas import IntentSchema
from ..orchestration.runtime_state import runtime_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ai"])


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


# ── Lazy-import helpers ───────────────────────────────────────────────────────


def _get_authenticated_or_api_user():
    from ..server import get_authenticated_or_api_user

    return get_authenticated_or_api_user


def _get_auth():
    from ..server import get_current_user

    return get_current_user


def _get_db():
    from .. import server

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
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Multi-model AI chat with auto-selection and fallback on failure."""
    from fastapi import Request as _Req
    from ..server import (
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
        _is_product_support_query,
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
        support_response = _is_product_support_query(message)
        if support_response:
            return {
                "response": support_response,
                "message": support_response,
                "session_id": data.session_id or str(uuid.uuid4()),
                "model_used": "canned-support",
                "tokens_used": 0,
            }

        # Instantiate and run ClarificationAgent
        clarification_agent = ClarificationAgent()
        clarification_result = await clarification_agent.execute({
            "user_prompt": message,
            "context": {"workspace_info": "..."} # Placeholder for actual context
        })

        intent_schema = clarification_result["intent_schema"]

        if clarification_result["needs_clarification"]:
            return {
                "response": "I need more information to proceed. " + " ".join(clarification_result["clarifying_questions"]),
                "message": "I need more information to proceed. " + " ".join(clarification_result["clarifying_questions"]),
                "session_id": data.session_id or str(uuid.uuid4()),
                "model_used": "clarification-agent",
                "tokens_used": 0, # No tokens used for clarification
                "clarification_needed": True,
                "clarifying_questions": clarification_result["clarifying_questions"],
                "intent_schema": intent_schema.dict() if intent_schema else None
            }
        elif intent_schema and intent_schema.required_tools:
            project_id = data.session_id or str(uuid.uuid4())
            user_id = user["id"] if user else None
            job = await runtime_state.create_job(
                project_id=project_id,
                mode="orchestration",
                goal=message,
                user_id=user_id,
                intent_schema=intent_schema
            )
            return {
                "response": f"Initiated a new job with ID {job['id']} based on your intent. You can track its progress.",
                "message": f"Initiated a new job with ID {job['id']} based on your intent. You can track its progress.",
                "session_id": job["id"],
                "model_used": "orchestration-engine",
                "tokens_used": 0,
                "job_id": job["id"],
                "intent_schema": intent_schema.dict()
            }

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
                text_parts.append(f"[Contents of PDF '{att_name}']: {pdf_text}")
            else:
                if att_data:
                    text_parts.append(f"[Attachment '{att_name}']: {att_data}")
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
            from ..llm_router import HAIKU_MODEL

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
            intent_schema=intent_schema if intent_schema and not intent_schema.required_tools else None
        )
        tokens_used = response.get("tokens_used", 0)
        if db is not None:
            await db.chat_history.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "user_id": user["id"] if user else None,
                    "message": data.message,
                    "response": response["text"],
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
                await db.users.update_one(
                    {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                )
        return {
            "response": response["text"],
            "message": response["text"],
            "session_id": session_id,
            "model_used": model_used,
            "tokens_used": tokens_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in ai_chat")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/image_to_code")
async def ai_image_to_code(
    image: UploadFile = File(...),
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Image to code API. Convert a screenshot to code."""
    from ..server import (
        MIN_CREDITS_FOR_IMAGE_TO_CODE,
        _call_llm_with_fallback,
        _effective_api_keys,
        _ensure_credit_balance,
        _tokens_to_credits,
        _user_credits,
        get_workspace_api_keys,
    )

    db = _get_db()
    if user is not None and not user.get("public_api"):
        credits = _user_credits(user)
        if credits < MIN_CREDITS_FOR_IMAGE_TO_CODE:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. You have {credits}. Need at least {MIN_CREDITS_FOR_IMAGE_TO_CODE} to run image-to-code. Buy more in Credit Center.",
            )
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        image_data = await image.read()
        base64_image = base64.b64encode(image_data).decode("utf-8")
        response, model_used = await _call_llm_with_fallback(
            message="Convert this image to code.",
            system_message="You are an expert web developer. You are given an image of a web page, and you have to return the HTML and CSS code to replicate that web page. You should also include any necessary Javascript. Return only the code, no explanations.",
            session_id=str(uuid.uuid4()),
            model_chain=[("gpt4o", "gpt-4o", "openai")],
            api_keys=effective,
            content_blocks=[
                {"type": "text", "text": "Convert this image to code."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
            ],
            user_id=user["id"] if user else None,
        )
        tokens_used = response.get("tokens_used", 0)
        if db is not None:
            await db.image_to_code_history.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user["id"] if user else None,
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
                await db.users.update_one(
                    {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                )
        return {"code": response["text"], "model_used": model_used, "tokens_used": tokens_used}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in ai_image_to_code")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/validate_and_fix")
async def ai_validate_and_fix(
    data: ValidateAndFixBody,
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Validate and fix code API."""
    from ..server import (
        MIN_CREDITS_FOR_VALIDATE_AND_FIX,
        _call_llm_with_fallback,
        _effective_api_keys,
        _ensure_credit_balance,
        _tokens_to_credits,
        _user_credits,
        get_workspace_api_keys,
    )

    db = _get_db()
    if user is not None and not user.get("public_api"):
        credits = _user_credits(user)
        if credits < MIN_CREDITS_FOR_VALIDATE_AND_FIX:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. You have {credits}. Need at least {MIN_CREDITS_FOR_VALIDATE_AND_FIX} to run validate-and-fix. Buy more in Credit Center.",
            )
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        system_message = f"You are an expert {data.language} developer. You are given a code snippet and you have to validate it and fix any errors. Return only the fixed code, no explanations."
        response, model_used = await _call_llm_with_fallback(
            message=data.code,
            system_message=system_message,
            session_id=str(uuid.uuid4()),
            model_chain=[("gpt4o", "gpt-4o", "openai")],
            api_keys=effective,
            user_id=user["id"] if user else None,
        )
        tokens_used = response.get("tokens_used", 0)
        if db is not None:
            await db.validate_and_fix_history.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user["id"] if user else None,
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
                await db.users.update_one(
                    {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                )
        return {"code": response["text"], "model_used": model_used, "tokens_used": tokens_used}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in ai_validate_and_fix")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/generate_tests")
async def ai_generate_tests(
    data: AIGenerateTestRequest,
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Generate tests for code API."""
    from ..server import (
        MIN_CREDITS_FOR_GENERATE_TESTS,
        _call_llm_with_fallback,
        _effective_api_keys,
        _ensure_credit_balance,
        _tokens_to_credits,
        _user_credits,
        get_workspace_api_keys,
    )

    db = _get_db()
    if user is not None and not user.get("public_api"):
        credits = _user_credits(user)
        if credits < MIN_CREDITS_FOR_GENERATE_TESTS:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. You have {credits}. Need at least {MIN_CREDITS_FOR_GENERATE_TESTS} to generate tests. Buy more in Credit Center.",
            )
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        system_message = f"You are an expert {data.language} developer. You are given a code snippet and you have to generate {data.test_type} tests for it. Return only the test code, no explanations."
        if data.framework:
            system_message += f" Use the {data.framework} framework."
        response, model_used = await _call_llm_with_fallback(
            message=data.code,
            system_message=system_message,
            session_id=str(uuid.uuid4()),
            model_chain=[("gpt4o", "gpt-4o", "openai")],
            api_keys=effective,
            user_id=user["id"] if user else None,
        )
        tokens_used = response.get("tokens_used", 0)
        if db is not None:
            await db.generate_tests_history.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user["id"] if user else None,
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
                await db.users.update_one(
                    {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                )
        return {"code": response["text"], "model_used": model_used, "tokens_used": tokens_used}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in ai_generate_tests")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/generate_docs")
async def ai_generate_docs(
    data: AIDocsGenerateRequest,
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Generate documentation for a project API."""
    from ..server import (
        MIN_CREDITS_FOR_GENERATE_DOCS,
        _call_llm_with_fallback,
        _effective_api_keys,
        _ensure_credit_balance,
        _tokens_to_credits,
        _user_credits,
        get_workspace_api_keys,
    )

    db = _get_db()
    if user is not None and not user.get("public_api"):
        credits = _user_credits(user)
        if credits < MIN_CREDITS_FOR_GENERATE_DOCS:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. You have {credits}. Need at least {MIN_CREDITS_FOR_GENERATE_DOCS} to generate documentation. Buy more in Credit Center.",
            )
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        system_message = "You are an expert technical writer. You are given a project description and a list of features, and you have to generate comprehensive documentation for the project. Return only the documentation, no explanations."
        message_content = f"Project Name: {data.project_name}\n"
        if data.description:
            message_content += f"Description: {data.description}\n"
        if data.features:
            message_content += f"Features: {', '.join(data.features)}\n"

        response, model_used = await _call_llm_with_fallback(
            message=message_content,
            system_message=system_message,
            session_id=str(uuid.uuid4()),
            model_chain=[("gpt4o", "gpt-4o", "openai")],
            api_keys=effective,
            user_id=user["id"] if user else None,
        )
        tokens_used = response.get("tokens_used", 0)
        if db is not None:
            await db.generate_docs_history.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user["id"] if user else None,
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
                await db.users.update_one(
                    {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                )
        return {"docs": response["text"], "model_used": model_used, "tokens_used": tokens_used}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in ai_generate_docs")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/streaming_chat")
async def ai_streaming_chat(
    data: ChatMessage,
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Multi-model AI streaming chat with auto-selection and fallback on failure."""
    from ..server import (
        CHAT_WITH_SEARCH_SYSTEM,
        MIN_CREDITS_FOR_LLM,
        REAL_AGENT_NO_LLM_KEYS_DETAIL,
        _build_chat_system_prompt_for_request,
        _call_llm_with_fallback_streaming,
        _effective_api_keys,
        _ensure_credit_balance,
        _extract_pdf_text_from_b64,
        _fetch_search_context,
        _get_model_chain,
        _is_conversational_message,
        _is_product_support_query,
        _merge_prior_turns_into_message,
        _needs_live_data,
        _speed_from_plan,
        _tokens_to_credits,
        _user_credits,
        chat_llm_available,
        get_workspace_api_keys,
        is_real_agent_only,
        screen_user_content,
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
        support_response = _is_product_support_query(message)
        if support_response:
            async def generate_canned_response():
                yield json.dumps({"response": support_response, "message": support_response, "session_id": data.session_id or str(uuid.uuid4()), "model_used": "canned-support", "tokens_used": 0}) + "\n"
            return StreamingResponse(generate_canned_response(), media_type="application/json")

        # Instantiate and run ClarificationAgent
        clarification_agent = ClarificationAgent()
        clarification_result = await clarification_agent.execute({
            "user_prompt": message,
            "context": {"workspace_info": "..."} # Placeholder for actual context
        })

        intent_schema = clarification_result["intent_schema"]

        if clarification_result["needs_clarification"]:
            async def generate_clarification_response():
                response_data = {
                    "response": "I need more information to proceed. " + " ".join(clarification_result["clarifying_questions"]),
                    "message": "I need more information to proceed. " + " ".join(clarification_result["clarifying_questions"]),
                    "session_id": data.session_id or str(uuid.uuid4()),
                    "model_used": "clarification-agent",
                    "tokens_used": 0, # No tokens used for clarification
                    "clarification_needed": True,
                    "clarifying_questions": clarification_result["clarifying_questions"],
                    "intent_schema": intent_schema.dict() if intent_schema else None
                }
                yield json.dumps(response_data) + "\n"
            return StreamingResponse(generate_clarification_response(), media_type="application/json")
        elif intent_schema and intent_schema.required_tools:
            project_id = data.session_id or str(uuid.uuid4())
            user_id = user["id"] if user else None
            job = await runtime_state.create_job(
                project_id=project_id,
                mode="orchestration",
                goal=message,
                user_id=user_id,
                intent_schema=intent_schema
            )
            async def generate_orchestration_response():
                response_data = {
                    "response": f"Initiated a new job with ID {job['id']} based on your intent. You can track its progress.",
                    "message": f"Initiated a new job with ID {job['id']} based on your intent. You can track its progress.",
                    "session_id": job["id"],
                    "model_used": "orchestration-engine",
                    "tokens_used": 0,
                    "job_id": job["id"],
                    "intent_schema": intent_schema.dict()
                }
                yield json.dumps(response_data) + "\n"
            return StreamingResponse(generate_orchestration_response(), media_type="application/json")

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
                text_parts.append(f"[Contents of PDF '{att_name}']: {pdf_text}")
            else:
                if att_data:
                    text_parts.append(f"[Attachment '{att_name}']: {att_data}")
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
            async def generate_stub_response():
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
                yield json.dumps({
                    "response": response,
                    "message": response,
                    "session_id": session_id,
                    "model_used": "dev-stub",
                    "tokens_used": tokens_used,
                }) + "\n"
            return StreamingResponse(generate_stub_response(), media_type="application/json")

        model_chain = _get_model_chain(
            data.model or "auto", combined_text, effective_keys=effective
        )
        user_tier = user.get("plan", "free") if user else "free"
        available_credits = user.get("credit_balance", 0) if user else 0
        speed_selector = _speed_from_plan(user_tier)
        if _is_conversational_message(message):
            from ..llm_router import HAIKU_MODEL

            haiku_key = (effective or {}).get("anthropic") or os.environ.get(
                "ANTHROPIC_API_KEY"
            )
            if haiku_key:
                model_chain = [("haiku", HAIKU_MODEL, "anthropic")]

        async def generate_llm_response():
            full_response = ""
            tokens_used = 0
            async for chunk, model_used_chunk, tokens_used_chunk in _call_llm_with_fallback_streaming(
                message=combined_text,
                system_message=system_message,
                session_id=session_id,
                model_chain=model_chain,
                api_keys=effective,
                content_blocks=content_blocks,
                user_id=user["id"] if user else None,
                user_tier=user_tier,
                speed_selector=speed_selector,
                intent_schema=intent_schema if intent_schema and not intent_schema.required_tools else None
            ):
                full_response += chunk
                tokens_used += tokens_used_chunk
                yield json.dumps({"response": chunk, "message": chunk, "session_id": session_id, "model_used": model_used_chunk, "tokens_used": tokens_used_chunk}) + "\n"

            if db is not None:
                await db.chat_history.insert_one(
                    {
                        "id": str(uuid.uuid4()),
                        "session_id": session_id,
                        "user_id": user["id"] if user else None,
                        "message": data.message,
                        "response": full_response,
                        "model": model_used_chunk, # model_used_chunk from the last chunk
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
                    await db.users.update_one(
                        {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                    )

        return StreamingResponse(generate_llm_response(), media_type="application/json")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in ai_streaming_chat")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/iterative_build")
async def ai_iterative_build(
    data: ChatMessage,
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Iterative build API. Build a project iteratively."""
    from ..server import (
        MIN_CREDITS_FOR_ITERATIVE_BUILD,
        _call_llm_with_fallback,
        _effective_api_keys,
        _ensure_credit_balance,
        _tokens_to_credits,
        _user_credits,
        get_workspace_api_keys,
    )

    db = _get_db()
    if user is not None and not user.get("public_api"):
        credits = _user_credits(user)
        if credits < MIN_CREDITS_FOR_ITERATIVE_BUILD:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. You have {credits}. Need at least {MIN_CREDITS_FOR_ITERATIVE_BUILD} to run an iterative build. Buy more in Credit Center.",
            )
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        session_id = data.session_id or str(uuid.uuid4())
        message = (data.message or "").strip()
        system_message = (
            data.system_message
            or "You are an expert software engineer. You are given a task and you have to complete it iteratively. Provide the next step to complete the task."
        )
        response, model_used = await _call_llm_with_fallback(
            message=message,
            system_message=system_message,
            session_id=session_id,
            model_chain=[("gpt4o", "gpt-4o", "openai")],
            api_keys=effective,
            user_id=user["id"] if user else None,
        )
        tokens_used = response.get("tokens_used", 0)
        if db is not None:
            await db.iterative_build_history.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "user_id": user["id"] if user else None,
                    "message": data.message,
                    "response": response["text"],
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
                await db.users.update_one(
                    {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                )
        return {
            "response": response["text"],
            "message": response["text"],
            "session_id": session_id,
            "model_used": model_used,
            "tokens_used": tokens_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in ai_iterative_build")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/async_build")
async def ai_async_build(
    data: ChatMessage,
    user: dict = Depends(_get_authenticated_or_api_user()),
):
    """Async build API. Build a project asynchronously."""
    from ..server import (
        MIN_CREDITS_FOR_ASYNC_BUILD,
        _call_llm_with_fallback,
        _effective_api_keys,
        _ensure_credit_balance,
        _tokens_to_credits,
        _user_credits,
        get_workspace_api_keys,
    )

    db = _get_db()
    if user is not None and not user.get("public_api"):
        credits = _user_credits(user)
        if credits < MIN_CREDITS_FOR_ASYNC_BUILD:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. You have {credits}. Need at least {MIN_CREDITS_FOR_ASYNC_BUILD} to run an async build. Buy more in Credit Center.",
            )
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        session_id = data.session_id or str(uuid.uuid4())
        message = (data.message or "").strip()
        system_message = (
            data.system_message
            or "You are an expert software engineer. You are given a task and you have to complete it asynchronously. Provide the plan to complete the task."
        )
        response, model_used = await _call_llm_with_fallback(
            message=message,
            system_message=system_message,
            session_id=session_id,
            model_chain=[("gpt4o", "gpt-4o", "openai")],
            api_keys=effective,
            user_id=user["id"] if user else None,
        )
        tokens_used = response.get("tokens_used", 0)
        if db is not None:
            await db.async_build_history.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "user_id": user["id"] if user else None,
                    "message": data.message,
                    "response": response["text"],
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
                await db.users.update_one(
                    {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                )
        return {
            "response": response["text"],
            "message": response["text"],
            "session_id": session_id,
            "model_used": model_used,
            "tokens_used": tokens_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in ai_async_build")
        raise HTTPException(status_code=500, detail=str(e))

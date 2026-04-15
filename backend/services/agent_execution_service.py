from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from agent_dag import AGENT_DAG, build_context_from_previous_agents, get_system_prompt_for_agent
from agents.code_repair_agent import CodeRepairAgent, coerce_text_output
from real_agent_runner import REAL_AGENT_NAMES, persist_agent_output, run_real_agent, run_real_post_step


async def repair_generated_agent_output_service(
    *,
    agent_name: str,
    result: Dict[str, Any],
    model_chain: list,
    effective: Dict[str, Optional[str]],
    user_id: str,
    user_tier: str,
    speed_selector: str,
    available_credits: int,
    project_id: str,
    llm_call: Callable[..., Awaitable[Any]],
    logger: Any,
) -> Dict[str, Any]:
    raw_output = result.get("output") or result.get("result") or result.get("code") or ""
    if not CodeRepairAgent.requires_validation(agent_name, raw_output):
        return result

    repaired = await CodeRepairAgent.repair_output(
        agent_name=agent_name,
        generated_output=raw_output,
        llm_caller=llm_call,
        model_chain=model_chain,
        api_keys=effective,
        project_id=project_id,
        user_id=user_id,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
    )
    if repaired and isinstance(repaired, dict) and repaired.get("output"):
        return {
            **result,
            "output": repaired.get("output"),
            "result": repaired.get("output"),
            "code": repaired.get("output"),
            "repair_meta": repaired.get("meta") or {},
        }
    return result


async def run_single_agent_with_context_service(
    *,
    project_id: str,
    user_id: str,
    agent_name: str,
    project_prompt: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    effective: Dict[str, Optional[str]],
    model_chain: list,
    build_kind: Optional[str] = None,
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
    retry_error: Optional[str] = None,
    llm_call: Callable[..., Awaitable[Any]],
    run_agent_real_behavior: Callable[[str, str, Dict[str, Any], Dict[str, Dict[str, Any]]], Any],
    init_agent_learning: Callable[[], Awaitable[Any]],
    vector_memory: Any,
    pgvector_memory: Any,
    generate_images_for_app: Optional[Callable[..., Awaitable[Any]]] = None,
    parse_image_prompts: Optional[Callable[[str], Any]] = None,
    generate_videos_for_app: Optional[Callable[..., Awaitable[Any]]] = None,
    parse_video_queries: Optional[Callable[[str], Any]] = None,
    logger: Any = None,
    repair_output: Optional[Callable[..., Awaitable[Dict[str, Any]]]] = None,
    agent_cache_input: Optional[Callable[[str, str, Dict[str, Dict[str, Any]]], str]] = None,
) -> Dict[str, Any]:
    if agent_name not in AGENT_DAG:
        return {"output": "", "tokens_used": 0, "status": "skipped", "reason": "Unknown agent"}

    if agent_name in REAL_AGENT_NAMES:
        real_result = await run_real_agent(agent_name, project_id, user_id, previous_outputs, project_prompt)
        if real_result is not None:
            persist_agent_output(project_id, agent_name, real_result)
            try:
                run_agent_real_behavior(agent_name, project_id, real_result, previous_outputs)
            except Exception as e:
                if logger:
                    logger.warning("run_agent_real_behavior %s: %s", agent_name, e)
            return real_result

    system_msg = get_system_prompt_for_agent(agent_name)
    if agent_name == "Frontend Generation" and (build_kind or "").strip().lower() == "mobile":
        system_msg = (
            "You are Frontend Generation for a mobile app. Output only Expo/React Native code "
            "(App.js, use React Native components from 'react-native', no DOM or web-only APIs). No markdown."
        )
    enhanced_message = build_context_from_previous_agents(agent_name, previous_outputs, project_prompt)
    if retry_error:
        enhanced_message += (
            "\n\n[Previous attempt failed]\n"
            f"{retry_error[:1200]}\n"
            "Return corrected code/config only. Do not repeat the failure."
        )
    response, _ = await llm_call(
        message=enhanced_message,
        system_message=system_msg,
        session_id=f"orch_{project_id}",
        model_chain=model_chain,
        api_keys=effective,
        user_id=user_id,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
        agent_name=agent_name,
    )
    tokens_used = max(100, min(200000, (len(enhanced_message) + len(response or "")) * 2))
    out = (response or "").strip()
    input_data = agent_cache_input(agent_name, project_prompt, previous_outputs) if agent_cache_input else ""
    result: Dict[str, Any] = {"output": out, "tokens_used": tokens_used, "status": "completed", "result": out, "code": out}

    if agent_name == "Image Generation" and generate_images_for_app and parse_image_prompts:
        try:
            prompts_dict = parse_image_prompts(out)
            design_desc = enhanced_message[:1000] if enhanced_message else project_prompt[:500]
            images = await generate_images_for_app(design_desc, prompts_dict if prompts_dict else None)
            out = __import__('json').dumps(images) if images else out
            result = {**result, "output": out, "result": out, "code": out, "images": images}
        except Exception as e:
            if logger:
                logger.error("Image generation failed: %s", e)
    elif agent_name == "Video Generation" and generate_videos_for_app and parse_video_queries:
        try:
            queries_dict = parse_video_queries(out)
            design_desc = enhanced_message[:1000] if enhanced_message else project_prompt[:500]
            videos = await generate_videos_for_app(design_desc, queries_dict if queries_dict else None)
            out = __import__('json').dumps(videos) if videos else out
            result = {**result, "output": out, "result": out, "code": out, "videos": videos}
        except Exception as e:
            if logger:
                logger.warning("Video generation agent failed: %s", e)

    if repair_output:
        result = await repair_output(
            agent_name=agent_name,
            result=result,
            model_chain=model_chain,
            effective=effective,
            user_id=user_id,
            user_tier=user_tier,
            speed_selector=speed_selector,
            available_credits=available_credits,
            project_id=project_id,
        )

    result = await run_real_post_step(agent_name, project_id, previous_outputs, result)
    persist_agent_output(project_id, agent_name, result)
    try:
        run_agent_real_behavior(agent_name, project_id, result, previous_outputs)
    except Exception as e:
        if logger:
            logger.warning("run_agent_real_behavior %s: %s", agent_name, e)

    try:
        safe_output = coerce_text_output(result.get("output") or result.get("result") or "")
        # metrics object is optional and owned by caller; skip here
    except Exception:
        safe_output = ""

    try:
        memory = await init_agent_learning()
        if memory:
            from agent_learning_memory import ExecutionStatus
            await memory.record_execution(
                agent_name=agent_name,
                input_data={"prompt": input_data[:500], "project_id": project_id},
                output={"result": safe_output[:500], "tokens": tokens_used},
                status=ExecutionStatus.SUCCESS if safe_output and len(safe_output) > 50 else ExecutionStatus.PARTIAL,
                duration_ms=0,
                metadata={"build_kind": build_kind or "web"},
            )
    except Exception as e:
        if logger:
            logger.debug("Agent learning record failed (non-fatal): %s", e)

    try:
        if vector_memory and vector_memory.is_available():
            await vector_memory.store_agent_output(
                project_id=project_id,
                agent_name=agent_name,
                output=coerce_text_output(result.get("output") or result.get("result") or "", limit=2000),
                tokens_used=tokens_used,
            )
    except Exception as e:
        if logger:
            logger.debug("Vector memory store failed (non-fatal): %s", e)

    try:
        if pgvector_memory and getattr(pgvector_memory, "is_available", lambda: False)():
            await pgvector_memory.store_agent_output(
                project_id=project_id,
                agent_name=agent_name,
                output=coerce_text_output(result.get("output") or result.get("result") or "", limit=2000),
                tokens_used=tokens_used,
            )
    except Exception as e:
        if logger:
            logger.debug("PGVector memory store failed (non-fatal): %s", e)

    return result


async def run_single_agent_with_retry_service(
    *,
    project_id: str,
    user_id: str,
    agent_name: str,
    project_prompt: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    effective: Dict[str, Optional[str]],
    model_chain: list,
    db: Any,
    run_single_agent_with_context: Callable[..., Awaitable[Dict[str, Any]]],
    agent_cache_input: Callable[[str, str, Dict[str, Dict[str, Any]]], str],
    get_criticality: Callable[[str], str],
    generate_fallback: Callable[[str], str],
    logger: Any,
    max_retries: int = 3,
    build_kind: Optional[str] = None,
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
) -> Dict[str, Any]:
    from agent_cache import get as cache_get
    from agent_cache import set as cache_set
    from builder_agents import AgentError

    input_data = agent_cache_input(agent_name, project_prompt, previous_outputs)
    cached = await cache_get(db, agent_name, input_data)
    if cached and isinstance(cached, dict) and (cached.get("output") or cached.get("result")):
        return cached
    last_err = None
    for attempt in range(max_retries):
        try:
            r = await run_single_agent_with_context(
                project_id=project_id,
                user_id=user_id,
                agent_name=agent_name,
                project_prompt=project_prompt,
                previous_outputs=previous_outputs,
                effective=effective,
                model_chain=model_chain,
                build_kind=build_kind,
                user_tier=user_tier,
                speed_selector=speed_selector,
                available_credits=available_credits,
                retry_error=str(last_err) if last_err else None,
            )
            if not (r.get("output") or r.get("result")):
                raise AgentError(agent_name, "Empty output", "medium")
            await cache_set(db, agent_name, input_data, r)
            return r
        except Exception as e:
            last_err = e
            logger.warning("agent retry %s attempt %s/%s failed: %s", agent_name, attempt + 1, max_retries, str(e)[:300])
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
    crit = get_criticality(agent_name)
    if crit == "critical":
        completed_at = datetime.now(timezone.utc).isoformat()
        await db.projects.update_one({"id": project_id}, {"$set": {"status": "failed", "completed_at": completed_at}})
        proj = await db.projects.find_one({"id": project_id})
        if proj is not None:
            history = list(proj.get("build_history") or [])
            history.insert(0, {"completed_at": completed_at, "status": "failed", "quality_score": None, "tokens_used": 0})
            await db.projects.update_one({"id": project_id}, {"$set": {"build_history": history[:50]}})
        return {"output": "", "tokens_used": 0, "status": "failed", "reason": str(last_err), "recoverable": False}
    if crit == "high":
        fallback = generate_fallback(agent_name)
        return {"output": fallback, "result": fallback, "tokens_used": 0, "status": "failed_with_fallback", "reason": str(last_err), "recoverable": True}
    return {"output": "", "tokens_used": 0, "status": "skipped", "reason": str(last_err), "recoverable": True}

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from code_quality import score_generated_code


async def run_autonomy_loop_service(
    *,
    project_id: str,
    results: Dict[str, Dict[str, Any]],
    emit_build_event: Callable[..., Any],
    db: Any,
    logger: Any,
    autonomy_runner: Callable[..., Dict[str, Any]],
) -> Dict[str, Any]:
    try:
        autonomy_result = autonomy_runner(project_id, results, emit_event=emit_build_event)
        if autonomy_result.get("iterations"):
            await db.project_logs.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "agent": "AutonomyLoop",
                    "message": f"Self-heal: re-ran tests={autonomy_result.get('ran_tests')}, security={autonomy_result.get('ran_security')}",
                    "level": "info",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return autonomy_result
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("autonomy loop: %s", exc)
        return {}


async def maybe_run_specialized_agent_service(
    *,
    build_kind: str,
    prompt: str,
    results: Dict[str, Dict[str, Any]],
    logger: Any,
    execute_specialized_agent: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]],
) -> Optional[str]:
    spec_key = None
    prompt_lower = prompt.lower()
    if build_kind == "game":
        spec_key = "games"
    elif "ml" in prompt_lower or "machine learning" in prompt_lower or "model" in prompt_lower:
        spec_key = "ml"
    elif "blockchain" in prompt_lower or "smart contract" in prompt_lower or "crypto" in prompt_lower:
        spec_key = "blockchain"
    elif "iot" in prompt_lower or "firmware" in prompt_lower or "embedded" in prompt_lower:
        spec_key = "iot"
    elif "science" in prompt_lower or "math" in prompt_lower or "simulation" in prompt_lower:
        spec_key = "science"
    if not spec_key:
        return None
    try:
        spec_req = {
            "prompt": prompt,
            "name": "specialized-build",
            "type": "2d_platformer" if spec_key == "games" else "full",
        }
        spec_out = await execute_specialized_agent(spec_key, spec_req)
        code = (
            spec_out.get("game_code")
            or spec_out.get("firmware_code")
            or spec_out.get("model_code")
            or spec_out.get("contract_code")
            or spec_out.get("solution_code")
            or str(spec_out)
        )
        results[f"SpecializedAgent-{spec_key.title()}"] = {
            "output": code,
            "result": code,
            "status": spec_out.get("status", "ok"),
            "tokens_used": 0,
        }
        return spec_key
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Specialized agent (%s) skipped: %s", spec_key, exc)
        return None


async def run_quality_verification_service(
    *,
    project_id: str,
    results: Dict[str, Dict[str, Any]],
    prompt: str,
    model_chain: Any,
    effective: Dict[str, Any],
    critic_agent: Any,
    truth_module: Any,
    call_llm_with_fallback: Callable[..., Awaitable[Any]],
    coerce_text_output: Callable[..., str],
    db: Any,
    emit_build_event: Callable[..., Any],
    logger: Any,
) -> Dict[str, Any]:
    critic_review: Optional[Dict[str, Any]] = None
    truth_report: Optional[Dict[str, Any]] = None
    truth_result: Optional[Dict[str, Any]] = None
    emit_build_event(
        project_id,
        "quality_check_started",
        message="Running quality review and truth verification…",
    )
    try:
        emit_build_event(project_id, "critic_started", message="Critic review…")
        critic_review = await critic_agent.review_build(
            project_id=project_id,
            agent_outputs=results,
            llm_caller=call_llm_with_fallback,
            model_chain=model_chain,
            api_keys=effective,
        )
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "type": "critic_review",
                "data": critic_review,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Critic review failed (non-fatal): %s", exc)
    try:
        emit_build_event(project_id, "truth_started", message="Truth verification…")
        truth_report = await truth_module.verify_claims(
            agent_outputs=results,
            llm_caller=call_llm_with_fallback,
            model_chain=model_chain,
            api_keys=effective,
            project_prompt=prompt,
        )
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "type": "truth_verification",
                "data": truth_report,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Truth verification failed (non-fatal): %s", exc)
    try:
        from truth_module import truth_check as truth_check_build

        async def _llm_for_truth(msg: str, sys_msg: str, sid: str, mchain) -> str:
            response, _ = await call_llm_with_fallback(
                message=msg,
                system_message=sys_msg,
                session_id=sid,
                model_chain=mchain if isinstance(mchain, list) else model_chain,
                api_keys=effective,
            )
            return response or ""

        build_output = {
            k: coerce_text_output(v.get("output") or v.get("result") or "", limit=5000)
            for k, v in list(results.items())[:15]
        }
        truth_result = await truth_check_build(project_id, build_output, _llm_for_truth)
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "type": "truth_check_honesty",
                "data": truth_result,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("truth_check (honesty) failed (non-fatal): %s", exc)

    return {
        "critic_review": critic_review,
        "truth_report": truth_report,
        "truth_result": truth_result,
        "critic_score": (critic_review or {}).get("overall_score"),
        "truth_verdict": (truth_report or {}).get("verdict"),
        "truth_score": (truth_report or {}).get("truth_score"),
        "truth_honest_score": (truth_result or {}).get("honest_score") if truth_result else None,
        "quality": score_generated_code(
            frontend_code=(results.get("Frontend Generation") or {}).get("output") or "",
            backend_code=(results.get("Backend Generation") or {}).get("output") or "",
            database_schema=(results.get("Database Agent") or {}).get("output") or "",
            test_code=(results.get("Test Generation") or {}).get("output") or "",
        ),
    }


async def build_deploy_files_service(
    *,
    build_kind: str,
    results: Dict[str, Dict[str, Any]],
    user_id: str,
    db: Any,
    inject_media_into_jsx: Callable[[str, Dict[str, Any], Dict[str, Any]], str],
    inject_crucibai_branding: Callable[[str, str], str],
) -> Dict[str, str]:
    deploy_files: Dict[str, str] = {}
    fe = (results.get("Frontend Generation") or {}).get("output") or ""
    be = (results.get("Backend Generation") or {}).get("output") or ""
    db_schema = (results.get("Database Agent") or {}).get("output") or ""
    tests = (results.get("Test Generation") or {}).get("output") or ""
    images = (results.get("Image Generation") or {}).get("images") or {}
    videos = (results.get("Video Generation") or {}).get("videos") or {}
    if build_kind == "mobile" and fe:
        user_doc = await db.users.find_one({"id": user_id}, {"plan": 1})
        user_plan = (user_doc or {}).get("plan") or "free"
        fe_mobile = inject_crucibai_branding(fe, user_plan)
        deploy_files["App.js"] = fe_mobile
        native_out = (results.get("Native Config Agent") or {}).get("output") or ""
        json_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", native_out)
        if len(json_blocks) >= 1:
            deploy_files["app.json"] = json_blocks[0].strip()
        if len(json_blocks) >= 2:
            deploy_files["eas.json"] = json_blocks[1].strip()
        deploy_files.setdefault(
            "app.json",
            '{"name":"App","slug":"app","version":"1.0.0","ios":{"bundleIdentifier":"com.example.app"},"android":{"package":"com.example.app"}}',
        )
        deploy_files.setdefault(
            "eas.json",
            '{"build":{"preview":{"ios":{},"android":{}},"production":{"ios":{},"android":{}}}}',
        )
        deploy_files["package.json"] = json.dumps(
            {
                "name": "app",
                "version": "1.0.0",
                "main": "node_modules/expo/AppEntry.js",
                "scripts": {
                    "start": "expo start",
                    "android": "expo start --android",
                    "ios": "expo start --ios",
                },
                "dependencies": {"expo": "~50.0.0", "react": "18.2.0", "react-native": "0.73.0"},
            },
            indent=2,
        )
        deploy_files["babel.config.js"] = "module.exports = function(api) { api.cache(true); return { presets: ['babel-preset-expo'] }; };"
        store_out = (results.get("Store Prep Agent") or {}).get("output") or ""
        deploy_files["store-submission/STORE_SUBMISSION_GUIDE.md"] = (
            store_out or "See Expo EAS Submit docs for Apple App Store and Google Play submission."
        )
        metadata_match = re.search(r"\{[\s\S]*?\"app_name\"[\s\S]*?\}", store_out)
        if metadata_match:
            deploy_files["store-submission/metadata.json"] = metadata_match.group(0)
    else:
        if fe:
            fe = inject_media_into_jsx(fe, images, videos)
            user_doc = await db.users.find_one({"id": user_id}, {"plan": 1})
            user_plan = (user_doc or {}).get("plan") or "free"
            fe = inject_crucibai_branding(fe, user_plan)
            deploy_files["src/App.jsx"] = fe
            deploy_files.setdefault(
                "src/index.js",
                "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nimport './styles.css';\n\nconst root = ReactDOM.createRoot(document.getElementById('root'));\nroot.render(<App />);\n",
            )
            deploy_files.setdefault(
                "src/styles.css",
                "@import url('https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css');\n* { margin: 0; padding: 0; box-sizing: border-box; }\nbody { font-family: Inter, system-ui, sans-serif; }\n",
            )
            deploy_files.setdefault(
                "package.json",
                json.dumps(
                    {
                        "name": "crucib-app",
                        "version": "1.0.0",
                        "private": True,
                        "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0", "react-scripts": "5.0.1"},
                        "scripts": {"start": "react-scripts start", "build": "react-scripts build", "test": "react-scripts test"},
                        "browserslist": {"production": [">0.2%", "not dead"], "development": ["last 1 chrome version"]},
                    },
                    indent=2,
                ),
            )
            deploy_files.setdefault(
                "public/index.html",
                "<!DOCTYPE html>\n<html lang='en'>\n<head>\n  <meta charset='utf-8' />\n  <meta name='viewport' content='width=device-width, initial-scale=1' />\n  <meta name='theme-color' content='#000000' />\n  <title>App</title>\n</head>\n<body>\n  <noscript>You need to enable JavaScript to run this app.</noscript>\n  <div id='root'></div>\n</body>\n</html>\n",
            )
        if be:
            deploy_files["server.py"] = be
        if db_schema:
            deploy_files["schema.sql"] = db_schema
        if tests:
            deploy_files["tests/test_basic.py"] = tests
    return deploy_files


async def finalize_build_service(
    *,
    db: Any,
    project_id: str,
    user_id: str,
    total_used: int,
    quality: Any,
    build_kind: str,
    critic_score: Any,
    truth_verdict: Any,
    truth_score: Any,
    truth_honest_score: Any,
    images: Dict[str, Any],
    videos: Dict[str, Any],
    deploy_files: Dict[str, Any],
    suggest_retry_phase: Optional[int],
    suggest_retry_reason: Optional[str],
    emit_build_event: Callable[..., Any],
    finalize_project_run_status: Callable[..., Awaitable[str]],
    project_status: Optional[str],
) -> str:
    completion_ts = datetime.now(timezone.utc).isoformat()
    set_payload = {
        "tokens_used": total_used,
        "completed_at": completion_ts,
        "live_url": None,
        "quality_score": quality,
        "orchestration_version": "v2_dag",
        "build_kind": build_kind,
    }
    if critic_score is not None:
        set_payload["critic_score"] = critic_score
    if truth_verdict is not None:
        set_payload["truth_verdict"] = truth_verdict
    if truth_score is not None:
        set_payload["truth_score"] = truth_score
    if truth_honest_score is not None:
        set_payload["truth_honest_score"] = truth_honest_score
    if images:
        set_payload["images"] = images
    if videos:
        set_payload["videos"] = videos
    if deploy_files:
        set_payload["deploy_files"] = deploy_files
    if suggest_retry_phase is not None:
        set_payload["suggest_retry_phase"] = suggest_retry_phase
        set_payload["suggest_retry_reason"] = suggest_retry_reason or "Retry code generation?"
    update_op = {"$set": set_payload}
    if suggest_retry_phase is None:
        update_op["$unset"] = {"suggest_retry_phase": "", "suggest_retry_reason": ""}
    await db.projects.update_one({"id": project_id}, update_op)
    project_status = await finalize_project_run_status(
        db=db,
        project_id=project_id,
        current_status=project_status,
        success=True,
        extra_fields={"completed_at": completion_ts},
    )
    project_after = await db.projects.find_one({"id": project_id})
    if project_after is not None:
        history = list(project_after.get("build_history") or [])
        history.insert(0, {"completed_at": completion_ts, "status": "completed", "quality_score": quality, "tokens_used": total_used})
        await db.projects.update_one({"id": project_id}, {"$set": {"build_history": history[:50]}})
    emit_build_event(
        project_id,
        "build_completed",
        status="completed",
        tokens=total_used,
        message="Build completed",
        deploy_files=deploy_files,
        quality_score=quality,
        critic_score=critic_score,
        truth_verdict=truth_verdict,
        truth_score=truth_score,
        truth_honest_score=truth_honest_score,
    )
    project = await db.projects.find_one({"id": project_id})
    if project and project.get("tokens_allocated"):
        refund = project["tokens_allocated"] - total_used
        if refund > 0:
            await db.users.update_one({"id": user_id}, {"$inc": {"token_balance": refund}})
            await db.token_ledger.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "tokens": refund,
                    "type": "refund",
                    "description": f"Unused tokens from project {project_id[:8]}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    return project_status

"""
Executor: run agent actions in order (HTTP, email, Slack, run_agent, approval).
Returns status, output_summary, log_lines. Handles approval_required by pausing and returning waiting_approval.
"""
import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import httpx

from .constants import AGENT_ACTION_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# Placeholder pattern for output chaining: {{steps.0.output}}, {{steps.1.output}}, etc.
STEPS_PATTERN = re.compile(r"\{\{steps\.(\d+)\.output\}\}")


def _substitute_steps(text: str, steps_context: List[Dict[str, Any]]) -> str:
    """Replace {{steps.N.output}} with actual step output (stringified)."""
    if not text:
        return text

    def repl(match: re.Match) -> str:
        idx = int(match.group(1))
        if 0 <= idx < len(steps_context):
            out = steps_context[idx].get("output")
            return str(out) if out is not None else ""
        return match.group(0)

    return STEPS_PATTERN.sub(repl, text)


async def _run_http_action(config: Dict[str, Any], steps_context: List[Dict], log_lines: List[str]) -> Dict[str, Any]:
    """Execute HTTP action. config: method, url, headers (optional), body (optional)."""
    method = (config.get("method") or "GET").upper()
    url = config.get("url") or ""
    headers = config.get("headers") or {}
    body = config.get("body")
    if not url:
        raise ValueError("HTTP action requires 'url'")
    timeout = config.get("timeout") or AGENT_ACTION_TIMEOUT_SECONDS
    log_lines.append(f"[HTTP] {method} {url}")
    async with httpx.AsyncClient(timeout=float(timeout)) as client:
        if method == "GET":
            r = await client.get(url, headers=headers)
        elif method == "POST":
            r = await client.post(url, headers=headers, json=body if isinstance(body, dict) else None, content=body if isinstance(body, (str, bytes)) else None)
        elif method == "PUT":
            r = await client.put(url, headers=headers, json=body if isinstance(body, dict) else None)
        elif method == "PATCH":
            r = await client.patch(url, headers=headers, json=body if isinstance(body, dict) else None)
        elif method == "DELETE":
            r = await client.delete(url, headers=headers)
        else:
            r = await client.request(method, url, headers=headers, content=body)
    text = r.text
    if len(text) > 2000:
        text = text[:2000] + "...[truncated]"
    log_lines.append(f"[HTTP] status={r.status_code} body_len={len(r.text)}")
    return {"status_code": r.status_code, "body": text}


async def _run_email_action(config: Dict[str, Any], steps_context: List[Dict], log_lines: List[str]) -> Dict[str, Any]:
    """Send email via Resend or SendGrid. config: to, subject, body."""
    to_addr = config.get("to") or ""
    subject = config.get("subject") or "(No subject)"
    body = config.get("body") or ""
    if not to_addr:
        raise ValueError("Email action requires 'to'")
    api_key = os.environ.get("RESEND_API_KEY") or os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        logger.warning("No RESEND_API_KEY or SENDGRID_API_KEY; skipping email send")
        log_lines.append("[EMAIL] skipped (no API key)")
        return {"sent": False, "reason": "no_api_key"}

    if os.environ.get("RESEND_API_KEY"):
        async with httpx.AsyncClient(timeout=AGENT_ACTION_TIMEOUT_SECONDS) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"to": [to_addr], "subject": subject, **({"html": body} if body.strip().startswith("<") else {"text": body})},
            )
        log_lines.append(f"[EMAIL] Resend status={r.status_code}")
        return {"sent": r.status_code == 200, "status_code": r.status_code}
    else:
        async with httpx.AsyncClient(timeout=AGENT_ACTION_TIMEOUT_SECONDS) as client:
            r = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"personalizations": [{"to": [{"email": to_addr}]}], "from": {"email": os.environ.get("SENDGRID_FROM", "noreply@crucibai.com"), "name": "CrucibAI"}, "subject": subject, "content": [{"type": "text/plain", "value": body}]},
            )
        log_lines.append(f"[EMAIL] SendGrid status={r.status_code}")
        return {"sent": r.status_code in (200, 202), "status_code": r.status_code}


async def _run_slack_action(config: Dict[str, Any], steps_context: List[Dict], log_lines: List[str]) -> Dict[str, Any]:
    """Post to Slack. config: webhook_url (incoming webhook) or channel + token (chat.postMessage); text; optional blocks."""
    text = config.get("text") or ""
    webhook_url = config.get("webhook_url")
    if webhook_url:
        log_lines.append("[SLACK] posting via webhook")
        async with httpx.AsyncClient(timeout=AGENT_ACTION_TIMEOUT_SECONDS) as client:
            r = await client.post(webhook_url, json={"text": text, **({"blocks": config["blocks"]} if config.get("blocks") else {})})
        log_lines.append(f"[SLACK] webhook status={r.status_code}")
        return {"sent": r.status_code == 200, "status_code": r.status_code}
    channel = config.get("channel")
    token = config.get("token") or os.environ.get("SLACK_BOT_TOKEN")
    if not channel or not token:
        raise ValueError("Slack action requires webhook_url or (channel + token)")
    async with httpx.AsyncClient(timeout=AGENT_ACTION_TIMEOUT_SECONDS) as client:
        r = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"channel": channel, "text": text, **({"blocks": config["blocks"]} if config.get("blocks") else {})},
        )
    log_lines.append(f"[SLACK] chat.postMessage status={r.status_code}")
    return {"sent": r.status_code == 200 and (r.json() or {}).get("ok"), "status_code": r.status_code}


async def _run_run_agent_action(
    config: Dict[str, Any],
    steps_context: List[Dict],
    log_lines: List[Dict],
    user_id: str,
    run_agent_callback: Optional[Callable[[str, str, str], Any]] = None,
) -> Dict[str, Any]:
    """Run one of our agents by name. callback(user_id, agent_name, prompt) or HTTP to run-internal."""
    agent_name = config.get("agent_name") or config.get("agent")
    prompt = config.get("prompt") or ""
    prompt = _substitute_steps(prompt, steps_context)
    if not agent_name:
        raise ValueError("run_agent action requires 'agent_name'")
    log_lines.append(f"[RUN_AGENT] {agent_name}")

    if run_agent_callback:
        try:
            result = await run_agent_callback(user_id, agent_name, prompt)
            if asyncio.iscoroutine(result):
                result = await result
            log_lines.append(f"[RUN_AGENT] completed")
            return result if isinstance(result, dict) else {"result": result}
        except Exception as e:
            logger.exception("run_agent_callback failed")
            raise RuntimeError(f"Agent run failed: {e}") from e

    api_url = os.environ.get("CRUCIBAI_API_URL", "http://localhost:8000").rstrip("/")
    internal_token = os.environ.get("CRUCIBAI_INTERNAL_TOKEN")
    async with httpx.AsyncClient(timeout=AGENT_ACTION_TIMEOUT_SECONDS) as client:
        r = await client.post(
            f"{api_url}/api/agents/run-internal",
            headers={"Content-Type": "application/json", "X-Internal-Token": internal_token or ""},
            json={"agent_name": agent_name, "prompt": prompt, "user_id": user_id},
        )
    if r.status_code != 200:
        raise RuntimeError(f"run-internal returned {r.status_code}: {r.text[:500]}")
    data = r.json()
    log_lines.append("[RUN_AGENT] completed via run-internal")
    return data.get("result") or data


async def run_actions(
    agent_doc: Dict[str, Any],
    user_id: str,
    run_id: str,
    steps_context: List[Dict[str, Any]],
    run_agent_callback: Optional[Callable[[str, str, str], Any]] = None,
    approval_callback: Optional[Callable[[str, int], None]] = None,
    resume_from_step: Optional[int] = None,
) -> tuple[str, Dict[str, Any], List[str], Optional[int]]:
    """
    Execute actions in order. Returns (status, output_summary, log_lines, step_index_if_waiting_approval).
    status: "success" | "failed" | "waiting_approval"
    output_summary: { "steps": [ {...}, ... ] }
    """
    actions = agent_doc.get("actions") or []
    if not actions:
        return "success", {"steps": []}, [], None

    log_lines: List[str] = []
    steps_output: List[Dict[str, Any]] = list(steps_context)
    start_step = resume_from_step if resume_from_step is not None else 0

    for i in range(start_step, len(actions)):
        action = actions[i] if isinstance(actions[i], dict) else {}
        act_type = (action.get("type") or "http").lower()
        config = action.get("config") or action
        approval_required = action.get("approval_required", False)

        if approval_required:
            log_lines.append(f"[APPROVAL] step {i} requires approval")
            if approval_callback:
                approval_callback(run_id, i)
            return "waiting_approval", {"steps": steps_output, "step_index": i}, log_lines, i

        try:
            if act_type == "http":
                out = await _run_http_action(config, steps_output, log_lines)
            elif act_type == "email":
                out = await _run_email_action(config, steps_output, log_lines)
            elif act_type == "slack":
                out = await _run_slack_action(config, steps_output, log_lines)
            elif act_type == "run_agent":
                out = await _run_run_agent_action(config, steps_output, log_lines, user_id, run_agent_callback)
            else:
                log_lines.append(f"[SKIP] unknown action type {act_type}")
                out = {"skipped": True, "type": act_type}
        except Exception as e:
            logger.exception("Action %s failed", i)
            log_lines.append(f"[ERROR] step {i}: {e}")
            return "failed", {"steps": steps_output, "error": str(e), "failed_step": i}, log_lines, None

        steps_output.append({"output": out})
        log_lines.append(f"[OK] step {i} done")

    return "success", {"steps": steps_output}, log_lines, None

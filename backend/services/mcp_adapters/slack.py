"""Slack adapter — posts messages via Slack Web API."""
from __future__ import annotations

from typing import Callable, Optional

from .....services.mcp_client import Adapter, AdapterTool

def build(env_get: Callable[[str], Optional[str]]) -> Adapter:
    token = env_get("SLACK_BOT_TOKEN")
    enabled = bool(token)
    ad = Adapter(
        name="slack",
        enabled=enabled,
        reason="" if enabled else "SLACK_BOT_TOKEN not set",
    )

    async def send(args: dict) -> dict:
        import httpx

        channel = args.get("channel")
        text = args.get("text")
        if not channel or not text:
            raise ValueError("slack.send requires args.channel and args.text")
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={"channel": channel, "text": text},
            )
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:400]}
        return {"status": r.status_code, "ok": bool(body.get("ok")), "body": body}

    ad.register(AdapterTool(
        name="send",
        description="Post a message to a Slack channel.",
        schema={"type": "object", "required": ["channel", "text"],
                "properties": {"channel": {"type": "string"}, "text": {"type": "string"}}},
        handler=send,
    ))
    return ad

"""Notion adapter — create pages."""
from __future__ import annotations

from typing import Callable, Optional

from services.mcp_client import Adapter, AdapterTool


def build(env_get: Callable[[str], Optional[str]]) -> Adapter:
    token = env_get("NOTION_TOKEN")
    enabled = bool(token)
    ad = Adapter(
        name="notion",
        enabled=enabled,
        reason="" if enabled else "NOTION_TOKEN not set",
    )

    async def create_page(args: dict) -> dict:
        import httpx
        parent_id = args.get("parent_id")
        title = args.get("title")
        content = args.get("content", "")
        if not parent_id or not title:
            raise ValueError("notion.create_page requires args.parent_id and args.title")
        url = "https://api.notion.com/v1/pages"
        body = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            },
            "children": [
                {
                    "object": "block", "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]}
                }
            ] if content else []
        }
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json",
                },
                json=body,
            )
        try:
            return {"status": r.status_code, "body": r.json()}
        except Exception:
            return {"status": r.status_code, "raw": r.text[:400]}

    ad.register(AdapterTool(name="create_page", description="Create a Notion page.",
                            schema={"type": "object", "required": ["parent_id", "title"]},
                            handler=create_page))
    return ad

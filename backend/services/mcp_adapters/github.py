"""GitHub adapter — create issues, list PRs."""
from __future__ import annotations

from typing import Callable, Optional

from backend.services.mcp_client import Adapter, AdapterTool


def build(env_get: Callable[[str], Optional[str]]) -> Adapter:
    token = env_get("GITHUB_PAT") or env_get("GITHUB_TOKEN")
    enabled = bool(token)
    ad = Adapter(
        name="github",
        enabled=enabled,
        reason="" if enabled else "GITHUB_PAT/GITHUB_TOKEN not set",
    )

    def _headers():
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def create_issue(args: dict) -> dict:
        import httpx
        repo = args.get("repo")
        title = args.get("title")
        body = args.get("body", "")
        if not repo or not title:
            raise ValueError("github.create_issue requires args.repo and args.title")
        url = f"https://api.github.com/repos/{repo}/issues"
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(url, headers=_headers(), json={"title": title, "body": body})
        try:
            return {"status": r.status_code, "body": r.json()}
        except Exception:
            return {"status": r.status_code, "raw": r.text[:400]}

    async def list_prs(args: dict) -> dict:
        import httpx
        repo = args.get("repo")
        state = args.get("state", "open")
        if not repo:
            raise ValueError("github.list_prs requires args.repo")
        url = f"https://api.github.com/repos/{repo}/pulls?state={state}&per_page=50"
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, headers=_headers())
        try:
            data = r.json()
        except Exception:
            return {"status": r.status_code, "raw": r.text[:400]}
        summary = [{"number": p.get("number"), "title": p.get("title"), "user": (p.get("user") or {}).get("login"), "draft": p.get("draft")} for p in data] if isinstance(data, list) else data
        return {"status": r.status_code, "prs": summary}

    ad.register(AdapterTool(name="create_issue", description="Create a GitHub issue.",
                            schema={"type": "object", "required": ["repo", "title"]},
                            handler=create_issue))
    ad.register(AdapterTool(name="list_prs", description="List PRs on a GitHub repo.",
                            schema={"type": "object", "required": ["repo"]},
                            handler=list_prs))
    return ad

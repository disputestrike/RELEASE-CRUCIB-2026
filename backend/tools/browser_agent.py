"""
Browser Agent - automate browser actions using Playwright.
Can:
- Navigate to URLs
- Take screenshots
- Scrape content
- Fill forms
- Click elements
- Extract data
"""

import base64
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from playwright.async_api import Browser, Page, async_playwright

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from ....agents.base_agent import BaseAgentfrom ssrf_url_validator import validate_url_for_request


class BrowserAgent(BaseAgent):
    """Browser automation agent using Playwright"""

    def __init__(self, llm_client, config, db=None):
        super().__init__(llm_client=llm_client, config=config, db=db)
        self.name = "BrowserAgent"
        self.browser: Browser = None
        self.page: Page = None

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute browser actions.

        Expected context:
        {
            "action": "navigate|screenshot|scrape|fill_form|click",
            "url": "https://example.com",
            "selector": ".some-class",  # For click/scrape
            "form_data": {"name": "value"},  # For fill_form
            "screenshot_path": "screenshot.png"
        }
        """
        action = context.get("action", "navigate")
        known = {"navigate", "screenshot", "scrape", "fill_form", "click"}
        if action not in known:
            return {"error": f"Unknown action: {action}", "success": False}

        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=True)
            self.page = await self.browser.new_page()

            try:
                if action == "navigate":
                    result = await self._navigate(context)
                elif action == "screenshot":
                    result = await self._screenshot(context)
                elif action == "scrape":
                    result = await self._scrape(context)
                elif action == "fill_form":
                    result = await self._fill_form(context)
                elif action == "click":
                    result = await self._click(context)
                else:
                    result = {"error": f"Unknown action: {action}", "success": False}

                await self.browser.close()
                return result

            except Exception as e:
                await self.browser.close()
                return {"error": str(e), "success": False}

    def _validate_url(self, url: str) -> None:
        """SSRF: block private IPs, file:, localhost (unless allowed in config)."""
        allow_private = self.config.get("allow_private_urls", False)
        validate_url_for_request(url, allow_private=allow_private)

    async def _navigate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate to URL (SSRF-safe)."""
        url = context.get("url")
        if not url:
            return {"error": "url is required", "success": False}
        self._validate_url(url)
        await self.page.goto(url)
        title = await self.page.title()
        content = await self.page.content()

        return {
            "url": url,
            "title": title,
            "content_length": len(content),
            "success": True,
        }

    async def _screenshot(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Take screenshot; path is restricted to temp dir (no path traversal)."""
        url = context.get("url")
        if not url:
            return {"error": "url is required", "success": False}
        self._validate_url(url)
        # Always write to temp dir — never use user-provided path for filesystem write
        suffix = (
            Path(context.get("screenshot_path") or "screenshot.png").suffix or ".png"
        )
        if suffix and not suffix.startswith("."):
            suffix = "." + suffix
        fd, path = tempfile.mkstemp(suffix=suffix, prefix="browser_screenshot_")
        try:
            await self.page.goto(url)
            await self.page.screenshot(path=path)
            with open(path, "rb") as f:
                img_bytes = f.read()
                img_base64 = base64.b64encode(img_bytes).decode()
            return {
                "url": url,
                "screenshot_base64": img_base64,
                "success": True,
            }
        finally:
            import os as _os

            try:
                _os.close(fd)
                _os.unlink(path)
            except Exception:
                pass

    async def _scrape(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Scrape content from page (SSRF-safe)."""
        url = context.get("url")
        if not url:
            return {"error": "url is required", "success": False}
        self._validate_url(url)
        selector = context.get("selector", "body")
        await self.page.goto(url)

        # Get text content
        element = await self.page.query_selector(selector)
        if element:
            text = await element.inner_text()
            html = await element.inner_html()
        else:
            text = await self.page.inner_text("body")
            html = await self.page.content()

        return {
            "url": url,
            "selector": selector,
            "text": text,
            "html": html,
            "success": True,
        }

    async def _fill_form(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fill and submit form (SSRF-safe)."""
        url = context.get("url")
        if not url:
            return {"error": "url is required", "success": False}
        self._validate_url(url)
        form_data = context.get("form_data", {})
        await self.page.goto(url)

        # Fill each field
        for selector, value in form_data.items():
            await self.page.fill(selector, value)

        # Submit (assumes there's a submit button)
        submit_selector = context.get("submit_selector", "button[type='submit']")
        await self.page.click(submit_selector)

        # Wait for navigation
        await self.page.wait_for_load_state("networkidle")

        return {
            "url": url,
            "form_filled": list(form_data.keys()),
            "current_url": self.page.url,
            "success": True,
        }

    async def _click(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Click element (SSRF-safe)."""
        url = context.get("url")
        if not url:
            return {"error": "url is required", "success": False}
        self._validate_url(url)
        selector = context.get("selector")
        await self.page.goto(url)
        await self.page.click(selector)
        await self.page.wait_for_load_state("networkidle")

        return {
            "url": url,
            "clicked": selector,
            "current_url": self.page.url,
            "success": True,
        }

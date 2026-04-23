import os
from typing import Any, Dict, List, Optional

from tavily import TavilyClient

def get_tools() -> Dict[str, Any]:
    """Return a dictionary of available tools."""
    tools = {}
    tavily_api_key = os.environ.get("TAVILY_API_KEY")
    if tavily_api_key:
        tavily = TavilyClient(api_key=tavily_api_key)
        def tavily_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
            """Search the web using Tavily API."""
            results = tavily.search(query=query, max_results=max_results)
            return results.get("results", [])
        tools["tavily_search"] = tavily_search
    return tools

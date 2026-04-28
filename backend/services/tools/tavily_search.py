"""Tavily search tool integration for ReAct loop."""

import os
from typing import Any, Dict, List, Optional


def get_tools() -> Dict[str, Any]:
    """Return a dictionary of available tools for the ReAct loop."""
    tools = {}
    tavily_api_key = os.environ.get("TAVILY_API_KEY")
    
    if tavily_api_key:
        try:
            from tavily import TavilyClient
            
            tavily = TavilyClient(api_key=tavily_api_key)
            
            async def tavily_search(name: str, args: Dict[str, Any]) -> List[Dict[str, Any]]:
                """Search the web using Tavily API."""
                query = args.get("query", "")
                max_results = args.get("max_results", 5)
                
                if not query:
                    return {"error": "query parameter is required"}
                
                try:
                    results = tavily.search(query=query, max_results=max_results)
                    return results.get("results", [])
                except Exception as e:
                    return {"error": str(e)}
            
            tavily_search.__doc__ = "Search the web for current information using Tavily API"
            tools["tavily_search"] = tavily_search
        except ImportError:
            pass
    
    return tools

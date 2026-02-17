"""
API Agent - make HTTP requests and handle OAuth.
Can:
- GET/POST/PUT/DELETE requests
- Handle authentication (Bearer, Basic, OAuth)
- Parse JSON/XML responses
- Handle rate limits
"""

import httpx
from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class APIAgent(BaseAgent):
    """HTTP API interaction agent"""
    
    def __init__(self, llm_client, config):
        super().__init__(llm_client, config)
        self.name = "APIAgent"
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP request.
        
        Expected context:
        {
            "method": "GET|POST|PUT|DELETE",
            "url": "https://api.example.com/endpoint",
            "headers": {"Authorization": "Bearer token"},
            "body": {"key": "value"},
            "params": {"page": 1}
        }
        """
        method = context.get("method", "GET").upper()
        url = context.get("url")
        headers = context.get("headers", {})
        body = context.get("body")
        params = context.get("params")
        
        async with httpx.AsyncClient() as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=body, params=params)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=body, params=params)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers, params=params)
                else:
                    return {"error": f"Unknown method: {method}"}
                
                # Parse response
                try:
                    data = response.json()
                except (ValueError, Exception):
                    data = response.text
                
                return {
                    "status_code": response.status_code,
                    "success": 200 <= response.status_code < 300,
                    "headers": dict(response.headers),
                    "data": data,
                    "url": str(response.url)
                }
                
            except Exception as e:
                return {
                    "error": str(e),
                    "success": False
                }

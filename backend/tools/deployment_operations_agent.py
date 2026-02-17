"""
Deployment Operations Agent - deploy to cloud platforms.
Supports: Vercel, Railway, Netlify
"""

import httpx
import subprocess
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class DeploymentOperationsAgent(BaseAgent):
    """Cloud deployment agent"""
    
    def __init__(self, llm_client, config):
        super().__init__(llm_client, config)
        self.name = "DeploymentOperationsAgent"
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy application.
        
        Expected context:
        {
            "platform": "vercel|railway|netlify",
            "project_path": "./my-app",
            "config": {"env": {...}, "build_command": "npm run build"}
        }
        """
        platform = context.get("platform", "vercel")
        
        try:
            if platform == "vercel":
                result = await self._deploy_vercel(context)
            elif platform == "railway":
                result = await self._deploy_railway(context)
            elif platform == "netlify":
                result = await self._deploy_netlify(context)
            else:
                result = {"error": f"Unknown platform: {platform}"}
            
            return result
            
        except Exception as e:
            return {"error": str(e), "success": False}
    
    async def _deploy_vercel(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to Vercel"""
        project_path = context.get("project_path")
        
        # Use Vercel CLI
        cmd = ["vercel", "--yes", "--cwd", project_path]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            # Parse URL from output
            output = process.stdout
            url = output.split("https://")[-1].split()[0] if "https://" in output else "unknown"
            
            return {
                "platform": "vercel",
                "url": f"https://{url}",
                "success": True,
                "output": output
            }
        else:
            return {
                "error": process.stderr,
                "success": False
            }
    
    async def _deploy_railway(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to Railway"""
        # Railway deployment logic
        project_path = context.get("project_path")
        
        cmd = ["railway", "up", "--detach"]
        process = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True)
        
        if process.returncode == 0:
            return {
                "platform": "railway",
                "success": True,
                "output": process.stdout
            }
        else:
            return {
                "error": process.stderr,
                "success": False
            }
    
    async def _deploy_netlify(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to Netlify"""
        project_path = context.get("project_path")
        
        cmd = ["netlify", "deploy", "--prod", "--dir", project_path]
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            output = process.stdout
            url = output.split("https://")[-1].split()[0] if "https://" in output else "unknown"
            
            return {
                "platform": "netlify",
                "url": f"https://{url}",
                "success": True,
                "output": output
            }
        else:
            return {
                "error": process.stderr,
                "success": False
            }

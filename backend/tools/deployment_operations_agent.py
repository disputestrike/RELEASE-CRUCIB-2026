"""
Deployment Operations Agent - deploy to cloud platforms.
Supports: Vercel, Railway, Netlify
project_path must resolve to a path under config["workspace_root"] (path traversal protection).
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from ....agents.base_agent import BaseAgent

def _resolve_project_path(workspace_root: Path, project_path: str) -> Path:
    """Resolve project_path strictly under workspace_root. Raises ValueError if outside."""
    base = workspace_root.resolve()
    path = (base / project_path.strip().lstrip("/")).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        raise ValueError(f"project_path must be under workspace: {project_path}")
    if not path.exists():
        raise ValueError(f"project_path does not exist: {path}")
    return path


class DeploymentOperationsAgent(BaseAgent):
    """Cloud deployment agent"""

    def __init__(self, llm_client, config, db=None):
        super().__init__(llm_client, config)
        self.name = "DeploymentOperationsAgent"
        self.workspace_root = Path(
            config.get("workspace_root", Path(__file__).parent.parent / "workspace")
        ).resolve()

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
        """Deploy to Vercel (project_path validated under workspace)."""
        project_path = _resolve_project_path(
            self.workspace_root, context.get("project_path") or "."
        )
        # Use Vercel CLI
        cmd = ["vercel", "--yes", "--cwd", str(project_path)]
        process = subprocess.run(
            cmd, cwd=str(project_path), capture_output=True, text=True
        )
        if process.returncode == 0:
            # Parse URL from output
            output = process.stdout
            url = (
                output.split("https://")[-1].split()[0]
                if "https://" in output
                else "unknown"
            )

            return {
                "platform": "vercel",
                "url": f"https://{url}",
                "success": True,
                "output": output,
            }
        else:
            return {"error": process.stderr, "success": False}

    async def _deploy_railway(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to Railway (project_path validated under workspace)."""
        project_path = _resolve_project_path(
            self.workspace_root, context.get("project_path") or "."
        )
        cmd = ["railway", "up", "--detach"]
        process = subprocess.run(
            cmd, cwd=str(project_path), capture_output=True, text=True
        )

        if process.returncode == 0:
            return {"platform": "railway", "success": True, "output": process.stdout}
        else:
            return {"error": process.stderr, "success": False}

    async def _deploy_netlify(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to Netlify (project_path validated under workspace)."""
        project_path = _resolve_project_path(
            self.workspace_root, context.get("project_path") or "."
        )
        cmd = ["netlify", "deploy", "--prod", "--dir", str(project_path)]
        process = subprocess.run(
            cmd, cwd=str(project_path), capture_output=True, text=True
        )

        if process.returncode == 0:
            output = process.stdout
            url = (
                output.split("https://")[-1].split()[0]
                if "https://" in output
                else "unknown"
            )

            return {
                "platform": "netlify",
                "url": f"https://{url}",
                "success": True,
                "output": output,
            }
        else:
            return {"error": process.stderr, "success": False}

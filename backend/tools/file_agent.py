"""
File Agent - perform file system operations.
Can:
- Read files
- Write files
- Move/rename files
- Delete files
- List directory contents
- Create directories
"""

from pathlib import Path
import shutil
from typing import Dict, Any, List
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class FileAgent(BaseAgent):
    """File system operations agent"""
    
    def __init__(self, llm_client, config):
        super().__init__(llm_client, config)
        self.name = "FileAgent"
        self.workspace = Path(config.get("workspace", "./workspace"))
        self.workspace.mkdir(exist_ok=True)
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute file operations.
        
        Expected context:
        {
            "action": "read|write|move|delete|list|mkdir",
            "path": "path/to/file",
            "content": "...",  # For write
            "destination": "...",  # For move
        }
        """
        action = context.get("action")
        
        try:
            if action == "read":
                result = self._read_file(context)
            elif action == "write":
                result = self._write_file(context)
            elif action == "move":
                result = self._move_file(context)
            elif action == "delete":
                result = self._delete_file(context)
            elif action == "list":
                result = self._list_directory(context)
            elif action == "mkdir":
                result = self._create_directory(context)
            else:
                result = {"error": f"Unknown action: {action}", "success": False}
            
            return result
            
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def _read_file(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Read file content"""
        filepath = self.workspace / context.get("path")
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        return {
            "path": str(filepath),
            "content": content,
            "size": filepath.stat().st_size,
            "success": True
        }
    
    def _write_file(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to file"""
        filepath = self.workspace / context.get("path")
        content = context.get("content", "")
        
        # Create parent directories
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        return {
            "path": str(filepath),
            "size": filepath.stat().st_size,
            "success": True
        }
    
    def _move_file(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Move/rename file"""
        source = self.workspace / context.get("path")
        destination = self.workspace / context.get("destination")
        
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        
        return {
            "source": str(source),
            "destination": str(destination),
            "success": True
        }
    
    def _delete_file(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Delete file"""
        filepath = self.workspace / context.get("path")
        
        if filepath.is_file():
            filepath.unlink()
        elif filepath.is_dir():
            shutil.rmtree(filepath)
        
        return {
            "path": str(filepath),
            "success": True
        }
    
    def _list_directory(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List directory contents"""
        dirpath = self.workspace / context.get("path", ".")
        
        files = []
        for item in dirpath.iterdir():
            files.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0
            })
        
        return {
            "path": str(dirpath),
            "files": files,
            "count": len(files),
            "success": True
        }
    
    def _create_directory(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create directory"""
        dirpath = self.workspace / context.get("path")
        dirpath.mkdir(parents=True, exist_ok=True)
        
        return {
            "path": str(dirpath),
            "success": True
        }

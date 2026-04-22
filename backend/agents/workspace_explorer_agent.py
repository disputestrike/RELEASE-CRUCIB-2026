"""
Workspace Explorer Agent: Discovers, indexes, and searches across codebase.
Provides context about project structure, dependencies, and relationships.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import AgentValidationError, BaseAgent
from agents.registry import AgentRegistry

import logging

logger = logging.getLogger(__name__)


@AgentRegistry.register
class WorkspaceExplorerAgent(BaseAgent):
    """
    Explores and indexes workspace for intelligent navigation and search.
    
    Input:
        - action: str (discover|search|analyze_dependencies|locate_pattern|project_map)
        - path: str (root path to explore, optional)
        - query: str (search query, for search action)
        - pattern: str (regex pattern to match, for locate_pattern)
    
    Output:
        - For discover: {files: list, directories: list, total_size: int}
        - For search: {results: list of matching files with snippets}
        - For analyze_dependencies: {dependencies: dict, import_map: dict}
        - For locate_pattern: {matches: list with location and context}
        - For project_map: {structure: tree, stats: dict}
    """

    def __init__(self, llm_client: Optional[Any] = None, config: Optional[Dict[str, Any]] = None, db: Optional[Any] = None):
        super().__init__(llm_client=llm_client, config=config, db=db)
        self.name = "WorkspaceExplorerAgent"
        self.workspace = Path(config.get("workspace", "./workspace")).resolve() if config else Path.cwd()
        self.cached_index = {}
        self.file_extensions = {
            "python": [".py"],
            "javascript": [".js", ".jsx", ".ts", ".tsx"],
            "json": [".json"],
            "yaml": [".yml", ".yaml"],
            "markdown": [".md"],
            "other": []
        }

    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)

        # Runtime may route exploratory work without explicit action metadata.
        # Derive a deterministic default instead of hard-failing.
        if "action" not in context:
            if context.get("query"):
                context["action"] = "search"
            elif context.get("pattern"):
                context["action"] = "locate_pattern"
            elif context.get("user_prompt"):
                context["action"] = "project_map"
            else:
                context["action"] = "discover"

        action = context["action"]
        valid_actions = ["discover", "search", "analyze_dependencies", "locate_pattern", "project_map", "symbol_index", "file_summary"]
        if action not in valid_actions:
            raise AgentValidationError(f"{self.name}: action must be one of {valid_actions}")

        if action == "search" and "query" not in context:
            context["query"] = str(context.get("user_prompt") or context.get("request") or "project").strip() or "project"

        if action == "locate_pattern" and "pattern" not in context:
            context["pattern"] = str(context.get("query") or context.get("user_prompt") or "TODO").strip() or "TODO"

        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        if "error" in result:
            return True  # Allow error responses
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workspace exploration"""
        action = context["action"]
        path = context.get("path", str(self.workspace))

        try:
            if action == "discover":
                result = self._discover_files(path)
            elif action == "search":
                query = context.get("query", "")
                result = await self._search_files(query, path)
            elif action == "analyze_dependencies":
                result = self._analyze_dependencies(path)
            elif action == "locate_pattern":
                pattern = context.get("pattern", "")
                result = self._locate_pattern(pattern, path)
            elif action == "project_map":
                result = self._generate_project_map(path)
            elif action == "symbol_index":
                result = self._symbol_index(path)
            elif action == "file_summary":
                target = context.get("target") or context.get("file") or path
                result = self._file_summary(target)
            else:
                result = {"error": f"Unknown action: {action}"}

            if self.performance:
                self.performance.track_execution(self.name, "success", 1)

            return result

        except Exception as e:
            logger.error(f"{self.name} execution error: {str(e)}")
            if self.performance:
                self.performance.track_execution(self.name, "error", 0)
            return {"error": str(e)}

    def _discover_files(self, root_path: str, max_depth: int = 5) -> Dict[str, Any]:
        """Discover files and directories in workspace"""
        root = Path(root_path)
        if not root.exists():
            return {"error": f"Path does not exist: {root_path}", "files": [], "directories": []}

        files = []
        directories = []
        total_size = 0
        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".env"}

        def traverse(current_path: Path, depth: int):
            nonlocal total_size
            if depth > max_depth:
                return

            try:
                for item in current_path.iterdir():
                    if item.name.startswith(".") and item.name not in {".gitignore", ".env"}:
                        continue

                    if item.is_dir():
                        if item.name not in ignore_dirs:
                            directories.append(str(item.relative_to(root)))
                            traverse(item, depth + 1)
                    else:
                        try:
                            size = item.stat().st_size
                            total_size += size
                            files.append({
                                "path": str(item.relative_to(root)),
                                "size": size,
                                "type": item.suffix,
                            })
                        except Exception:
                            pass
            except PermissionError:
                pass

        traverse(root, 0)

        return {
            "root": str(root),
            "files": sorted(files, key=lambda x: x["path"])[:100],  # Limit to 100
            "directories": sorted(directories)[:50],
            "total_size": total_size,
            "file_count": len(files),
            "directory_count": len(directories),
        }

    async def _search_files(self, query: str, root_path: str) -> Dict[str, Any]:
        """Search for files matching query"""
        root = Path(root_path)
        results = []
        query_lower = query.lower()

        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}

        def search_recursive(current_path: Path):
            try:
                for item in current_path.iterdir():
                    if item.is_dir():
                        if item.name not in ignore_dirs:
                            search_recursive(item)
                    else:
                        # Match filename or content
                        if query_lower in item.name.lower():
                            results.append({
                                "path": str(item.relative_to(root)),
                                "type": "filename_match",
                                "relevance": "high" if item.name.lower() == query_lower else "medium",
                            })
                        elif item.suffix in [".py", ".js", ".ts", ".md"]:
                            try:
                                content = item.read_text(encoding="utf-8", errors="ignore")
                                if query_lower in content.lower():
                                    lines = content.split("\n")
                                    matches = []
                                    for i, line in enumerate(lines):
                                        if query_lower in line.lower():
                                            matches.append({
                                                "line_num": i + 1,
                                                "snippet": line.strip()[:100],
                                            })
                                    if matches:
                                        results.append({
                                            "path": str(item.relative_to(root)),
                                            "type": "content_match",
                                            "matches": matches[:3],  # Top 3 matches
                                        })
                            except Exception:
                                pass
            except PermissionError:
                pass

        search_recursive(root)
        return {
            "query": query,
            "results": results[:20],  # Limit to 20 results
            "total_matches": len(results),
        }

    def _analyze_dependencies(self, root_path: str) -> Dict[str, Any]:
        """Analyze project dependencies and imports"""
        root = Path(root_path)
        dependencies = {}
        import_map = {}

        # Check for common dependency files
        dep_files = {
            "requirements.txt": "python",
            "package.json": "nodejs",
            "Gemfile": "ruby",
            "go.mod": "go",
            "Cargo.toml": "rust",
        }

        for filename, language in dep_files.items():
            dep_file = root / filename
            if dep_file.exists():
                try:
                    content = dep_file.read_text(encoding="utf-8", errors="ignore")
                    deps = [line.strip() for line in content.split("\n")
                           if line.strip() and not line.startswith("#")]
                    dependencies[language] = deps[:20]  # First 20 deps
                except Exception:
                    pass

        # Try to extract imports from Python files
        python_files = list(root.glob("**/*.py"))[:10]  # Sample first 10 py files
        for py_file in python_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")
                imports = [line for line in lines if line.startswith(("import ", "from "))]
                if imports:
                    import_map[str(py_file.relative_to(root))] = imports[:5]
            except Exception:
                pass

        return {
            "dependencies": dependencies,
            "import_map": import_map,
            "has_pyproject": (root / "pyproject.toml").exists(),
            "has_package_json": (root / "package.json").exists(),
            "has_setup_py": (root / "setup.py").exists(),
        }

    def _locate_pattern(self, pattern: str, root_path: str) -> Dict[str, Any]:
        """Locate files matching regex pattern"""
        import re

        root = Path(root_path)
        matches = []

        try:
            regex = re.compile(pattern)
        except Exception as e:
            return {"error": f"Invalid regex pattern: {str(e)}", "matches": []}

        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}

        def search_recursive(current_path: Path):
            try:
                for item in current_path.iterdir():
                    if item.is_dir():
                        if item.name not in ignore_dirs:
                            search_recursive(item)
                    else:
                        try:
                            content = item.read_text(encoding="utf-8", errors="ignore")
                            for match in regex.finditer(content):
                                start_line = content[:match.start()].count("\n") + 1
                                matches.append({
                                    "file": str(item.relative_to(root)),
                                    "line": start_line,
                                    "match": match.group(0)[:50],
                                })
                                if len(matches) >= 30:
                                    return
                        except Exception:
                            pass
            except PermissionError:
                pass

        search_recursive(root)
        return {
            "pattern": pattern,
            "matches": matches,
            "total_matches": len(matches),
        }

    def _generate_project_map(self, root_path: str) -> Dict[str, Any]:
        """Generate visual project structure map"""
        root = Path(root_path)
        structure = []
        stats = {
            "total_files": 0,
            "total_dirs": 0,
            "by_extension": {},
            "by_language": {}
        }

        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}

        def build_tree(current_path: Path, prefix: str = "", max_depth: int = 4, current_depth: int = 0):
            if current_depth > max_depth:
                return

            try:
                items = sorted(current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                for i, item in enumerate(items):
                    if item.name.startswith(".") and item.name not in {".gitignore"}:
                        continue

                    is_last = i == len(items) - 1
                    current_prefix = "└── " if is_last else "├── "
                    next_prefix = prefix + ("    " if is_last else "│   ")

                    if item.is_dir():
                        if item.name not in ignore_dirs:
                            structure.append(f"{prefix}{current_prefix}{item.name}/")
                            stats["total_dirs"] += 1
                            build_tree(item, next_prefix, max_depth, current_depth + 1)
                    else:
                        structure.append(f"{prefix}{current_prefix}{item.name}")
                        stats["total_files"] += 1
                        ext = item.suffix or "no_extension"
                        stats["by_extension"][ext] = stats["by_extension"].get(ext, 0) + 1

                        # Categorize by language
                        if ext in [".py"]:
                            stats["by_language"]["python"] = stats["by_language"].get("python", 0) + 1
                        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
                            stats["by_language"]["javascript"] = stats["by_language"].get("javascript", 0) + 1
                        elif ext in [".md"]:
                            stats["by_language"]["markdown"] = stats["by_language"].get("markdown", 0) + 1

            except PermissionError:
                pass

        structure.append(str(root.name) + "/")
        build_tree(root)

        return {
            "project_root": str(root),
            "structure": structure[:100],  # Limit to 100 lines
            "stats": stats,
        }

    def _symbol_index(self, root_path: str) -> Dict[str, Any]:
        """Build a lightweight symbol index (classes, functions) for .py files via AST."""
        import ast as _ast
        root = Path(root_path)
        if not root.exists():
            return {"error": f"Path does not exist: {root_path}", "symbols": {}}

        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}
        index: Dict[str, List[Dict[str, Any]]] = {}
        total = 0

        def walk(p: Path):
            nonlocal total
            try:
                for item in p.iterdir():
                    if item.is_dir() and item.name not in ignore_dirs and not item.name.startswith("."):
                        walk(item)
                        continue
                    if item.suffix != ".py":
                        continue
                    try:
                        tree = _ast.parse(item.read_text(encoding="utf-8", errors="ignore"))
                    except Exception:
                        continue
                    syms: List[Dict[str, Any]] = []
                    for node in _ast.walk(tree):
                        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                            syms.append({"kind": "function", "name": node.name, "line": getattr(node, "lineno", 0)})
                        elif isinstance(node, _ast.ClassDef):
                            syms.append({"kind": "class", "name": node.name, "line": getattr(node, "lineno", 0)})
                    if syms:
                        try:
                            rel = str(item.relative_to(root))
                        except Exception:
                            rel = str(item)
                        index[rel] = syms[:50]
                        total += len(syms)
                        if len(index) >= 100:
                            return
            except PermissionError:
                return

        walk(root)
        return {"root": str(root), "symbols": index, "file_count": len(index), "symbol_count": total}

    def _file_summary(self, target: str) -> Dict[str, Any]:
        """Return a quick summary (size, line count, first docstring, top imports) for a single file."""
        import ast as _ast
        p = Path(target)
        if not p.exists() or not p.is_file():
            return {"error": f"Not a file: {target}"}
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return {"error": f"read error: {e}"}
        summary: Dict[str, Any] = {
            "path": str(p),
            "size": p.stat().st_size,
            "lines": content.count("\n") + 1,
        }
        if p.suffix == ".py":
            try:
                tree = _ast.parse(content)
                ds = _ast.get_docstring(tree)
                if ds:
                    summary["docstring"] = ds[:400]
                summary["imports"] = [
                    n.names[0].name if isinstance(n, _ast.Import) else f"{n.module}.{n.names[0].name}"
                    for n in tree.body
                    if isinstance(n, (_ast.Import, _ast.ImportFrom)) and getattr(n, "names", None)
                ][:15]
                summary["symbols"] = [
                    {"kind": "class" if isinstance(n, _ast.ClassDef) else "function", "name": n.name}
                    for n in tree.body
                    if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef))
                ][:30]
            except Exception:
                pass
        else:
            # Generic summary: first non-empty 5 lines
            preview = [ln for ln in content.splitlines() if ln.strip()][:5]
            summary["preview"] = preview
        return summary

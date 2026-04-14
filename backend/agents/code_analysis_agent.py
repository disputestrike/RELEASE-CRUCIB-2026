"""
Code Analysis Agent: Analyzes code structure, detects issues, provides insights.
Uses AST parsing, type checking, linting to understand code deeply.
"""

import ast
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import AgentValidationError, BaseAgent
from agents.registry import AgentRegistry

logger = logging.getLogger(__name__)


@AgentRegistry.register
class CodeAnalysisAgent(BaseAgent):
    """
    Analyzes code files for structure, issues, patterns, and refactoring opportunities.
    
    Input:
        - code_content: str (Python code to analyze)
        - file_path: str (optional, for context)
        - analysis_type: str (structure|issues|complexity|patterns|all)
    
    Output:
        - structure: dict with classes, functions, imports
        - issues: list of detected problems (unused vars, type hints, security issues)
        - complexity: dict with cyclomatic complexity, lines of code stats
        - patterns: list of detected design patterns
        - suggestions: list of refactoring suggestions
        - quality_score: float (0-100)
    """

    def __init__(self, llm_client: Optional[Any] = None, config: Optional[Dict[str, Any]] = None, db: Optional[Any] = None):
        super().__init__(llm_client=llm_client, config=config, db=db)
        self.name = "CodeAnalysisAgent"

    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)

        if "code_content" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'code_content'")

        code = context["code_content"]
        if not isinstance(code, str) or len(code) < 10:
            raise AgentValidationError(f"{self.name}: code_content must be string with >10 chars")

        analysis_type = context.get("analysis_type", "all")
        valid_types = ["structure", "issues", "complexity", "patterns", "all"]
        if analysis_type not in valid_types:
            raise AgentValidationError(f"{self.name}: analysis_type must be one of {valid_types}")

        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)

        required = ["structure", "issues", "complexity", "patterns", "suggestions", "quality_score"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required output field '{field}'")

        if not isinstance(result["quality_score"], (int, float)) or not (0 <= result["quality_score"] <= 100):
            raise AgentValidationError(f"{self.name}: quality_score must be 0-100")

        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code analysis"""
        code_content = context["code_content"]
        file_path = context.get("file_path", "unknown.py")
        analysis_type = context.get("analysis_type", "all")

        try:
            # Parse the code into AST
            tree = ast.parse(code_content)

            # Perform different analyses
            structure = self._analyze_structure(tree) if analysis_type in ["structure", "all"] else {}
            issues = self._analyze_issues(tree, code_content) if analysis_type in ["issues", "all"] else []
            complexity_stats = self._analyze_complexity(tree, code_content) if analysis_type in ["complexity", "all"] else {}
            patterns = self._detect_patterns(tree) if analysis_type in ["patterns", "all"] else []

            # Use LLM for suggestions if available
            suggestions = []
            if self.llm_client:
                suggestions = await self._get_suggestions(code_content, structure, issues)

            # Calculate quality score
            quality_score = self._calculate_quality_score(structure, issues, complexity_stats)

            result = {
                "structure": structure,
                "issues": issues,
                "complexity": complexity_stats,
                "patterns": patterns,
                "suggestions": suggestions,
                "quality_score": quality_score,
                "file_path": file_path,
            }

            if self.performance:
                self.performance.track_execution(self.name, "success", len(code_content))

            return result

        except SyntaxError as e:
            return {
                "structure": {},
                "issues": [{"type": "syntax_error", "message": str(e), "line": e.lineno}],
                "complexity": {},
                "patterns": [],
                "suggestions": ["Fix syntax error first before analysis"],
                "quality_score": 0,
                "file_path": file_path,
            }
        except Exception as e:
            logger.error(f"{self.name} execution error: {str(e)}")
            if self.performance:
                self.performance.track_execution(self.name, "error", 0)
            raise

    def _analyze_structure(self, tree: ast.AST) -> Dict[str, Any]:
        """Extract structural information from AST"""
        structure = {
            "imports": [],
            "classes": [],
            "functions": [],
            "async_functions": [],
            "decorators": [],
            "total_lines": 0,
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    structure["imports"].append({"name": alias.name, "type": "import"})
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    structure["imports"].append({
                        "name": alias.name,
                        "from": node.module,
                        "type": "from_import",
                    })
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                structure["classes"].append({
                    "name": node.name,
                    "methods": methods,
                    "decorators": [self._node_to_string(d) for d in node.decorator_list],
                    "lineno": node.lineno,
                })
            elif isinstance(node, ast.FunctionDef):
                structure["functions"].append({
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "returns": self._node_to_string(node.returns) if node.returns else None,
                    "decorators": [self._node_to_string(d) for d in node.decorator_list],
                    "lineno": node.lineno,
                })
            elif isinstance(node, ast.AsyncFunctionDef):
                structure["async_functions"].append({
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "lineno": node.lineno,
                })

        return structure

    def _analyze_issues(self, tree: ast.AST, code: str) -> List[Dict[str, Any]]:
        """Detect common issues in code"""
        issues = []
        lines = code.split("\n")

        for node in ast.walk(tree):
            # Detect unused variables
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        if var_name.startswith("_"):
                            continue
                        # Check if used (simplified check)
                        usage_count = sum(1 for n in ast.walk(tree)
                                         if isinstance(n, ast.Name) and n.id == var_name and n != target)
                        if usage_count == 0:
                            issues.append({
                                "type": "unused_variable",
                                "name": var_name,
                                "line": node.lineno,
                                "severity": "warning",
                            })

            # Detect missing type hints in functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.returns:
                    issues.append({
                        "type": "missing_return_type",
                        "function": node.name,
                        "line": node.lineno,
                        "severity": "info",
                    })
                for arg in node.args.args:
                    if not arg.annotation:
                        issues.append({
                            "type": "missing_arg_type",
                            "function": node.name,
                            "arg": arg.arg,
                            "line": node.lineno,
                            "severity": "info",
                        })

            # Detect bare except clauses
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append({
                        "type": "bare_except",
                        "line": node.lineno,
                        "severity": "error",
                        "message": "Avoid bare 'except' - catch specific exceptions",
                    })

            # Detect long functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lines = node.end_lineno - node.lineno if node.end_lineno else 0
                if func_lines > 50:
                    issues.append({
                        "type": "long_function",
                        "function": node.name,
                        "lines": func_lines,
                        "line": node.lineno,
                        "severity": "warning",
                        "message": f"Function is {func_lines} lines (consider refactoring)",
                    })

        return issues

    def _analyze_complexity(self, tree: ast.AST, code: str) -> Dict[str, Any]:
        """Analyze code complexity metrics"""
        lines = code.split("\n")
        non_empty_lines = len([l for l in lines if l.strip()])
        comment_lines = len([l for l in lines if l.strip().startswith("#")])

        # Cyclomatic complexity (simplified)
        cyclomatic = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.BoolOp)):
                cyclomatic += 1

        return {
            "cyclomatic_complexity": cyclomatic,
            "total_lines": len(lines),
            "non_empty_lines": non_empty_lines,
            "comment_lines": comment_lines,
            "comment_ratio": comment_lines / non_empty_lines if non_empty_lines > 0 else 0,
        }

    def _detect_patterns(self, tree: ast.AST) -> List[Dict[str, str]]:
        """Detect design patterns in code"""
        patterns = []

        # Check for singleton pattern
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                has_instance = False
                has_new = False
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == "instance":
                                has_instance = True
                    if isinstance(item, ast.FunctionDef) and item.name == "__new__":
                        has_new = True

                if has_instance or has_new:
                    patterns.append({"pattern": "Singleton", "class": node.name})

        # Check for decorator pattern
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.decorator_list:
                patterns.append({
                    "pattern": "Decorator",
                    "function": node.name,
                    "decorators": len(node.decorator_list),
                })

        return patterns

    async def _get_suggestions(self, code: str, structure: Dict, issues: List) -> List[str]:
        """Use LLM to generate refactoring suggestions"""
        if not self.llm_client:
            return []

        try:
            prompt = f"""Analyze this code and provide 3-5 specific refactoring suggestions:

Structure: {json.dumps(structure, default=str)[:500]}
Issues found: {json.dumps(issues, default=str)[:500]}

Code snippet:
{code[:500]}

Provide concise, actionable suggestions."""

            response = await self.llm_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            
            suggestions_text = response.content[0].text if response.content else ""
            return [s.strip() for s in suggestions_text.split("\n") if s.strip()][:5]

        except Exception as e:
            logger.error(f"Error getting LLM suggestions: {str(e)}")
            return []

    def _calculate_quality_score(self, structure: Dict, issues: List, complexity: Dict) -> float:
        """Calculate code quality score (0-100)"""
        score = 100.0

        # Deduct for issues
        for issue in issues:
            if issue.get("severity") == "error":
                score -= 20
            elif issue.get("severity") == "warning":
                score -= 10
            elif issue.get("severity") == "info":
                score -= 2

        # Deduct for high complexity
        cyclomatic = complexity.get("cyclomatic_complexity", 1)
        if cyclomatic > 10:
            score -= 15
        elif cyclomatic > 5:
            score -= 5

        # Bonus for comments
        comment_ratio = complexity.get("comment_ratio", 0)
        if comment_ratio > 0.1:
            score += 5

        return max(0, min(100, score))

    @staticmethod
    def _node_to_string(node: Optional[ast.AST]) -> str:
        """Convert AST node to string representation"""
        if node is None:
            return ""
        try:
            return ast.unparse(node)
        except Exception:
            return str(type(node).__name__)

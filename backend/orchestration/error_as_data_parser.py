"""
Error-as-Data Parser - Converts failures into structured repair signals.

Treats errors as navigation signals, not stop signs.
"""

import re
import traceback
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class ErrorType(Enum):
    """Types of errors that can be parsed and repaired."""
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    BUILD_ERROR = "build_error"
    RUNTIME_ERROR = "runtime_error"
    CONTRACT_VIOLATION = "contract_violation"
    MISSING_FILE = "missing_file"
    MISSING_ROUTE = "missing_route"
    VERIFIER_FAILED = "verifier_failed"
    UNKNOWN = "unknown"


@dataclass
class StructuredError:
    """
    A parsed error with all information needed for repair.
    
    This is the "error-as-data" representation that enables
    intelligent routing to repair agents.
    """
    error_type: ErrorType
    raw_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    
    # Parsed components
    missing_import: Optional[str] = None  # For import errors
    syntax_detail: Optional[str] = None  # For syntax errors
    expected_token: Optional[str] = None  # For syntax errors
    
    # Contract mapping
    affected_contract_item: Optional[str] = None  # e.g., "required_files:client/src/main.tsx"
    affected_contract_type: Optional[str] = None  # e.g., "required_files"
    
    # Stack trace (if available)
    stack_trace: Optional[List[str]] = None
    
    # Original error object (for reference)
    original_error: Optional[Exception] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": self.error_type.value,
            "raw_message": self.raw_message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "missing_import": self.missing_import,
            "syntax_detail": self.syntax_detail,
            "expected_token": self.expected_token,
            "affected_contract_item": self.affected_contract_item,
            "affected_contract_type": self.affected_contract_type,
            "stack_trace": self.stack_trace
        }


class ErrorAsDataParser:
    """
    Parses various error types into StructuredError objects.
    
    This enables the system to route errors to appropriate repair agents
    instead of just failing.
    """
    
    def parse(self, error: Exception, context: Optional[Dict] = None) -> StructuredError:
        """
        Parse an exception into a StructuredError.
        
        Args:
            error: The original exception
            context: Additional context (e.g., file being processed, contract item)
            
        Returns:
            StructuredError with all repair-relevant information
        """
        error_str = str(error)
        error_type = self._classify_error(error, error_str)
        
        # Parse based on error type
        if error_type == ErrorType.SYNTAX_ERROR:
            return self._parse_syntax_error(error, error_str, context)
        elif error_type == ErrorType.IMPORT_ERROR:
            return self._parse_import_error(error, error_str, context)
        elif error_type == ErrorType.BUILD_ERROR:
            return self._parse_build_error(error, error_str, context)
        elif error_type == ErrorType.MISSING_FILE:
            return self._parse_missing_file_error(error, error_str, context)
        elif error_type == ErrorType.MISSING_ROUTE:
            return self._parse_missing_route_error(error, error_str, context)
        else:
            return self._parse_generic_error(error, error_str, context)
    
    def parse_build_output(self, build_output: str, contract: Any) -> List[StructuredError]:
        """
        Parse build output (stderr) into multiple StructuredErrors.
        
        A single build can produce multiple errors.
        """
        errors = []
        
        # Look for TypeScript/JavaScript errors
        ts_errors = self._extract_typescript_errors(build_output)
        errors.extend(ts_errors)
        
        # Look for Python errors
        py_errors = self._extract_python_errors(build_output)
        errors.extend(py_errors)
        
        # Look for missing module errors
        module_errors = self._extract_module_errors(build_output)
        errors.extend(module_errors)
        
        # Look for contract violations mentioned in output
        contract_errors = self._extract_contract_violations(build_output, contract)
        errors.extend(contract_errors)
        
        return errors
    
    def _classify_error(self, error: Exception, error_str: str) -> ErrorType:
        """Classify the error type from the exception."""
        error_name = type(error).__name__
        
        # Python syntax errors
        if error_name == "SyntaxError":
            return ErrorType.SYNTAX_ERROR
        
        # Import errors
        if error_name in ["ImportError", "ModuleNotFoundError"]:
            return ErrorType.IMPORT_ERROR
        
        # File not found
        if error_name == "FileNotFoundError":
            return ErrorType.MISSING_FILE
        
        # Build errors (often generic exceptions with specific messages)
        if any(kw in error_str.lower() for kw in ["build failed", "compilation failed", "webpack", "esbuild"]):
            return ErrorType.BUILD_ERROR
        
        # Missing route (often from router or contract check)
        if any(kw in error_str.lower() for kw in ["missing route", "route not found", "no route"]):
            return ErrorType.MISSING_ROUTE
        
        # Contract violations
        if any(kw in error_str.lower() for kw in ["contract", "coverage incomplete", "required"]):
            return ErrorType.CONTRACT_VIOLATION
        
        return ErrorType.UNKNOWN
    
    def _parse_syntax_error(
        self,
        error: Exception,
        error_str: str,
        context: Optional[Dict]
    ) -> StructuredError:
        """Parse a syntax error (Python or JavaScript/TypeScript)."""
        structured = StructuredError(
            error_type=ErrorType.SYNTAX_ERROR,
            raw_message=error_str,
            original_error=error
        )
        
        # Python SyntaxError has lineno and offset
        if hasattr(error, 'lineno'):
            structured.line_number = error.lineno
        if hasattr(error, 'offset'):
            structured.column = error.offset
        if hasattr(error, 'filename'):
            structured.file_path = error.filename
        
        # Extract syntax detail from message
        if "invalid syntax" in error_str.lower():
            structured.syntax_detail = "invalid_syntax"
        elif "unexpected token" in error_str.lower():
            structured.syntax_detail = "unexpected_token"
            # Try to extract expected token
            match = re.search(r"expected ['\"](\w+)['\"]", error_str, re.IGNORECASE)
            if match:
                structured.expected_token = match.group(1)
        
        # Map to contract item if context provided
        if context and "contract_item_id" in context:
            structured.affected_contract_item = context["contract_item_id"]
            structured.affected_contract_type = context.get("contract_item_type")
        elif structured.file_path:
            # Try to infer from file path
            structured.affected_contract_item = f"required_files:{structured.file_path}"
            structured.affected_contract_type = "required_files"
        
        return structured
    
    def _parse_import_error(
        self,
        error: Exception,
        error_str: str,
        context: Optional[Dict]
    ) -> StructuredError:
        """Parse an import/module not found error."""
        structured = StructuredError(
            error_type=ErrorType.IMPORT_ERROR,
            raw_message=error_str,
            original_error=error
        )
        
        # Extract missing module name
        # Python: "No module named 'xyz'"
        # JS: "Cannot resolve 'xyz'" or "Module not found: Error: Can't resolve 'xyz'"
        patterns = [
            r"No module named ['\"]([^'\"]+)['\"]",
            r"Cannot resolve ['\"]([^'\"]+)['\"]",
            r"Can't resolve ['\"]([^'\"]+)['\"]",
            r"Module not found.*['\"]([^'\"]+)['\"]"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_str, re.IGNORECASE)
            if match:
                structured.missing_import = match.group(1)
                break
        
        # Extract file path from context or error
        if context and "file_path" in context:
            structured.file_path = context["file_path"]
        
        if context and "contract_item_id" in context:
            structured.affected_contract_item = context["contract_item_id"]
            structured.affected_contract_type = context.get("contract_item_type")
        
        return structured
    
    def _parse_build_error(
        self,
        error: Exception,
        error_str: str,
        context: Optional[Dict]
    ) -> StructuredError:
        """Parse a build/compilation error."""
        structured = StructuredError(
            error_type=ErrorType.BUILD_ERROR,
            raw_message=error_str,
            original_error=error
        )
        
        # Try to extract file and line from common build error formats
        # TypeScript: "src/file.tsx(5,10): error TS1234: ..."
        ts_pattern = r"([\w\./-]+\.tsx?)\((\d+),(\d+)\)"
        match = re.search(ts_pattern, error_str)
        if match:
            structured.file_path = match.group(1)
            structured.line_number = int(match.group(2))
            structured.column = int(match.group(3))
        
        # Webpack/esbuild format: "ERROR in ./src/file.tsx 5:10"
        webpack_pattern = r"ERROR in ([\w\./-]+)\s+(\d+):(\d+)"
        match = re.search(webpack_pattern, error_str)
        if match:
            structured.file_path = match.group(1)
            structured.line_number = int(match.group(2))
            structured.column = int(match.group(3))
        
        if context and "contract_item_id" in context:
            structured.affected_contract_item = context["contract_item_id"]
            structured.affected_contract_type = context.get("contract_item_type")
        elif structured.file_path:
            structured.affected_contract_item = f"required_files:{structured.file_path}"
            structured.affected_contract_type = "required_files"
        
        return structured
    
    def _parse_missing_file_error(
        self,
        error: Exception,
        error_str: str,
        context: Optional[Dict]
    ) -> StructuredError:
        """Parse a missing file error."""
        structured = StructuredError(
            error_type=ErrorType.MISSING_FILE,
            raw_message=error_str,
            original_error=error
        )
        
        # Extract file path from error
        if hasattr(error, 'filename'):
            structured.file_path = error.filename
        else:
            # Try to extract from message: "No such file or directory: 'path'"
            match = re.search(r"['\"]([^'\"]+)['\"]", error_str)
            if match:
                structured.file_path = match.group(1)
        
        if context and "contract_item_id" in context:
            structured.affected_contract_item = context["contract_item_id"]
            structured.affected_contract_type = context.get("contract_item_type")
        elif structured.file_path:
            structured.affected_contract_item = f"required_files:{structured.file_path}"
            structured.affected_contract_type = "required_files"
        
        return structured
    
    def _parse_missing_route_error(
        self,
        error: Exception,
        error_str: str,
        context: Optional[Dict]
    ) -> StructuredError:
        """Parse a missing route error."""
        structured = StructuredError(
            error_type=ErrorType.MISSING_ROUTE,
            raw_message=error_str,
            original_error=error
        )
        
        # Extract route path if mentioned
        # e.g., "Missing route: /analytics" or "Route /analytics not found"
        patterns = [
            r"Missing route:\s+(/\w+)",
            r"Route\s+(/\w+)\s+not found",
            r"required_routes:(/\w+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_str, re.IGNORECASE)
            if match:
                route = match.group(1)
                structured.affected_contract_item = f"required_routes:{route}"
                structured.affected_contract_type = "required_routes"
                break
        
        if context and "contract_item_id" in context:
            structured.affected_contract_item = context["contract_item_id"]
            structured.affected_contract_type = context.get("contract_item_type")
        
        return structured
    
    def _parse_generic_error(
        self,
        error: Exception,
        error_str: str,
        context: Optional[Dict]
    ) -> StructuredError:
        """Parse a generic/unknown error."""
        structured = StructuredError(
            error_type=ErrorType.UNKNOWN,
            raw_message=error_str,
            original_error=error,
            stack_trace=traceback.format_exc().split("\n") if error else None
        )
        
        if context and "contract_item_id" in context:
            structured.affected_contract_item = context["contract_item_id"]
            structured.affected_contract_type = context.get("contract_item_type")
        
        return structured
    
    def _extract_typescript_errors(self, output: str) -> List[StructuredError]:
        """Extract TypeScript errors from build output."""
        errors = []
        
        # Pattern: "src/file.tsx(5,10): error TS1234: message"
        pattern = r"([\w\./-]+\.tsx?)\((\d+),(\d+)\):\s*error\s*TS\d+:\s*(.+)"
        
        for match in re.finditer(pattern, output):
            structured = StructuredError(
                error_type=ErrorType.BUILD_ERROR,
                raw_message=match.group(3).strip(),
                file_path=match.group(1),
                line_number=int(match.group(2)),
                column=int(match.group(3))
            )
            structured.affected_contract_item = f"required_files:{structured.file_path}"
            structured.affected_contract_type = "required_files"
            errors.append(structured)
        
        return errors
    
    def _extract_python_errors(self, output: str) -> List[StructuredError]:
        """Extract Python errors from output."""
        errors = []
        
        # Pattern: "File "...", line X, in Y"
        file_pattern = r'File "([^"]+)", line (\d+)'
        
        for match in re.finditer(file_pattern, output):
            structured = StructuredError(
                error_type=ErrorType.RUNTIME_ERROR,
                raw_message="Python runtime error",
                file_path=match.group(1),
                line_number=int(match.group(2))
            )
            structured.affected_contract_item = f"required_files:{structured.file_path}"
            structured.affected_contract_type = "required_files"
            errors.append(structured)
        
        return errors
    
    def _extract_module_errors(self, output: str) -> List[StructuredError]:
        """Extract module not found errors."""
        errors = []
        
        # Pattern: "Module not found: Error: Can't resolve 'X' in 'Y'"
        pattern = r"Module not found.*Can't resolve ['\"]([^'\"]+)['\"]"
        
        for match in re.finditer(pattern, output):
            structured = StructuredError(
                error_type=ErrorType.IMPORT_ERROR,
                raw_message=f"Module not found: {match.group(1)}",
                missing_import=match.group(1)
            )
            errors.append(structured)
        
        return errors
    
    def _extract_contract_violations(self, output: str, contract: Any) -> List[StructuredError]:
        """Extract contract coverage violations from output."""
        errors = []
        
        # Look for "Contract coverage incomplete" messages
        if "Contract coverage incomplete" in output:
            # Extract missing items list
            pattern = r"Contract coverage incomplete:\s*\[(.*?)\]"
            match = re.search(pattern, output)
            
            if match:
                items_str = match.group(1)
                # Parse items like "file:path, route:/path"
                items = [item.strip().strip("'\"") for item in items_str.split(",")]
                
                for item in items:
                    if ":" in item:
                        item_type, item_id = item.split(":", 1)
                        structured = StructuredError(
                            error_type=ErrorType.CONTRACT_VIOLATION,
                            raw_message=f"Missing contract item: {item}",
                            affected_contract_item=item,
                            affected_contract_type=f"required_{item_type}s"
                        )
                        errors.append(structured)
        
        return errors


class RepairRouter:
    """
    Routes StructuredErrors to appropriate repair agents.
    
    This is the "error-as-data" routing layer.
    """
    
    # Map error types to repair agent types
    ERROR_TO_AGENT_MAP = {
        ErrorType.SYNTAX_ERROR: ["SyntaxRepairAgent"],
        ErrorType.IMPORT_ERROR: ["ImportRepairAgent", "IntegrationAgent"],
        ErrorType.BUILD_ERROR: ["BuildRepairAgent"],
        ErrorType.MISSING_FILE: ["FileGenerationAgent"],
        ErrorType.MISSING_ROUTE: ["RoutingAgent", "PageGenerationAgent"],
        ErrorType.CONTRACT_VIOLATION: ["ContractRepairAgent"],
        ErrorType.RUNTIME_ERROR: ["DebugAgent", "LogicRepairAgent"],
        ErrorType.UNKNOWN: ["DiagnosticAgent"]
    }
    
    def route(self, error: StructuredError) -> List[str]:
        """
        Determine which repair agents should handle this error.
        
        Returns list of agent names to try in order.
        """
        return self.ERROR_TO_AGENT_MAP.get(error.error_type, ["GenericRepairAgent"])
    
    def route_with_context(self, error: StructuredError, contract: Any) -> Dict[str, Any]:
        """
        Create a complete repair plan from the error.
        
        Returns dict with:
        - target_agents: List of agent names
        - contract_item: The contract item to repair
        - repair_strategy: How to repair
        - priority: Repair priority
        """
        agents = self.route(error)
        
        plan = {
            "target_agents": agents,
            "contract_item_id": error.affected_contract_item,
            "contract_item_type": error.affected_contract_type,
            "error_type": error.error_type.value,
            "priority": self._determine_priority(error),
            "repair_context": self._build_repair_context(error)
        }
        
        return plan
    
    def _determine_priority(self, error: StructuredError) -> str:
        """Determine repair priority based on error type."""
        if error.error_type == ErrorType.CONTRACT_VIOLATION:
            return "critical"
        elif error.error_type == ErrorType.MISSING_FILE:
            return "high"
        elif error.error_type == ErrorType.SYNTAX_ERROR:
            return "high"
        elif error.error_type == ErrorType.MISSING_ROUTE:
            return "medium"
        else:
            return "medium"
    
    def _build_repair_context(self, error: StructuredError) -> Dict[str, Any]:
        """Build context dict for the repair agent."""
        context = {
            "error_message": error.raw_message,
            "file_path": error.file_path,
            "line_number": error.line_number
        }
        
        # Add type-specific context
        if error.error_type == ErrorType.SYNTAX_ERROR:
            context["syntax_detail"] = error.syntax_detail
            context["expected_token"] = error.expected_token
        
        elif error.error_type == ErrorType.IMPORT_ERROR:
            context["missing_import"] = error.missing_import
        
        return context

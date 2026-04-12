"""
Comprehensive Output Validation for CrucibAI
Validates JSON, code syntax, and output formats.
"""

import json
import ast
import re
import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)


class OutputValidator:
    """Validates agent outputs against expected formats."""

    @staticmethod
    def validate_json(output: str) -> Tuple[bool, Any, str]:
        """
        Validate JSON output.

        Returns: (is_valid, parsed_json, error_message)
        """
        try:
            # Try to parse as-is
            parsed = json.loads(output)
            return True, parsed, ""
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            match = re.search(r"```json\s*(.*?)\s*```", output, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    return True, parsed, ""
                except json.JSONDecodeError as e:
                    return False, None, f"Invalid JSON in code block: {str(e)}"

            # Try to extract any JSON object
            match = re.search(r"\{.*\}", output, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    return True, parsed, ""
                except json.JSONDecodeError as e:
                    return False, None, f"Invalid JSON format: {str(e)}"

            return False, None, f"No valid JSON found in output"

    @staticmethod
    def validate_python_code(code: str) -> Tuple[bool, str]:
        """
        Validate Python code syntax.

        Returns: (is_valid, error_message)
        """
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"Python syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Python validation error: {str(e)}"

    @staticmethod
    def validate_javascript_code(code: str) -> Tuple[bool, str]:
        """
        Validate JavaScript code syntax.

        Returns: (is_valid, error_message)
        """
        # Basic JavaScript validation (not perfect, but catches common errors)
        errors = []

        # Check for balanced braces
        if code.count("{") != code.count("}"):
            errors.append("Unbalanced curly braces")

        # Check for balanced parentheses
        if code.count("(") != code.count(")"):
            errors.append("Unbalanced parentheses")

        # Check for balanced brackets
        if code.count("[") != code.count("]"):
            errors.append("Unbalanced square brackets")

        # Check for common syntax errors
        if re.search(r"\bfunciton\b", code):
            errors.append("Typo: 'funciton' should be 'function'")

        if re.search(r"==\s*=", code):
            errors.append("Possible syntax error: '===' instead of '=='")

        if errors:
            return False, "; ".join(errors)

        return True, ""

    @staticmethod
    def validate_sql_code(code: str) -> Tuple[bool, str]:
        """
        Validate SQL code syntax.

        Returns: (is_valid, error_message)
        """
        try:
            import sqlparse

            parsed = sqlparse.parse(code)
            if not parsed:
                return False, "No valid SQL statements found"
            return True, ""
        except ImportError:
            # sqlparse not available, do basic checks
            code_upper = code.upper()

            if (
                "CREATE TABLE" not in code_upper
                and "INSERT" not in code_upper
                and "SELECT" not in code_upper
            ):
                return False, "No recognized SQL keywords found"

            # Check for balanced parentheses
            if code.count("(") != code.count(")"):
                return False, "Unbalanced parentheses in SQL"

            return True, ""
        except Exception as e:
            return False, f"SQL validation error: {str(e)}"

    @staticmethod
    def validate_output_format(output: str, expected_format: str) -> Tuple[bool, str]:
        """
        Validate output matches expected format.

        Returns: (is_valid, error_message)
        """
        if expected_format == "json":
            is_valid, _, error = OutputValidator.validate_json(output)
            return is_valid, error

        elif expected_format == "code":
            # Try Python first
            is_valid, error = OutputValidator.validate_python_code(output)
            if is_valid:
                return True, ""

            # Try JavaScript
            is_valid, error = OutputValidator.validate_javascript_code(output)
            if is_valid:
                return True, ""

            # Try SQL
            is_valid, error = OutputValidator.validate_sql_code(output)
            if is_valid:
                return True, ""

            return False, f"Code validation failed: {error}"

        elif expected_format == "sql":
            return OutputValidator.validate_sql_code(output)

        elif expected_format == "checklist":
            # Validate checklist format
            lines = output.strip().split("\n")
            if not lines:
                return False, "Empty checklist"

            for line in lines:
                if "PASS" not in line and "FAIL" not in line:
                    return False, f"Checklist item missing PASS/FAIL: {line}"

            return True, ""

        elif expected_format == "numbered_list":
            # Validate numbered list format
            lines = output.strip().split("\n")
            if not lines:
                return False, "Empty list"

            for i, line in enumerate(lines, 1):
                if not line.strip().startswith(f"{i}."):
                    return False, f"Expected item {i} to start with '{i}.'"

            return True, ""

        elif expected_format == "question_list":
            # Validate question list
            lines = output.strip().split("\n")
            if not lines:
                return False, "Empty question list"

            for line in lines:
                if not line.strip().endswith("?"):
                    return False, f"Question must end with '?': {line}"

            return True, ""

        elif expected_format == "steps":
            # Validate step format
            lines = output.strip().split("\n")
            if not lines:
                return False, "Empty steps"

            for i, line in enumerate(lines, 1):
                if line.strip() and not re.match(r"^\d+\.", line.strip()):
                    return False, f"Step must start with number: {line}"

            return True, ""

        return True, ""

    @staticmethod
    def validate_agent_output(
        agent_name: str, output: str, expected_format: str
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of agent output.

        Returns: {
            "is_valid": bool,
            "format_valid": bool,
            "syntax_valid": bool,
            "errors": [str],
            "warnings": [str],
            "parsed_output": Any (if JSON)
        }
        """
        result = {
            "is_valid": True,
            "format_valid": True,
            "syntax_valid": True,
            "errors": [],
            "warnings": [],
            "parsed_output": None,
        }

        if not output or not output.strip():
            result["is_valid"] = False
            result["errors"].append("Empty output from agent")
            return result

        # Check format
        format_valid, format_error = OutputValidator.validate_output_format(
            output, expected_format
        )
        result["format_valid"] = format_valid

        if not format_valid:
            result["errors"].append(f"Format error: {format_error}")
            result["is_valid"] = False

        # Check syntax
        if expected_format == "json":
            syntax_valid, parsed, syntax_error = OutputValidator.validate_json(output)
            result["syntax_valid"] = syntax_valid
            result["parsed_output"] = parsed
            if not syntax_valid:
                result["errors"].append(f"Syntax error: {syntax_error}")
                result["is_valid"] = False

        elif expected_format == "code":
            # Try to determine code type and validate
            if "import" in output or "def " in output or "class " in output:
                syntax_valid, syntax_error = OutputValidator.validate_python_code(
                    output
                )
            elif "function" in output or "const " in output or "let " in output:
                syntax_valid, syntax_error = OutputValidator.validate_javascript_code(
                    output
                )
            else:
                syntax_valid, syntax_error = OutputValidator.validate_python_code(
                    output
                )

            result["syntax_valid"] = syntax_valid
            if not syntax_valid:
                result["errors"].append(f"Syntax error: {syntax_error}")
                result["is_valid"] = False

        # Log results
        if result["is_valid"]:
            logger.info(f"✅ {agent_name} output validation PASSED")
        else:
            logger.error(
                f"❌ {agent_name} output validation FAILED: {result['errors']}"
            )

        return result

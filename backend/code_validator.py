"""
Code Validator: Comprehensive syntax and type checking for generated code.
"""

import ast
import subprocess
import tempfile
import os
import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)


class CodeValidator:
    """Validates generated code for syntax and type errors."""
    
    @staticmethod
    def validate_python(code: str) -> Dict[str, Any]:
        """
        Validate Python code with multiple checks.
        
        Returns: {
            "is_valid": bool,
            "syntax_valid": bool,
            "type_valid": bool,
            "lint_valid": bool,
            "errors": [str],
            "warnings": [str]
        }
        """
        result = {
            "is_valid": True,
            "syntax_valid": True,
            "type_valid": True,
            "lint_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 1. Syntax check with ast.parse
        try:
            ast.parse(code)
            logger.info("✅ Python syntax check PASSED")
        except SyntaxError as e:
            result["syntax_valid"] = False
            result["is_valid"] = False
            result["errors"].append(f"Syntax error at line {e.lineno}: {e.msg}")
            logger.error(f"❌ Python syntax error: {e}")
            return result
        
        # 2. Type check with mypy (if available)
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                f.flush()
                
                try:
                    output = subprocess.run(
                        ['mypy', f.name, '--ignore-missing-imports'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if output.returncode != 0:
                        result["type_valid"] = False
                        result["warnings"].extend(output.stdout.split('\n'))
                        logger.warning(f"⚠️ Type check warnings: {output.stdout}")
                except FileNotFoundError:
                    logger.debug("mypy not available, skipping type check")
                finally:
                    os.unlink(f.name)
        except Exception as e:
            logger.warning(f"Type check failed: {e}")
        
        # 3. Lint check with pylint (if available)
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                f.flush()
                
                try:
                    output = subprocess.run(
                        ['pylint', f.name, '--disable=all', '--enable=E,F'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if output.returncode != 0:
                        result["lint_valid"] = False
                        result["warnings"].extend(output.stdout.split('\n'))
                        logger.warning(f"⚠️ Lint warnings: {output.stdout}")
                except FileNotFoundError:
                    logger.debug("pylint not available, skipping lint check")
                finally:
                    os.unlink(f.name)
        except Exception as e:
            logger.warning(f"Lint check failed: {e}")
        
        return result
    
    @staticmethod
    def validate_javascript(code: str) -> Dict[str, Any]:
        """
        Validate JavaScript code with multiple checks.
        
        Returns: {
            "is_valid": bool,
            "syntax_valid": bool,
            "errors": [str],
            "warnings": [str]
        }
        """
        result = {
            "is_valid": True,
            "syntax_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 1. Basic syntax check
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                f.flush()
                
                try:
                    output = subprocess.run(
                        ['node', '--check', f.name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if output.returncode != 0:
                        result["syntax_valid"] = False
                        result["is_valid"] = False
                        result["errors"].append(output.stderr)
                        logger.error(f"❌ JavaScript syntax error: {output.stderr}")
                    else:
                        logger.info("✅ JavaScript syntax check PASSED")
                except FileNotFoundError:
                    logger.warning("node not available, skipping JavaScript syntax check")
                finally:
                    os.unlink(f.name)
        except Exception as e:
            logger.warning(f"JavaScript syntax check failed: {e}")
        
        # 2. ESLint check (if available)
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                f.flush()
                
                try:
                    output = subprocess.run(
                        ['eslint', f.name, '--no-eslintrc', '--parser-options=ecmaVersion:2021'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if output.returncode != 0:
                        result["warnings"].extend(output.stdout.split('\n'))
                        logger.warning(f"⚠️ ESLint warnings: {output.stdout}")
                except FileNotFoundError:
                    logger.debug("eslint not available, skipping linting")
                finally:
                    os.unlink(f.name)
        except Exception as e:
            logger.warning(f"ESLint check failed: {e}")
        
        return result
    
    @staticmethod
    def validate_sql(code: str) -> Dict[str, Any]:
        """
        Validate SQL code syntax.
        
        Returns: {
            "is_valid": bool,
            "syntax_valid": bool,
            "errors": [str],
            "warnings": [str]
        }
        """
        result = {
            "is_valid": True,
            "syntax_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Try sqlparse
        try:
            import sqlparse
            
            parsed = sqlparse.parse(code)
            if not parsed:
                result["syntax_valid"] = False
                result["is_valid"] = False
                result["errors"].append("No valid SQL statements found")
                logger.error("❌ No valid SQL statements found")
                return result
            
            # Check for common SQL errors
            code_upper = code.upper()
            
            # Check for balanced parentheses
            if code.count('(') != code.count(')'):
                result["errors"].append("Unbalanced parentheses")
                result["syntax_valid"] = False
                result["is_valid"] = False
            
            # Check for incomplete statements
            if code_upper.startswith('SELECT') and not code_upper.count('FROM'):
                result["warnings"].append("SELECT statement without FROM clause")
            
            if result["syntax_valid"]:
                logger.info("✅ SQL syntax check PASSED")
            
            return result
        except ImportError:
            logger.debug("sqlparse not available, doing basic SQL checks")
        
        # Basic SQL checks without sqlparse
        code_upper = code.upper()
        
        # Check for balanced parentheses
        if code.count('(') != code.count(')'):
            result["errors"].append("Unbalanced parentheses")
            result["syntax_valid"] = False
            result["is_valid"] = False
        
        # Check for recognized SQL keywords
        if not any(kw in code_upper for kw in ['CREATE', 'INSERT', 'SELECT', 'UPDATE', 'DELETE', 'DROP']):
            result["errors"].append("No recognized SQL keywords found")
            result["syntax_valid"] = False
            result["is_valid"] = False
        
        return result
    
    @staticmethod
    def validate_code(code: str, language: str = None) -> Dict[str, Any]:
        """
        Auto-detect language and validate code.
        
        Returns: comprehensive validation result
        """
        # Auto-detect language if not specified
        if not language:
            if any(kw in code for kw in ['import ', 'def ', 'class ', 'async def']):
                language = 'python'
            elif any(kw in code for kw in ['function', 'const ', 'let ', 'var ', 'import {']):
                language = 'javascript'
            elif any(kw in code for kw in ['CREATE', 'INSERT', 'SELECT', 'UPDATE']):
                language = 'sql'
            else:
                language = 'python'  # default
        
        if language.lower() == 'python':
            return CodeValidator.validate_python(code)
        elif language.lower() in ['javascript', 'js', 'typescript', 'ts']:
            return CodeValidator.validate_javascript(code)
        elif language.lower() == 'sql':
            return CodeValidator.validate_sql(code)
        else:
            return {
                "is_valid": False,
                "errors": [f"Unknown language: {language}"],
                "warnings": []
            }

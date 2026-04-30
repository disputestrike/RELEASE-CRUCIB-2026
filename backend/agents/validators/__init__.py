"""
CrucibAI Runtime Validators.

This package provides **runtime validation** for generated code —
going BEYOND static analysis by actually compiling, building, and
testing generated projects.

Validators:
  - PythonValidator   — py_compile, pip install, uvicorn health check
  - NodeValidator     — node --check, npm install/build, server health
  - TypeScriptValidator — tsc --noEmit, npm build, server health
  - CppValidator      — g++ syntax, cmake/g++ build, binary execution
  - GoValidator       — go vet, go build, server health check
  - RustValidator     — cargo check, cargo build, cargo run

Each validator implements four stages:
  1. validate_syntax()       — fast static checks
  2. validate_build()        — full compilation / bundle
  3. validate_runtime(port)  — start server, health check, kill
  4. validate_integration(port) — test all detected endpoints

Factory:
  get_validator(language, workspace_path, timeout) -> BaseValidator

Usage example:

    from backend.agents.validators import get_validator

    v = get_validator("python", "/tmp/generated-project")
    results = v.validate_all()
    for stage, result in results.items():
        print(result.summary())
"""

# Re-export base classes and types
from .base import BaseValidator, ValidationResult

# Re-export all concrete validators
from .python_validator import PythonValidator
from .node_validator import NodeValidator
from .typescript_validator import TypeScriptValidator
from .cpp_validator import CppValidator
from .go_validator import GoValidator
from .rust_validator import RustValidator

# Re-export factory
from .validator_factory import get_validator, list_supported_languages

__all__ = [
    # Base
    "BaseValidator",
    "ValidationResult",
    # Concrete validators
    "PythonValidator",
    "NodeValidator",
    "TypeScriptValidator",
    "CppValidator",
    "GoValidator",
    "RustValidator",
    # Factory
    "get_validator",
    "list_supported_languages",
]

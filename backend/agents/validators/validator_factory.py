"""
Validator Factory: Get the right validator for a given language.

Usage:
    from backend.agents.validators import get_validator

    validator = get_validator("python", "/path/to/workspace")
    results = validator.validate_all()
"""

import logging
from typing import Dict, Type

from .base import BaseValidator

logger = logging.getLogger(__name__)


def get_validator(
    language: str,
    workspace_path: str,
    timeout: int = 60,
) -> BaseValidator:
    """
    Factory function that returns the appropriate validator for a language.

    Args:
        language:      One of python, javascript, typescript, cpp, go, rust
        workspace_path: Absolute path to the generated project workspace
        timeout:       Maximum seconds for any single command

    Returns:
        An instance of the matching language validator.

    Raises:
        ValueError: If the language is not supported.
    """
    _registry: Dict[str, Type[BaseValidator]] = _build_registry()

    key = language.lower().strip()
    cls = _registry.get(key)

    if cls is None:
        supported = sorted(_registry.keys())
        raise ValueError(
            f"No validator for language: {language!r}. "
            f"Supported languages: {supported}"
        )

    logger.info(
        "[validator-factory] Creating %s validator for workspace=%r timeout=%ds",
        language,
        workspace_path,
        timeout,
    )
    return cls(workspace_path, timeout)


def list_supported_languages() -> list:
    """Return a sorted list of supported language names."""
    return sorted(_build_registry().keys())


# ------------------------------------------------------------------
# Internal: lazy-import registry to avoid circular imports
# ------------------------------------------------------------------

def _build_registry() -> Dict[str, Type[BaseValidator]]:
    """Build the language -> validator class mapping.

    Lazy imports so the module can be imported even when individual
    validators are not installed.
    """
    from .python_validator import PythonValidator
    from .node_validator import NodeValidator
    from .typescript_validator import TypeScriptValidator
    from .cpp_validator import CppValidator
    from .go_validator import GoValidator
    from .rust_validator import RustValidator

    return {
        "python": PythonValidator,
        "javascript": NodeValidator,
        "js": NodeValidator,
        "typescript": TypeScriptValidator,
        "ts": TypeScriptValidator,
        "cpp": CppValidator,
        "c++": CppValidator,
        "go": GoValidator,
        "rust": RustValidator,
    }

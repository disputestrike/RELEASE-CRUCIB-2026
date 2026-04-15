from __future__ import annotations

import importlib
from typing import Any, Optional


def register_optional_router(
    *,
    app: Any,
    logger: Any,
    module_path: str,
    attr_name: str,
    success_message: str,
    failure_message: str,
    fallback_router: Optional[Any] = None,
) -> bool:
    try:
        module = importlib.import_module(module_path)
        router = getattr(module, attr_name)
        app.include_router(router)
        logger.info(success_message)
        return True
    except Exception as exc:  # pragma: no cover - defensive registration wrapper
        logger.warning(failure_message, exc)
        if fallback_router is not None:
            app.include_router(fallback_router)
        return False

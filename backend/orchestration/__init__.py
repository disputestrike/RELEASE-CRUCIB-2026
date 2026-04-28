# Lazy import to avoid relative-import-beyond-top-level errors when
# orchestration is imported as a top-level package via PYTHONPATH=/app/backend.
__all__ = ["runtime_state", "build_memory"]


def __getattr__(name):
    if name == "runtime_state":
        import importlib
        _rs = importlib.import_module("backend.orchestration.runtime_state")
        # Cache in this module's namespace to prevent repeated __getattr__ calls
        globals()["runtime_state"] = _rs
        return _rs
    if name == "build_memory":
        import importlib
        _bm = importlib.import_module("backend.orchestration.build_memory")
        globals()["build_memory"] = _bm
        return _bm
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

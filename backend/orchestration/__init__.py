# Lazy import to avoid relative-import-beyond-top-level errors when
# orchestration is imported as a top-level package via PYTHONPATH=/app/backend.
__all__ = ["runtime_state", "build_memory"]


def __getattr__(name):
    if name == "runtime_state":
        from . import runtime_state as _rs
        return _rs
    if name == "build_memory":
        from . import build_memory as _bm
        return _bm
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

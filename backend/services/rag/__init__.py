"""RAG / vector memory subsystem.

Re-exports the Chroma-backed store and the pattern-capture hooks.
"""
from .store import RagStore, get_store  # noqa: F401
from .pattern_hook import record_success, retrieve_priors  # noqa: F401

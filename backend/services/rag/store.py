"""Chroma-backed vector store with OpenAI embeddings.

Falls back to a local stub (no persistence, no embeddings) when chromadb or
OPENAI_API_KEY is missing — the rest of the app still boots.

Collections are per-kind namespaces, e.g. 'project_patterns', 'doc_chunks'.
Documents carry free-form metadata; `where` filters are passed through to
Chroma's native metadata query syntax.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class _NullStore:
    """No-op fallback when chromadb or an embedding key is absent."""

    def __init__(self, reason: str):
        self.reason = reason
        logger.warning("RAG: using null store — %s", reason)

    async def upsert(self, collection: str, docs: list[dict]) -> dict:
        return {"ok": False, "reason": self.reason, "upserted": 0}

    async def query(self, collection: str, query: str, k: int = 5,
                    where: Optional[dict] = None) -> list[dict]:
        return []

    async def forget(self, collection: str, ids: list[str]) -> dict:
        return {"ok": False, "reason": self.reason}

    def stats(self) -> dict:
        return {"backend": "null", "reason": self.reason}


class RagStore:
    """Chroma persistent client wrapper."""

    def __init__(self, persist_path: str = "./data/chroma"):
        self.persist_path = persist_path
        self._client = None
        self._embedder = None
        self._init_error: Optional[str] = None
        self._try_init()

    def _try_init(self) -> None:
        try:
            import chromadb  # type: ignore
        except Exception as e:
            self._init_error = f"chromadb not installed: {e}"
            return
        try:
            Path(self.persist_path).mkdir(parents=True, exist_ok=True)
            # Prefer PersistentClient; settings minimal to avoid telemetry noise.
            self._client = chromadb.PersistentClient(path=self.persist_path)
        except Exception as e:
            self._init_error = f"chromadb init failed: {e}"
            self._client = None
            return
        # Embeddings are optional at construction — we lazy-load on first use
        # so callers without OPENAI_API_KEY can still get the client for testing.
        self._embedder = self._build_embedder()

    def _build_embedder(self):
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            logger.info("RAG: OPENAI_API_KEY missing — embeddings disabled until set")
            return None
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:
            logger.info("RAG: openai package missing — %s", e)
            return None
        client = OpenAI(api_key=api_key)

        def embed(texts: list[str]) -> list[list[float]]:
            resp = client.embeddings.create(
                model="text-embedding-3-small", input=texts
            )
            return [d.embedding for d in resp.data]

        return embed

    def available(self) -> bool:
        return self._client is not None

    def _col(self, name: str):
        return self._client.get_or_create_collection(name=name)

    async def upsert(self, collection: str, docs: list[dict]) -> dict:
        if not self.available():
            return {"ok": False, "reason": self._init_error, "upserted": 0}
        if not docs:
            return {"ok": True, "upserted": 0}
        ids = [str(d["id"]) for d in docs]
        texts = [str(d["text"]) for d in docs]
        metas = [dict(d.get("metadata") or {}) for d in docs]
        for m in metas:
            m.setdefault("ts", time.time())
        col = self._col(collection)
        if self._embedder is None:
            self._embedder = self._build_embedder()
        if self._embedder is None:
            # No embeddings — upsert with text only (Chroma can fall back to its default
            # embedding function if configured; otherwise this will raise). Best-effort.
            col.upsert(ids=ids, documents=texts, metadatas=metas)
        else:
            vecs = self._embedder(texts)
            col.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=vecs)
        return {"ok": True, "upserted": len(docs)}

    async def query(self, collection: str, query: str, k: int = 5,
                    where: Optional[dict] = None) -> list[dict]:
        if not self.available():
            return []
        col = self._col(collection)
        if self._embedder is None:
            self._embedder = self._build_embedder()
        if self._embedder is None:
            # Text query against default embedder; may fail if no collection embedding fn.
            try:
                res = col.query(query_texts=[query], n_results=k, where=where or None)
            except Exception as e:
                logger.warning("RAG query failed (no embedder): %s", e)
                return []
        else:
            vec = self._embedder([query])[0]
            res = col.query(query_embeddings=[vec], n_results=k, where=where or None)
        out = []
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0] if res.get("distances") else [None] * len(ids)
        for i, _id in enumerate(ids):
            out.append({
                "id": _id,
                "text": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else None,
            })
        return out

    async def forget(self, collection: str, ids: list[str]) -> dict:
        if not self.available():
            return {"ok": False, "reason": self._init_error}
        col = self._col(collection)
        col.delete(ids=[str(i) for i in ids])
        return {"ok": True, "deleted": len(ids)}

    def stats(self) -> dict:
        if not self.available():
            return {"backend": "null", "reason": self._init_error}
        return {"backend": "chromadb", "persist_path": self.persist_path,
                "embedder": "openai:text-embedding-3-small" if self._embedder else "disabled"}


# Process-wide singleton
_store: Optional[RagStore] = None


def get_store() -> RagStore:
    global _store
    if _store is not None:
        return _store
    persist = os.environ.get("RAG_PERSIST_DIR", "./data/chroma")
    _store = RagStore(persist_path=persist)
    return _store

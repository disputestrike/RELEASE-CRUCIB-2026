"""
Vector database integration with safe provider fallback.

The live runtime should not crash when Pinecone/OpenAI are unavailable. We use:
- Pinecone + OpenAI embeddings when configured
- an in-memory fallback otherwise
"""

from __future__ import annotations

import hashlib
import inspect
import logging
import math
import os
import sys
import types
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _fallback_embed_text(text: str, dimension: int) -> List[float]:
    buckets = [0.0] * dimension
    for token in (text or "").lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dimension
        buckets[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in buckets)) or 1.0
    return [v / norm for v in buckets]


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    size = min(len(a), len(b))
    return sum(a[i] * b[i] for i in range(size))


class _InMemoryIndex:
    def __init__(self):
        self.vectors: Dict[str, Dict] = {}

    def upsert(self, vectors: List[Dict]) -> None:
        for vector in vectors:
            self.vectors[vector["id"]] = vector

    def query(
        self,
        *,
        vector: List[float],
        top_k: int = 5,
        include_metadata: bool = False,
        filter: Optional[Dict] = None,
    ) -> Dict:
        project_id = ((filter or {}).get("project_id") or {}).get("$eq")
        memory_types = ((filter or {}).get("type") or {}).get("$in")
        matches = []
        for vid, payload in self.vectors.items():
            metadata = payload.get("metadata") or {}
            if project_id and metadata.get("project_id") != project_id:
                continue
            if memory_types and metadata.get("type") not in memory_types:
                continue
            matches.append(
                {
                    "id": vid,
                    "score": _cosine(vector, payload.get("values") or []),
                    "metadata": metadata if include_metadata else {},
                }
            )
        matches.sort(key=lambda item: item["score"], reverse=True)
        return {"matches": matches[:top_k]}

    def delete(self, ids: List[str]) -> None:
        for vid in ids:
            self.vectors.pop(vid, None)


try:
    from pinecone import Pinecone, ServerlessSpec  # type: ignore
    _PINECONE_AVAILABLE = True
except Exception:
    _PINECONE_AVAILABLE = False

    class ServerlessSpec:  # pragma: no cover - fallback shim
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Pinecone:  # pragma: no cover - fallback shim
        def __init__(self, *args, **kwargs):
            self._indexes: Dict[str, _InMemoryIndex] = {}

        def list_indexes(self):
            return [types.SimpleNamespace(name=name) for name in self._indexes]

        def create_index(self, name: str, **kwargs):
            self._indexes.setdefault(name, _InMemoryIndex())

        def Index(self, name: str):
            return self._indexes.setdefault(name, _InMemoryIndex())

    pinecone_stub = types.ModuleType("pinecone")
    pinecone_stub.Pinecone = Pinecone
    pinecone_stub.ServerlessSpec = ServerlessSpec
    sys.modules.setdefault("pinecone", pinecone_stub)


class _FallbackEmbeddings:
    async def create(self, model: str, input: str):
        return types.SimpleNamespace(
            data=[types.SimpleNamespace(embedding=_fallback_embed_text(input, 1536))]
        )


class _FallbackAsyncOpenAI:
    def __init__(self, *args, **kwargs):
        self.embeddings = _FallbackEmbeddings()


try:
    from openai import AsyncOpenAI as _OpenAIAsyncClient  # type: ignore
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False
    _OpenAIAsyncClient = None


def _build_embeddings_client():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if _OPENAI_AVAILABLE and api_key:
        return _OpenAIAsyncClient(api_key=api_key)
    return _FallbackAsyncOpenAI()


class VectorMemory:
    """
    Manage project context using Pinecone when configured, otherwise in-memory fallback.
    """

    def __init__(self):
        self.max_metadata_size = 500
        self.embedding_dimension = 1536
        self.index_name = "crucibai-memory"
        self.provider = "memory"
        self.index = _InMemoryIndex()
        self.pc = None

        pinecone_api_key = os.getenv("PINECONE_API_KEY", "").strip()
        if _PINECONE_AVAILABLE and pinecone_api_key:
            try:
                self.pc = Pinecone(api_key=pinecone_api_key)
                self._ensure_index_exists()
                self.index = self.pc.Index(self.index_name)
                self.provider = "pinecone"
            except Exception as exc:
                logger.warning("VectorMemory: falling back to in-memory index: %s", exc)
                self.index = _InMemoryIndex()
                self.provider = "memory"

        self.embeddings_client = _build_embeddings_client()

    def _ensure_index_exists(self) -> None:
        if not self.pc:
            return
        indexes = self.pc.list_indexes()
        index_names = [idx.name for idx in indexes]
        if self.index_name not in index_names:
            self.pc.create_index(
                name=self.index_name,
                dimension=self.embedding_dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

    async def add_memory(
        self,
        project_id: str,
        text: str,
        memory_type: str,
        agent_name: Optional[str] = None,
        phase: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tokens: int = 0,
    ) -> str:
        embedding_text = (text or "")[:2000]
        embedding = await self._embed_text(embedding_text)
        vector_id = f"{project_id}#{agent_name or 'system'}#{int(datetime.utcnow().timestamp())}#{hash(text) % 1000000}"
        meta = {
            "project_id": project_id,
            "type": memory_type,
            "agent": agent_name or "system",
            "phase": phase or "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "tokens": str(tokens),
            "text": (text or "")[: self.max_metadata_size],
        }
        if metadata:
            meta.update(metadata)
        upsert_result = self.index.upsert(
            vectors=[
                {
                    "id": vector_id,
                    "values": embedding,
                    "metadata": meta,
                }
            ]
        )
        if inspect.isawaitable(upsert_result):  # pragma: no cover - mock compatibility
            await upsert_result
        logger.info("VectorMemory[%s]: stored %s", self.provider, vector_id)
        return vector_id

    async def retrieve_context(
        self,
        project_id: str,
        query: str,
        top_k: int = 5,
        memory_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        try:
            query_embedding = await self._embed_text(query)
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter={
                    "project_id": {"$eq": project_id},
                    **({"type": {"$in": memory_types}} if memory_types else {}),
                },
            )
            if inspect.isawaitable(results):
                results = await results
            memories = []
            for match in results.get("matches", []):
                meta = match.get("metadata") or {}
                memories.append(
                    {
                        "id": match.get("id"),
                        "text": meta.get("text", ""),
                        "type": meta.get("type", ""),
                        "agent": meta.get("agent", ""),
                        "phase": meta.get("phase", ""),
                        "timestamp": meta.get("timestamp", ""),
                        "relevance_score": match.get("score", 0.0),
                        "tokens": int(meta.get("tokens", 0)),
                    }
                )
            return memories
        except Exception as exc:
            logger.warning("VectorMemory retrieve_context failed: %s", exc)
            return []

    async def count_project_tokens(self, project_id: str) -> int:
        try:
            results = self.index.query(
                vector=[0.0] * self.embedding_dimension,
                top_k=10000,
                include_metadata=True,
                filter={"project_id": {"$eq": project_id}},
            )
            if inspect.isawaitable(results):
                results = await results
            return sum(int((match.get("metadata") or {}).get("tokens", 0)) for match in results.get("matches", []))
        except Exception as exc:
            logger.warning("VectorMemory count_project_tokens failed: %s", exc)
            return 0

    async def delete_project_memory(self, project_id: str) -> bool:
        try:
            results = self.index.query(
                vector=[0.0] * self.embedding_dimension,
                top_k=10000,
                include_metadata=True,
                filter={"project_id": {"$eq": project_id}},
            )
            if inspect.isawaitable(results):
                results = await results
            ids = [match["id"] for match in results.get("matches", [])]
            if ids:
                deleted = self.index.delete(ids=ids)
                if inspect.isawaitable(deleted):
                    await deleted
            return True
        except Exception as exc:
            logger.warning("VectorMemory delete_project_memory failed: %s", exc)
            return False

    async def _embed_text(self, text: str) -> List[float]:
        if self.provider == "memory" or not os.getenv("OPENAI_API_KEY", "").strip():
            return _fallback_embed_text(text, self.embedding_dimension)
        try:
            response = await self.embeddings_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.warning("VectorMemory embed fallback activated: %s", exc)
            return _fallback_embed_text(text, self.embedding_dimension)


_vector_memory: Optional[VectorMemory] = None


async def get_vector_memory() -> VectorMemory:
    global _vector_memory
    if _vector_memory is None:
        _vector_memory = VectorMemory()
    return _vector_memory


async def store_memory(project_id: str, text: str, memory_type: str, **kwargs) -> str:
    vm = await get_vector_memory()
    return await vm.add_memory(project_id, text, memory_type, **kwargs)


async def retrieve_memory(project_id: str, query: str, **kwargs) -> List[Dict]:
    vm = await get_vector_memory()
    return await vm.retrieve_context(project_id, query, **kwargs)

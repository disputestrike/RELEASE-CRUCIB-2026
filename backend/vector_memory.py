"""
CrucibAI Vector Memory Module
===============================
Provides long-term memory and RAG (Retrieval-Augmented Generation)
for the agent system using ChromaDB for vector storage.

Falls back gracefully if ChromaDB is not installed — the system
continues to work without vector memory, just without RAG.

Usage:
    from vector_memory import VectorMemory

    memory = VectorMemory()
    await memory.store("project_123", "agent_output", {"code": "..."}, {"agent": "Frontend"})
    results = await memory.search("project_123", "responsive navbar component", top_k=5)
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import ChromaDB — graceful fallback if not installed
_chroma_available = False
try:
    import chromadb
    from chromadb.config import Settings

    _chroma_available = True
    logger.info("✅ ChromaDB available — vector memory enabled")
except ImportError:
    logger.debug("ChromaDB not installed — vector memory disabled (optional feature)")


class VectorMemory:
    """
    Vector-based memory system for CrucibAI agents.
    Stores agent outputs, code snippets, and project context
    for retrieval-augmented generation.
    """

    def __init__(self, persist_directory: str = "./chroma_data"):
        self._client = None
        self._collections: Dict[str, Any] = {}
        self._persist_dir = persist_directory
        self._initialized = False

    def _ensure_client(self):
        """Lazy-initialize the ChromaDB client."""
        if not _chroma_available:
            return False
        if self._client is None:
            try:
                self._client = chromadb.Client(
                    Settings(
                        chroma_db_impl="duckdb+parquet",
                        persist_directory=self._persist_dir,
                        anonymized_telemetry=False,
                    )
                )
                self._initialized = True
                logger.info(
                    f"✅ ChromaDB client initialized (persist: {self._persist_dir})"
                )
            except Exception as e:
                logger.error(f"❌ ChromaDB init failed: {e}")
                return False
        return True

    def _get_collection(self, collection_name: str):
        """Get or create a ChromaDB collection."""
        if collection_name not in self._collections:
            self._collections[collection_name] = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[collection_name]

    async def store(
        self,
        project_id: str,
        content_type: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Store content in vector memory.

        Args:
            project_id: Project identifier
            content_type: Type of content (agent_output, code_snippet, project_context)
            content: The content to store
            metadata: Additional metadata

        Returns:
            Document ID if stored, None if ChromaDB unavailable
        """
        if not self._ensure_client():
            return None

        try:
            collection = self._get_collection(f"crucibai_{content_type}")

            # Generate document text from content
            doc_text = self._content_to_text(content)
            if not doc_text or len(doc_text) < 10:
                return None

            doc_id = self._generate_id(project_id, doc_text)

            meta = {
                "project_id": project_id,
                "content_type": content_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            }
            # ChromaDB metadata values must be str, int, float, or bool
            meta = {
                k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                for k, v in meta.items()
            }

            collection.upsert(
                documents=[doc_text[:8000]],  # ChromaDB has document size limits
                metadatas=[meta],
                ids=[doc_id],
            )

            logger.debug(f"Stored in vector memory: {content_type}/{doc_id[:12]}...")
            return doc_id

        except Exception as e:
            logger.error(f"Vector memory store failed: {e}")
            return None

    async def search(
        self,
        project_id: str,
        query: str,
        content_type: str = "agent_output",
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search vector memory for relevant content.

        Args:
            project_id: Project to search within (or None for global)
            query: Search query text
            content_type: Type of content to search
            top_k: Number of results to return

        Returns:
            List of matching documents with scores
        """
        if not self._ensure_client():
            return []

        try:
            collection = self._get_collection(f"crucibai_{content_type}")

            where_filter = {"project_id": project_id} if project_id else None

            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter,
            )

            documents = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    documents.append(
                        {
                            "content": doc,
                            "metadata": (
                                results["metadatas"][0][i]
                                if results.get("metadatas")
                                else {}
                            ),
                            "distance": (
                                results["distances"][0][i]
                                if results.get("distances")
                                else 0
                            ),
                            "id": results["ids"][0][i] if results.get("ids") else "",
                        }
                    )

            return documents

        except Exception as e:
            logger.error(f"Vector memory search failed: {e}")
            return []

    async def get_context_for_agent(
        self,
        project_id: str,
        agent_name: str,
        project_prompt: str,
        top_k: int = 3,
    ) -> str:
        """
        Get relevant context from vector memory for an agent.
        Used to enhance agent prompts with historical knowledge.

        Returns:
            Context string to prepend to agent prompt, or empty string
        """
        if not self._ensure_client():
            return ""

        query = f"{agent_name}: {project_prompt[:200]}"
        results = await self.search(project_id, query, "agent_output", top_k)

        if not results:
            return ""

        context_parts = []
        for r in results:
            if r.get("distance", 1) < 0.5:  # Only include relevant results
                context_parts.append(
                    f"[Previous: {r['metadata'].get('agent_name', 'unknown')}]\n{r['content'][:500]}"
                )

        if not context_parts:
            return ""

        return (
            f"\n--- RELEVANT CONTEXT FROM MEMORY ---\n"
            + "\n---\n".join(context_parts)
            + "\n--- END CONTEXT ---\n"
        )

    async def store_agent_output(
        self,
        project_id: str,
        agent_name: str,
        output: str,
        tokens_used: int = 0,
    ) -> Optional[str]:
        """Convenience method to store an agent's output in vector memory."""
        return await self.store(
            project_id=project_id,
            content_type="agent_output",
            content={"output": output, "agent_name": agent_name},
            metadata={"agent_name": agent_name, "tokens_used": tokens_used},
        )

    def is_available(self) -> bool:
        """Check if vector memory is available."""
        return _chroma_available and self._ensure_client()

    def _content_to_text(self, content: Dict[str, Any]) -> str:
        """Convert content dict to searchable text."""
        if isinstance(content, str):
            return content
        parts = []
        for key, value in content.items():
            if isinstance(value, str) and len(value) > 10:
                parts.append(f"{key}: {value}")
            elif isinstance(value, (dict, list)):
                parts.append(f"{key}: {json.dumps(value, default=str)[:500]}")
        return "\n".join(parts)

    def _generate_id(self, project_id: str, text: str) -> str:
        """Generate a deterministic document ID."""
        hash_input = f"{project_id}:{text[:200]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:24]


# Singleton instance
vector_memory = VectorMemory()

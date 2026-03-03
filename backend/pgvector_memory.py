"""
CrucibAI pgvector Memory Module
================================
Provides semantic search and embeddings using PostgreSQL pgvector extension.

Uses asyncpg to execute pgvector queries with the <-> distance operator
for efficient similarity search on embeddings.

Usage:
    from pgvector_memory import PgVectorMemory
    
    memory = PgVectorMemory()
    await memory.store_embedding("project_123", "agent_output", embedding_vector, metadata)
    results = await memory.search_similar("project_123", query_embedding, top_k=5)
"""
import json
import logging
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import asyncpg

logger = logging.getLogger(__name__)

class PgVectorMemory:
    """
    Vector memory using PostgreSQL pgvector extension.
    Stores embeddings and performs similarity search using L2 distance (<-> operator).
    """
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self._initialized = False
    
    async def initialize(self, db_pool):
        """Initialize pgvector extension and create embeddings table."""
        self.db_pool = db_pool
        
        try:
            async with self.db_pool.acquire() as conn:
                # Enable pgvector extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Create embeddings table if not exists
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id SERIAL PRIMARY KEY,
                        project_id VARCHAR(255) NOT NULL,
                        content_type VARCHAR(100) NOT NULL,
                        embedding vector(1536),
                        metadata JSONB,
                        content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT idx_embeddings_project_type UNIQUE (project_id, content_type)
                    );
                """)
                
                # Create index for fast similarity search
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
                    ON embeddings USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
                
            self._initialized = True
            logger.info("✅ pgvector extension initialized and embeddings table created")
        except Exception as e:
            logger.error(f"❌ pgvector initialization failed: {e}")
            raise
    
    async def store_embedding(
        self,
        project_id: str,
        content_type: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        content: Optional[str] = None,
    ) -> Optional[int]:
        """
        Store an embedding vector in pgvector.
        
        Args:
            project_id: Project identifier
            content_type: Type of content (agent_output, code_snippet, etc.)
            embedding: Vector embedding (1536-dimensional for OpenAI embeddings)
            metadata: Additional metadata as JSON
            content: Original text content
            
        Returns:
            Embedding ID if stored, None on failure
        """
        if not self.db_pool:
            logger.warning("pgvector not initialized")
            return None
        
        try:
            async with self.db_pool.acquire() as conn:
                # Convert embedding list to pgvector format
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                
                result = await conn.fetchval("""
                    INSERT INTO embeddings (project_id, content_type, embedding, metadata, content)
                    VALUES ($1, $2, $3::vector, $4, $5)
                    ON CONFLICT (project_id, content_type) DO UPDATE
                    SET embedding = $3::vector, metadata = $4, content = $5, created_at = CURRENT_TIMESTAMP
                    RETURNING id;
                """, project_id, content_type, embedding_str, json.dumps(metadata or {}), content)
                
                logger.debug(f"Stored embedding {result} for {project_id}/{content_type}")
                return result
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            return None
    
    async def search_similar(
        self,
        project_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        content_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings using pgvector <-> distance operator.
        
        Args:
            project_id: Project to search within
            query_embedding: Query vector (1536-dimensional)
            top_k: Number of results to return
            content_type: Optional filter by content type
            
        Returns:
            List of similar embeddings with metadata and distance scores
        """
        if not self.db_pool:
            logger.warning("pgvector not initialized")
            return []
        
        try:
            async with self.db_pool.acquire() as conn:
                # Convert query embedding to pgvector format
                embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
                
                # Use <-> operator for L2 (Euclidean) distance
                # Lower distance = more similar
                where_clause = "project_id = $1"
                params = [project_id, embedding_str, top_k]
                
                if content_type:
                    where_clause += " AND content_type = $4"
                    params = [project_id, embedding_str, top_k, content_type]
                
                query = f"""
                    SELECT 
                        id,
                        project_id,
                        content_type,
                        embedding <-> $2::vector AS distance,
                        metadata,
                        content,
                        created_at
                    FROM embeddings
                    WHERE {where_clause}
                    ORDER BY embedding <-> $2::vector
                    LIMIT $3;
                """
                
                rows = await conn.fetch(query, *params)
                
                results = []
                for row in rows:
                    results.append({
                        "id": row["id"],
                        "project_id": row["project_id"],
                        "content_type": row["content_type"],
                        "distance": float(row["distance"]),
                        "metadata": json.loads(row["metadata"] or "{}"),
                        "content": row["content"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    })
                
                logger.debug(f"Found {len(results)} similar embeddings for {project_id}")
                return results
        except Exception as e:
            logger.error(f"pgvector search failed: {e}")
            return []
    
    async def get_context_for_agent(
        self,
        project_id: str,
        query_embedding: List[float],
        agent_name: str,
        top_k: int = 3,
    ) -> str:
        """
        Get relevant context from pgvector for an agent.
        Used to enhance agent prompts with historical knowledge.
        
        Returns:
            Context string to prepend to agent prompt, or empty string
        """
        results = await self.search_similar(project_id, query_embedding, top_k, "agent_output")
        
        if not results:
            return ""
        
        context_parts = []
        for r in results:
            # Only include results with low distance (high similarity)
            if r["distance"] < 0.5:
                metadata = r.get("metadata", {})
                context_parts.append(f"[Previous: {metadata.get('agent_name', 'unknown')}]\n{r['content'][:500]}")
        
        if not context_parts:
            return ""
        
        return f"\n--- RELEVANT CONTEXT FROM VECTOR MEMORY ---\n" + "\n---\n".join(context_parts) + "\n--- END CONTEXT ---\n"
    
    def is_available(self) -> bool:
        """Check if pgvector is available and initialized."""
        return self._initialized and self.db_pool is not None


# Singleton instance (initialized at startup)
pgvector_memory = PgVectorMemory()

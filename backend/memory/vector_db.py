# backend/memory/vector_db.py
"""
Vector database integration for project context management.
Stores and retrieves agent outputs, requirements, and decisions.
Prevents token overflow through memory retrieval and forking.
"""

import os
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pinecone import Pinecone, ServerlessSpec
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class VectorMemory:
    """
    Manage project context using Pinecone vector database.
    Stores all agent outputs and allows intelligent context retrieval.
    """
    
    def __init__(self):
        # Initialize Pinecone
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        
        # Create or get index
        self.index_name = "crucibai-memory"
        self._ensure_index_exists()
        self.index = self.pc.Index(self.index_name)
        
        # Initialize embeddings client
        self.embeddings_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.embedding_dimension = 1536
        self.max_metadata_size = 500  # characters
    
    def _ensure_index_exists(self):
        """Create index if it doesn't exist."""
        try:
            # Check if index exists
            indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in indexes]
            
            if self.index_name not in index_names:
                logger.info(f"Creating Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.embedding_dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                logger.info(f"Index {self.index_name} created successfully")
            else:
                logger.info(f"Index {self.index_name} already exists")
        except Exception as e:
            logger.error(f"Error ensuring index exists: {e}")
            raise
    
    async def add_memory(
        self,
        project_id: str,
        text: str,
        memory_type: str,  # "output", "requirement", "decision", "error", "schema"
        agent_name: Optional[str] = None,
        phase: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tokens: int = 0
    ) -> str:
        """
        Embed text and store in vector database.
        Called after each significant agent operation.
        """
        try:
            # Truncate text for embedding
            embedding_text = text[:2000]
            
            # Get embedding from OpenAI
            embedding = await self._embed_text(embedding_text)
            
            # Create unique vector ID
            vector_id = f"{project_id}#{agent_name}#{int(datetime.utcnow().timestamp())}#{hash(text) % 1000000}"
            
            # Prepare metadata
            meta = {
                "project_id": project_id,
                "type": memory_type,
                "agent": agent_name or "system",
                "phase": phase or "unknown",
                "timestamp": datetime.utcnow().isoformat(),
                "tokens": str(tokens),
                "text": text[:self.max_metadata_size]  # Preview
            }
            
            if metadata:
                meta.update(metadata)
            
            # Upsert to Pinecone
            self.index.upsert(
                vectors=[
                    {
                        "id": vector_id,
                        "values": embedding,
                        "metadata": meta
                    }
                ]
            )
            
            logger.info(f"Added memory: {vector_id}")
            return vector_id
        
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            raise
    
    async def retrieve_context(
        self,
        project_id: str,
        query: str,
        top_k: int = 5,
        memory_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Retrieve relevant memories using semantic search.
        Used when agent needs context to proceed.
        """
        try:
            # Embed query
            query_embedding = await self._embed_text(query)
            
            # Build filter for project
            filter_dict = {
                "project_id": {"$eq": project_id}
            }
            
            # Add memory type filter if specified
            if memory_types:
                filter_dict["type"] = {"$in": memory_types}
            
            # Search Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
            
            # Format results
            memories = []
            for match in results.get('matches', []):
                meta = match.get('metadata', {})
                memories.append({
                    "id": match['id'],
                    "text": meta.get('text', ''),
                    "type": meta.get('type', ''),
                    "agent": meta.get('agent', ''),
                    "phase": meta.get('phase', ''),
                    "timestamp": meta.get('timestamp', ''),
                    "relevance_score": match['score'],
                    "tokens": int(meta.get('tokens', 0))
                })
            
            logger.info(f"Retrieved {len(memories)} memories for project {project_id}")
            return memories
        
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []
    
    async def count_project_tokens(self, project_id: str) -> int:
        """
        Count total tokens used in a project.
        Used to detect token overflow and trigger forking.
        """
        try:
            # Query all vectors for project (returns only IDs)
            results = self.index.query(
                vector=[0] * self.embedding_dimension,
                top_k=10000,
                include_metadata=True,
                filter={"project_id": {"$eq": project_id}}
            )
            
            # Sum tokens from metadata
            total_tokens = 0
            for match in results.get('matches', []):
                meta = match.get('metadata', {})
                tokens = int(meta.get('tokens', 0))
                total_tokens += tokens
            
            logger.info(f"Project {project_id} token count: {total_tokens}")
            return total_tokens
        
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return 0
    
    async def delete_project_memory(self, project_id: str) -> bool:
        """Delete all memories for a project (cleanup after completion)."""
        try:
            # Get all vector IDs for project
            results = self.index.query(
                vector=[0] * self.embedding_dimension,
                top_k=10000,
                filter={"project_id": {"$eq": project_id}}
            )
            
            # Delete all vectors
            vector_ids = [match['id'] for match in results.get('matches', [])]
            if vector_ids:
                self.index.delete(ids=vector_ids)
                logger.info(f"Deleted {len(vector_ids)} memories for project {project_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting project memory: {e}")
            return False
    
    async def _embed_text(self, text: str) -> List[float]:
        """Embed text using OpenAI API."""
        try:
            response = await self.embeddings_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            # Return zero vector on error
            return [0.0] * self.embedding_dimension

# Global instance
_vector_memory: Optional[VectorMemory] = None

async def get_vector_memory() -> VectorMemory:
    """Get or create singleton vector memory instance."""
    global _vector_memory
    if _vector_memory is None:
        _vector_memory = VectorMemory()
    return _vector_memory

# Helper functions for easy access
async def store_memory(
    project_id: str,
    text: str,
    memory_type: str,
    **kwargs
) -> str:
    """Helper to store memory."""
    vm = await get_vector_memory()
    return await vm.add_memory(project_id, text, memory_type, **kwargs)

async def retrieve_memory(
    project_id: str,
    query: str,
    top_k: int = 5
) -> List[Dict]:
    """Helper to retrieve memory."""
    vm = await get_vector_memory()
    return await vm.retrieve_context(project_id, query, top_k)

async def get_project_tokens(project_id: str) -> int:
    """Helper to count tokens."""
    vm = await get_vector_memory()
    return await vm.count_project_tokens(project_id)

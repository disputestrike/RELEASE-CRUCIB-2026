"""Embedding service for RAG and semantic search"""

import json
import os
from typing import List

import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


async def generate_embedding(text: str) -> List[float]:
    """Generate embedding using OpenAI text-embedding-3-small"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"model": EMBEDDING_MODEL, "input": text, "encoding_format": "float"},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]


async def embed_and_store(
    project_id: str, agent_name: str, content: str, db_connection
) -> dict:
    """Generate embedding and store in vector database"""
    try:
        embedding = await generate_embedding(content)

        # Store in PostgreSQL with pgvector
        result = await db_connection.execute(
            """
            INSERT INTO vector_store (project_id, agent_name, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, created_at
        """,
            (
                project_id,
                agent_name,
                content,
                embedding,
                json.dumps({"tokens": len(content.split())}),
            ),
        )

        return {
            "success": True,
            "embedding_id": result[0][0],
            "created_at": result[0][1],
            "dimensions": len(embedding),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def search_similar(
    project_id: str, query: str, limit: int = 5, db_connection=None
) -> List[dict]:
    """Search for similar vectors using cosine similarity"""
    try:
        query_embedding = await generate_embedding(query)

        # Search using pgvector <-> operator
        results = await db_connection.fetch(
            """
            SELECT id, agent_name, content, 
                   (embedding <-> %s::vector) as distance,
                   created_at
            FROM vector_store
            WHERE project_id = %s
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """,
            (query_embedding, project_id, query_embedding, limit),
        )

        return [
            {
                "id": r[0],
                "agent_name": r[1],
                "content": r[2],
                "similarity": 1 - r[3],  # Convert distance to similarity
                "created_at": r[4],
            }
            for r in results
        ]
    except Exception as e:
        return []

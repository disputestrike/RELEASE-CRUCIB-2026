"""Unified memory service for planner/executor/controller usage."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .vector_db import get_vector_memory


class MemoryService:
    async def store_step_summary(
        self,
        *,
        project_id: str,
        job_id: str,
        text: str,
        agent_name: str,
        phase: str,
        step_key: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        vm = await get_vector_memory()
        return await vm.add_memory(
            project_id=project_id or job_id,
            text=text,
            memory_type="step_output",
            agent_name=agent_name or "system",
            phase=phase or "unknown",
            tokens=0,
            metadata={
                "job_id": job_id,
                "step_key": step_key,
                **(metadata or {}),
            },
        )

    async def retrieve_project_context(
        self,
        *,
        project_id: str,
        query: str,
        top_k: int = 5,
        memory_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        vm = await get_vector_memory()
        return await vm.retrieve_context(
            project_id=project_id,
            query=query,
            top_k=top_k,
            memory_types=memory_types,
        )


_memory_service: Optional[MemoryService] = None


async def get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service

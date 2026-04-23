"""Unified memory service for planner/executor/controller usage."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .vector_db import get_vector_memory


class MemoryService:
    def _normalized_project_id(self, project_id: str, job_id: str | None = None) -> str:
        return project_id or job_id or "unknown-project"

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
            project_id=self._normalized_project_id(project_id, job_id),
            text=text,
            memory_type="step_output",
            agent_name=agent_name or "system",
            phase=phase or "unknown",
            tokens=0,
            metadata={
                "job_id": job_id,
                "step_key": step_key,
                "scope": "step",
                **(metadata or {}),
            },
        )

    async def store_controller_checkpoint(
        self,
        *,
        project_id: str,
        job_id: str,
        text: str,
        phase: str,
        checkpoint_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        vm = await get_vector_memory()
        return await vm.add_memory(
            project_id=self._normalized_project_id(project_id, job_id),
            text=text,
            memory_type="controller_checkpoint",
            agent_name="Controller Brain",
            phase=phase or "unknown",
            tokens=0,
            metadata={
                "job_id": job_id,
                "checkpoint_type": checkpoint_type,
                "scope": "controller",
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
        metadata_filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict]:
        vm = await get_vector_memory()
        return await vm.retrieve_context(
            project_id=project_id,
            query=query,
            top_k=top_k,
            memory_types=memory_types,
            metadata_filters=metadata_filters,
        )

    async def retrieve_job_context(
        self,
        *,
        project_id: str,
        job_id: str,
        query: str,
        top_k: int = 5,
        memory_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        return await self.retrieve_project_context(
            project_id=self._normalized_project_id(project_id, job_id),
            query=query,
            top_k=top_k,
            memory_types=memory_types,
            metadata_filters={"job_id": job_id},
        )

    async def build_context_packet(
        self,
        *,
        project_id: str,
        query: str,
        job_id: Optional[str] = None,
        phase: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        normalized_project_id = self._normalized_project_id(project_id, job_id)
        vm = await get_vector_memory()
        metadata_filters = {
            **({"job_id": job_id} if job_id else {}),
            **({"phase": phase} if phase else {}),
        }
        relevant = await vm.retrieve_context(
            project_id=normalized_project_id,
            query=query,
            top_k=top_k,
            metadata_filters=metadata_filters,
        )
        recent = await vm.list_recent_context(
            project_id=normalized_project_id,
            limit=top_k,
            metadata_filters=metadata_filters,
        )
        tokens = await vm.count_project_tokens(
            normalized_project_id,
            metadata_filters=metadata_filters,
        )
        return {
            "provider": getattr(vm, "provider", "memory"),
            "project_id": normalized_project_id,
            "job_id": job_id,
            "phase": phase,
            "query": query,
            "relevant_memories": relevant,
            "recent_memories": recent,
            "token_usage": tokens,
        }


_memory_service: Optional[MemoryService] = None


async def get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..agent_dag import AGENT_DAG, build_dynamic_dag
from ..agents.schemas import IntentSchema

from backend.project_state import WORKSPACE_ROOT
from backend.services.events import event_bus
from backend.services.runtime.task_manager import task_manager


class RuntimeStateAdapter:
    """RuntimeState compatibility adapter backed by runtime TaskManager storage.

    This keeps older job/event/step service code working while all execution is
    owned by RuntimeEngine + TaskManager.
    """

    def __init__(self) -> None:
        self._pool = None

    def set_pool(self, pool: Any) -> None:
        self._pool = pool

    async def ensure_job_fk_prerequisites(self, project_id: str, user_id: Optional[str]) -> None:
        """Ensure the projects row exists before inserting a job with this project_id."""
        if self._pool is None or not project_id:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO projects (id, doc)
                VALUES ($1, $2::jsonb)
                ON CONFLICT (id) DO NOTHING
                """,
                str(project_id),
                json.dumps({"user_id": str(user_id) if user_id else None, "created_by": "auto"}),
            )

    async def create_job(
        self,
        *,
        project_id: str,
        mode: str,
        goal: str,
        intent_schema: Optional[IntentSchema] = None,
        user_id: Optional[str],
    ) -> Dict[str, Any]:
        task = task_manager.create_task(
            project_id=project_id,
            description=goal,
            metadata={
                "mode": mode,
                "goal": goal,
                "user_id": user_id,
                "source": "runtime_state.create_job",
                "intent_schema": intent_schema.model_dump() if intent_schema else None,
            },
            intent_schema=intent_schema,
        )
        job = self._job_view(task)
        await self.ensure_job_fk_prerequisites(project_id, user_id)
        await self._upsert_job_row(job)
        await self._create_steps_from_dag(job["id"], project_id, user_id, intent_schema)
        return job

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        project_id = self._find_project_for_job(job_id)
        if not project_id:
            return None
        task = task_manager.get_task(project_id, job_id)
        if not task:
            return None
        return self._job_view(task)

    async def list_jobs_for_user(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for project_id in self._list_projects():
            rows = task_manager.list_project_tasks(project_id, limit=1000)
            for row in rows:
                meta = row.get("metadata") or {}
                if str(meta.get("user_id") or "") != str(user_id):
                    continue
                out.append(self._job_view(row))
        out.sort(key=lambda r: float(r.get("updated_at") or r.get("created_at") or 0), reverse=True)
        return out[: max(1, int(limit))]

    async def update_job_state(
        self,
        job_id: str,
        status: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        project_id = self._find_project_for_job(job_id)
        if not project_id:
            return None
        task = task_manager.update_task(project_id, job_id, status=status, metadata=extra or {})
        if not task:
            return None
        job = self._job_view(task)
        await self._upsert_job_row(job, extra or {})
        await self.append_job_event(job_id, "job_status_changed", {"status": status, **(extra or {})})
        return job

    async def create_step(
        self,
        *,
        job_id: str,
        step_key: str,
        agent_name: str,
        phase: str,
        depends_on: Optional[List[str]] = None,
        order_index: int = 0,
    ) -> Dict[str, Any]:
        step = {
            "id": f"stp_{uuid.uuid4().hex[:12]}",
            "job_id": job_id,
            "step_key": step_key,
            "agent_name": agent_name,
            "phase": phase,
            "depends_on": list(depends_on or []),
            "order_index": int(order_index),
            "status": "pending",
            "retry_count": 0,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        steps = self._load_steps(job_id)
        steps.append(step)
        self._save_steps(job_id, steps)
        await self.append_job_event(job_id, "step_created", {"step_id": step["id"], "step_key": step_key})
        return dict(step)

    async def get_steps(self, job_id: str) -> List[Dict[str, Any]]:
        rows = self._load_steps(job_id)
        rows.sort(key=lambda s: (int(s.get("order_index") or 0), float(s.get("created_at") or 0)))
        return rows

    async def get_step(self, step_id: str) -> Optional[Dict[str, Any]]:
        for project_id in self._list_projects():
            for path in self._job_dir_candidates(project_id):
                sp = path / "steps.json"
                if not sp.exists():
                    continue
                try:
                    rows = json.loads(sp.read_text(encoding="utf-8"))
                except Exception:
                    continue
                for row in rows:
                    if str(row.get("id")) == str(step_id):
                        return dict(row)
        return None

    async def update_step_state(
        self,
        step_id: str,
        status: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        for project_id in self._list_projects():
            for path in self._job_dir_candidates(project_id):
                sp = path / "steps.json"
                if not sp.exists():
                    continue
                try:
                    rows = json.loads(sp.read_text(encoding="utf-8"))
                except Exception:
                    continue
                changed = False
                step: Optional[Dict[str, Any]] = None
                for row in rows:
                    if str(row.get("id")) != str(step_id):
                        continue
                    row["status"] = status
                    row["updated_at"] = time.time()
                    if extra:
                        row.update(extra)
                    step = dict(row)
                    changed = True
                    break
                if not changed:
                    continue
                sp.write_text(json.dumps(rows, indent=2), encoding="utf-8")
                if step:
                    await self.append_job_event(step.get("job_id") or "", "step_status_changed", {"step_id": step_id, "status": status})
                return step
        return None

    async def append_job_event(
        self,
        job_id: str,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        event_payload: Dict[str, Any] = {}
        if isinstance(payload, dict):
            event_payload.update(payload)
        elif payload is not None:
            event_payload["value"] = payload
        if kwargs:
            event_payload.update(kwargs)
        rows = self._load_events(job_id)
        event = {
            "id": f"evt_{uuid.uuid4().hex[:12]}",
            "job_id": job_id,
            "event_type": event_type,
            "payload_json": json.dumps(event_payload, ensure_ascii=True),
            "created_at": time.time(),
        }
        rows.append(event)
        if len(rows) > 5000:
            rows = rows[-5000:]
        self._save_events(job_id, rows)
        event_bus.emit(event_type, {"job_id": job_id, **event_payload})
        return dict(event)

    async def get_job_events(
        self,
        job_id: str,
        since_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        rows = self._load_events(job_id)
        if since_id:
            idx = -1
            for i, row in enumerate(rows):
                if str(row.get("id")) == str(since_id):
                    idx = i
                    break
            if idx >= 0:
                rows = rows[idx + 1 :]
        rows = rows[-max(1, int(limit)) :]
        return [dict(r) for r in rows]

    async def save_checkpoint(self, job_id: str, checkpoint_key: str, data: Dict[str, Any]) -> None:
        cps = self._load_checkpoints(job_id)
        cps[str(checkpoint_key)] = {
            "data": data,
            "updated_at": time.time(),
        }
        self._save_checkpoints(job_id, cps)

    async def load_checkpoint(self, job_id: str, checkpoint_key: str) -> Optional[Dict[str, Any]]:
        cps = self._load_checkpoints(job_id)
        row = cps.get(str(checkpoint_key))
        if not row:
            return None
        return row.get("data")

    async def _create_steps_from_dag(
        self, job_id: str, project_id: str, user_id: Optional[str], intent_schema: Optional[IntentSchema]
    ) -> None:
        if not intent_schema:
            return

        dynamic_dag = build_dynamic_dag(intent_schema)
        
        # Create steps based on the dynamic DAG
        order_index = 0
        for agent_name, agent_info in dynamic_dag.items():
            await self.create_step(
                job_id=job_id,
                step_key=agent_name,
                agent_name=agent_name,
                phase="orchestration", # All dynamic DAG steps are part of orchestration phase
                depends_on=agent_info.get("depends_on", []),
                order_index=order_index,
            )
            order_index += 1

    def _job_view(self, task: Dict[str, Any]) -> Dict[str, Any]:
        meta = task.get("metadata") or {}
        return {
            "id": task.get("task_id"),
            "project_id": task.get("project_id"),
            "status": task.get("status"),
            "mode": meta.get("mode") or "guided",
            "goal": meta.get("goal") or task.get("description"),
            "user_id": meta.get("user_id"),
            "created_at": task.get("created_at"),
            "updated_at": task.get("updated_at"),
            "metadata": meta,
        }

    def _list_projects(self) -> List[str]:
        out: List[str] = []
        for child in WORKSPACE_ROOT.iterdir():
            if not child.is_dir():
                continue
            rt = child / "runtime_tasks"
            if rt.exists() and rt.is_dir():
                out.append(child.name)
        return out

    def _find_project_for_job(self, job_id: str) -> Optional[str]:
        for project_id in self._list_projects():
            candidate = WORKSPACE_ROOT / project_id / "runtime_tasks" / f"{job_id}.json"
            if candidate.exists():
                return project_id
        return None

    def _job_dir(self, job_id: str) -> Path:
        project_id = self._find_project_for_job(job_id)
        if not project_id:
            project_id = "runtime_compat"
        root = WORKSPACE_ROOT / project_id / "runtime_state" / job_id
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _job_dir_candidates(self, project_id: str) -> List[Path]:
        root = WORKSPACE_ROOT / project_id / "runtime_state"
        if not root.exists():
            return []
        return [p for p in root.iterdir() if p.is_dir()]

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _save_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_steps(self, job_id: str) -> List[Dict[str, Any]]:
        return self._load_json(self._job_dir(job_id) / "steps.json", [])

    def _save_steps(self, job_id: str, rows: List[Dict[str, Any]]) -> None:
        self._save_json(self._job_dir(job_id) / "steps.json", rows)

    def _load_events(self, job_id: str) -> List[Dict[str, Any]]:
        return self._load_json(self._job_dir(job_id) / "events.json", [])

    def _save_events(self, job_id: str, rows: List[Dict[str, Any]]) -> None:
        self._save_json(self._job_dir(job_id) / "events.json", rows)

    def _load_checkpoints(self, job_id: str) -> Dict[str, Any]:
        return self._load_json(self._job_dir(job_id) / "checkpoints.json", {})

    def _save_checkpoints(self, job_id: str, data: Dict[str, Any]) -> None:
        self._save_json(self._job_dir(job_id) / "checkpoints.json", data)

    async def _upsert_job_row(
        self,
        job: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self._pool is None:
            return
        payload = dict(job)
        if extra:
            payload.update(extra)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO jobs (
                    id, project_id, user_id, status, mode, goal,
                    current_phase, error_message, failure_reason,
                    created_at, updated_at
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,NOW(),NOW())
                ON CONFLICT (id) DO UPDATE SET
                    project_id = EXCLUDED.project_id,
                    user_id = EXCLUDED.user_id,
                    status = EXCLUDED.status,
                    mode = EXCLUDED.mode,
                    goal = EXCLUDED.goal,
                    current_phase = COALESCE(EXCLUDED.current_phase, jobs.current_phase),
                    error_message = COALESCE(EXCLUDED.error_message, jobs.error_message),
                    failure_reason = COALESCE(EXCLUDED.failure_reason, jobs.failure_reason),
                    updated_at = NOW()
                """,
                str(payload.get("id") or ""),
                str(payload.get("project_id") or ""),
                payload.get("user_id"),
                str(payload.get("status") or "planned"),
                str(payload.get("mode") or "guided"),
                str(payload.get("goal") or ""),
                payload.get("current_phase"),
                payload.get("error_message"),
                payload.get("failure_reason"),
            )


runtime_state = RuntimeStateAdapter()


def set_pool(pool: Any) -> None:
    runtime_state.set_pool(pool)


async def ensure_job_fk_prerequisites(project_id: str, user_id: Optional[str]) -> None:
    await runtime_state.ensure_job_fk_prerequisites(project_id, user_id)


async def create_job(*, project_id: str, mode: str, goal: str, user_id: Optional[str]) -> Dict[str, Any]:
    return await runtime_state.create_job(project_id=project_id, mode=mode, goal=goal, user_id=user_id)


async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return await runtime_state.get_job(job_id)


async def list_jobs_for_user(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    return await runtime_state.list_jobs_for_user(user_id, limit=limit)


async def update_job_state(job_id: str, status: str, extra: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    return await runtime_state.update_job_state(job_id, status, extra=extra)


async def create_step(
    *,
    job_id: str,
    step_key: str,
    agent_name: str,
    phase: str,
    depends_on: Optional[List[str]] = None,
    order_index: int = 0,
) -> Dict[str, Any]:
    return await runtime_state.create_step(
        job_id=job_id,
        step_key=step_key,
        agent_name=agent_name,
        phase=phase,
        depends_on=depends_on,
        order_index=order_index,
    )


async def get_steps(job_id: str) -> List[Dict[str, Any]]:
    return await runtime_state.get_steps(job_id)


async def get_step(step_id: str) -> Optional[Dict[str, Any]]:
    return await runtime_state.get_step(step_id)


async def update_step_state(step_id: str, status: str, extra: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    return await runtime_state.update_step_state(step_id, status, extra=extra)


async def append_job_event(
    job_id: str,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    return await runtime_state.append_job_event(job_id, event_type, payload, **kwargs)


async def get_job_events(job_id: str, since_id: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    return await runtime_state.get_job_events(job_id, since_id=since_id, limit=limit)


async def save_checkpoint(job_id: str, checkpoint_key: str, data: Dict[str, Any]) -> None:
    await runtime_state.save_checkpoint(job_id, checkpoint_key, data)


async def load_checkpoint(job_id: str, checkpoint_key: str) -> Optional[Dict[str, Any]]:
    return await runtime_state.load_checkpoint(job_id, checkpoint_key)


def set_job(job_id: str, payload: Dict[str, Any]) -> None:
    project_id = str(payload.get("project_id") or "runtime_compat")
    task_manager.create_task(
        project_id=project_id,
        description=payload.get("goal") or payload.get("description") or "runtime_state.set_job",
        metadata={**(payload.get("metadata") or {}), "source": "runtime_state.set_job"},
    )


def _coerce_json_text_updates(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            return loaded if isinstance(loaded, dict) else {"value": loaded}
        except Exception:
            return {"value": value}
    if value is None:
        return {}
    return {"value": value}

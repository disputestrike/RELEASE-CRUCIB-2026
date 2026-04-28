from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

try:
    from services.brain_layer import BrainLayer
    from services.conversation_manager import ContextManager
    from services.events import event_bus
    from services.runtime.task_manager import task_manager
except ImportError:  # pragma: no cover
    from backend.services.brain_layer import BrainLayer  # type: ignore[no-redef]
    from backend.services.conversation_manager import ContextManager  # type: ignore[no-redef]
    from backend.services.events import event_bus  # type: ignore[no-redef]
    from backend.services.runtime.task_manager import task_manager  # type: ignore[no-redef]

router = APIRouter(prefix="/api", tags=["chat"])


async def send_chat_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = str(payload.get("session_id") or "session-compat")
    project_id = str(payload.get("project_id") or "project-compat")
    message = str(payload.get("message") or "")

    event_bus.emit("chat.request.started", {"session_id": session_id, "project_id": project_id})
    task = task_manager.create_task(project_id=project_id, description=message)
    event_bus.emit("task.started", {"task_id": task["task_id"], "project_id": project_id})

    try:
        session = ContextManager().create_session(session_id)
        brain = BrainLayer()
        assessed = brain.assess_request(session, message)
        event_bus.emit("brain.assessed", {"task_id": task["task_id"]})
        event_bus.emit("brain.execution.started", {"task_id": task["task_id"]})

        execution = await brain.execute_request(
            session,
            message,
            execution_meta={"project_id": project_id, "task_id": task["task_id"]},
        )
        agent_outputs = (
            execution.get("agent_outputs")
            or (execution.get("execution") or {}).get("agent_outputs")
            or []
        )
        if not agent_outputs:
            fallback_result = execution.get("result") or execution.get("assistant_response")
            if fallback_result is not None:
                agent_outputs = [{"result": fallback_result}]
        execution_payload = dict(execution)
        execution_payload.setdefault("agent_outputs", agent_outputs)
        status = "completed" if execution.get("status") not in {"execution_failed", "execution_cancelled"} else "failed"
        task_manager.update_task(project_id, task["task_id"], status=status, metadata={"execution": execution_payload})
        event_bus.emit("task.updated", {"task_id": task["task_id"], "status": status})
        event_bus.emit("chat.request.completed", {"task_id": task["task_id"], "status": status})
        return {
            "status": "executed" if status == "completed" else "failed",
            "session_id": session_id,
            "project_id": project_id,
            "task_id": task["task_id"],
            "task_status": status,
            "assessment": assessed,
            "execution": execution_payload,
        }
    except Exception as exc:
        task_manager.update_task(project_id, task["task_id"], status="failed", metadata={"error": str(exc)})
        event_bus.emit("task.updated", {"task_id": task["task_id"], "status": "failed"})
        event_bus.emit("chat.request.completed", {"task_id": task["task_id"], "status": "failed"})
        return {
            "status": "failed",
            "session_id": session_id,
            "project_id": project_id,
            "task_id": task["task_id"],
            "task_status": "failed",
            "error": str(exc),
        }

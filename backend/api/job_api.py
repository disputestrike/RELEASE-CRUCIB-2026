"""
Job API - Persistent Build Continuation Endpoints.

All 15 required endpoints for job control:
- 9 GET endpoints for reading state
- 6 POST endpoints for controlling execution
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import asyncio

from ..db.build_contract_models import (
    Job, GeneratedFile, JobEvent, ContractDelta, 
    ProofItem, VerifierResult, RepairAttempt, Screenshot,
    ExportGateResult, get_db_session
)
from ..orchestration.build_contract import BuildContract, ContractDelta as ContractDeltaModel
from ..orchestration.final_assembly_agent import FinalAssemblyAgent

app = FastAPI()


# ============== Pydantic Models ==============

class JobCreateRequest(BaseModel):
    prompt: str
    attachments: List[Dict] = []


class InstructionRequest(BaseModel):
    instruction: str


class RetryRequest(BaseModel):
    node_ids: Optional[List[str]] = None


class ContractApprovalRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None


# ============== GET ENDPOINTS (Reading State) ==============

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, db=Depends(get_db_session)) -> Dict[str, Any]:
    """
    Get full job state including contract, progress, status.
    
    Used by UI to display current build status.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "dag_state": job.dag_state,
        "contract_status": job.contract_status,
        "contract_version": job.contract_version,
        "current_phase": job.current_phase,
        "completed_nodes": job.completed_nodes,
        "failed_nodes": job.failed_nodes,
        "paused_nodes": job.paused_nodes,
        "contract_progress": job.contract_progress,
        "export_allowed": job.export_allowed,
        "export_blocked_reason": job.export_blocked_reason,
        "quality_score": job.quality_score,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "last_activity_at": job.last_activity_at.isoformat() if job.last_activity_at else None,
        "resume_token": job.resume_token,
        "can_resume": job.dag_state in ["paused", "failed_recoverable"],
        "can_repair": job.dag_state == "failed_recoverable",
        "can_export": job.export_allowed and job.dag_state == "completed"
    }


@app.get("/api/jobs/{job_id}/state")
async def get_job_state(job_id: str, db=Depends(get_db_session)) -> Dict[str, Any]:
    """
    Get current DAG state: completed, failed, paused nodes.
    
    Used to render progress bar and node status.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "dag_state": job.dag_state,
        "current_phase": job.current_phase,
        "completed_nodes": job.completed_nodes,
        "failed_nodes": job.failed_nodes,
        "paused_nodes": job.paused_nodes,
        "progress_percent": _calculate_progress(job)
    }


@app.get("/api/jobs/{job_id}/files")
async def get_job_files(job_id: str, db=Depends(get_db_session)) -> List[Dict[str, Any]]:
    """
    Get all generated files with metadata.
    
    Used by file explorer in UI.
    """
    files = db.query(GeneratedFile).filter(GeneratedFile.job_id == job_id).all()
    
    return [
        {
            "id": f.id,
            "path": f.path,
            "size_bytes": f.size_bytes,
            "language": f.language,
            "writer_agent": f.writer_agent,
            "syntax_valid": f.syntax_valid,
            "import_resolves": f.import_resolves,
            "created_at": f.created_at.isoformat() if f.created_at else None
        }
        for f in files
    ]


@app.get("/api/jobs/{job_id}/files/{file_path:path}")
async def get_file_content(job_id: str, file_path: str, db=Depends(get_db_session)) -> Dict[str, str]:
    """
    Get specific file content.
    
    Used by code editor in UI.
    """
    file = db.query(GeneratedFile).filter(
        GeneratedFile.job_id == job_id,
        GeneratedFile.path == file_path
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {
        "path": file.path,
        "content": file.content,
        "language": file.language
    }


@app.get("/api/jobs/{job_id}/proof")
async def get_job_proof(job_id: str, db=Depends(get_db_session)) -> List[Dict[str, Any]]:
    """
    Get all proof items (build, preview, route, database proofs).
    
    Used to display verification status.
    """
    proofs = db.query(ProofItem).filter(ProofItem.job_id == job_id).all()
    
    return [
        {
            "id": p.id,
            "type": p.proof_type,
            "category": p.category,
            "verified": p.verified,
            "score_value": p.score_value,
            "payload": p.payload,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in proofs
    ]


@app.get("/api/jobs/{job_id}/errors")
async def get_job_errors(job_id: str, db=Depends(get_db_session)) -> List[Dict[str, Any]]:
    """
    Get error history with repair attempts.
    
    Used to display failure analysis and repair options.
    """
    # Get errors from events
    error_events = db.query(JobEvent).filter(
        JobEvent.job_id == job_id,
        JobEvent.event_type.in_(["node_fail", "repair_failed"])
    ).all()
    
    # Get repair attempts
    repairs = db.query(RepairAttempt).filter(RepairAttempt.job_id == job_id).all()
    
    return {
        "errors": [
            {
                "id": e.id,
                "type": e.event_type,
                "payload": e.payload,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None
            }
            for e in error_events
        ],
        "repair_attempts": [
            {
                "id": r.id,
                "error_type": r.error_type,
                "repair_agents": r.repair_agents,
                "success": r.success,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in repairs
        ]
    }


@app.get("/api/jobs/{job_id}/contract")
async def get_build_contract(job_id: str, db=Depends(get_db_session)) -> Dict[str, Any]:
    """
    Get current BuildContract (with version).
    
    Used to display plan and approval UI.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "contract": job.contract_json,
        "version": job.contract_version,
        "status": job.contract_status
    }


@app.get("/api/jobs/{job_id}/deltas")
async def get_contract_deltas(job_id: str, db=Depends(get_db_session)) -> List[Dict[str, Any]]:
    """
    Get contract change history.
    
    Used to show how plan evolved.
    """
    deltas = db.query(ContractDelta).filter(
        ContractDelta.job_id == job_id
    ).order_by(ContractDelta.delta_version).all()
    
    return [
        {
            "id": d.id,
            "version": d.delta_version,
            "changes": d.changes,
            "reason": d.reason,
            "trigger": d.trigger,
            "approved_by": d.approved_by,
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in deltas
    ]


@app.get("/api/jobs/{job_id}/screenshots")
async def get_screenshots(job_id: str, db=Depends(get_db_session)) -> List[Dict[str, Any]]:
    """
    Get all visual QA screenshots.
    
    Used to display preview thumbnails.
    """
    screenshots = db.query(Screenshot).filter(Screenshot.job_id == job_id).all()
    
    return [
        {
            "id": s.id,
            "route": s.route,
            "viewport": s.viewport,
            "visual_check_results": s.visual_check_results,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in screenshots
    ]


@app.get("/api/jobs/{job_id}/events")
async def get_events(
    job_id: str, 
    since: Optional[datetime] = None,
    db=Depends(get_db_session)
) -> List[Dict[str, Any]]:
    """
    Get event log for replay/debugging.
    
    Used for diagnostics and replay.
    """
    query = db.query(JobEvent).filter(JobEvent.job_id == job_id)
    
    if since:
        query = query.filter(JobEvent.timestamp > since)
    
    events = query.order_by(JobEvent.timestamp).all()
    
    return [
        {
            "id": e.id,
            "type": e.event_type,
            "payload": e.payload,
            "agent_id": e.agent_id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None
        }
        for e in events
    ]


# ============== POST ENDPOINTS (Controlling Execution) ==============

@app.post("/api/jobs/{job_id}/pause")
async def pause_job(job_id: str, db=Depends(get_db_session)) -> Dict[str, Any]:
    """
    Pause active build.
    
    Transitions: running → paused
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.dag_state != "running":
        raise HTTPException(status_code=400, detail=f"Cannot pause job in state: {job.dag_state}")
    
    job.dag_state = "paused"
    job.updated_at = datetime.utcnow()
    job.last_activity_at = datetime.utcnow()
    
    # Emit event
    event = JobEvent(
        job_id=job_id,
        event_type="pause",
        payload={"reason": "user_requested"},
        dag_state_snapshot={"state": "paused"}
    )
    db.add(event)
    db.commit()
    
    return {"status": "paused", "job_id": job_id}


@app.post("/api/jobs/{job_id}/resume")
async def resume_job(
    job_id: str, 
    background_tasks: BackgroundTasks,
    db=Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Resume paused or failed_recoverable build.
    
    Transitions: paused → running, failed_recoverable → running
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.dag_state not in ["paused", "failed_recoverable"]:
        raise HTTPException(status_code=400, detail=f"Cannot resume job in state: {job.dag_state}")
    
    job.dag_state = "running"
    job.updated_at = datetime.utcnow()
    job.last_activity_at = datetime.utcnow()
    
    # Emit event
    event = JobEvent(
        job_id=job_id,
        event_type="resume",
        payload={"previous_state": job.dag_state},
        dag_state_snapshot={"state": "running"}
    )
    db.add(event)
    db.commit()
    
    # Trigger async resume
    background_tasks.add_task(_resume_build_async, job_id)
    
    return {"status": "resuming", "job_id": job_id}


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, db=Depends(get_db_session)) -> Dict[str, Any]:
    """
    Cancel build.
    
    Transitions: any → cancelled (irreversible)
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.dag_state == "cancelled":
        raise HTTPException(status_code=400, detail="Job already cancelled")
    
    previous_state = job.dag_state
    job.dag_state = "cancelled"
    job.updated_at = datetime.utcnow()
    job.last_activity_at = datetime.utcnow()
    
    # Emit event
    event = JobEvent(
        job_id=job_id,
        event_type="cancel",
        payload={"previous_state": previous_state},
        dag_state_snapshot={"state": "cancelled"}
    )
    db.add(event)
    db.commit()
    
    return {"status": "cancelled", "job_id": job_id}


@app.post("/api/jobs/{job_id}/instructions")
async def add_instruction(
    job_id: str, 
    request: InstructionRequest,
    db=Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Add user instruction during paused/failed build.
    
    May trigger ContractDelta if instruction changes scope.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.dag_state not in ["paused", "failed_recoverable", "repair_required"]:
        raise HTTPException(status_code=400, detail="Can only add instructions to paused/failed builds")
    
    # Store instruction
    event = JobEvent(
        job_id=job_id,
        event_type="user_instruction",
        payload={"instruction": request.instruction},
        dag_state_snapshot={"state": job.dag_state}
    )
    db.add(event)
    
    # Analyze if contract needs updating (simplified)
    if "add" in request.instruction.lower() or "fix" in request.instruction.lower():
        # Create ContractDelta
        delta = ContractDelta(
            job_id=job_id,
            delta_version=job.contract_version + 1,
            changes=[{"type": "user_instruction", "instruction": request.instruction}],
            reason=request.instruction,
            trigger="human_request",
            approved_by="user"
        )
        db.add(delta)
        
        job.contract_version += 1
        job.contract_status = "draft"  # Requires re-approval
        job.dag_state = "repair_required"
    
    job.updated_at = datetime.utcnow()
    job.last_activity_at = datetime.utcnow()
    db.commit()
    
    return {
        "status": "instruction_added",
        "job_id": job_id,
        "may_require_approval": job.contract_status == "draft"
    }


@app.post("/api/jobs/{job_id}/retry")
async def retry_failed(
    job_id: str, 
    request: RetryRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Retry failed nodes.
    
    If node_ids provided: retry specific nodes.
    If not provided: retry all failed nodes.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.dag_state not in ["failed_recoverable", "repair_required"]:
        raise HTTPException(status_code=400, detail="No failed nodes to retry")
    
    nodes_to_retry = request.node_ids or job.failed_nodes
    
    # Clear failed status for nodes being retried
    for node_id in nodes_to_retry:
        if node_id in job.failed_nodes:
            job.failed_nodes.remove(node_id)
    
    job.dag_state = "running"
    job.updated_at = datetime.utcnow()
    job.last_activity_at = datetime.utcnow()
    
    # Emit event
    event = JobEvent(
        job_id=job_id,
        event_type="retry",
        payload={"nodes": nodes_to_retry},
        dag_state_snapshot={"state": "running", "retrying": nodes_to_retry}
    )
    db.add(event)
    db.commit()
    
    # Trigger async retry
    background_tasks.add_task(_retry_nodes_async, job_id, nodes_to_retry)
    
    return {"status": "retrying", "job_id": job_id, "nodes": nodes_to_retry}


@app.post("/api/jobs/{job_id}/branch")
async def branch_job(
    job_id: str, 
    request: InstructionRequest,
    db=Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Create new job from current state with new instructions.
    
    Copies: BuildContract, files, disk state
    New: Instructions applied as ContractDelta
    """
    parent_job = db.query(Job).filter(Job.id == job_id).first()
    if not parent_job:
        raise HTTPException(status_code=404, detail="Parent job not found")
    
    # Create new job
    from ..db.build_contract_models import generate_uuid
    
    new_job = Job(
        id=generate_uuid(),
        user_id=parent_job.user_id,
        workspace_id=generate_uuid(),  # New workspace
        workspace_path=f"{parent_job.workspace_path}_branch_{generate_uuid()[:8]}",
        original_prompt=f"{parent_job.original_prompt}\n\n[BRANCH]: {request.instruction}",
        contract_id=parent_job.contract_id,
        contract_version=parent_job.contract_version,
        contract_status="draft",  # Requires approval
        contract_json=parent_job.contract_json,
        dag_state="pending",
        contract_progress=parent_job.contract_progress,
        resume_token=generate_uuid()
    )
    db.add(new_job)
    
    # Copy files
    parent_files = db.query(GeneratedFile).filter(GeneratedFile.job_id == job_id).all()
    for f in parent_files:
        new_file = GeneratedFile(
            job_id=new_job.id,
            path=f.path,
            content_hash=f.content_hash,
            size_bytes=f.size_bytes,
            language=f.language,
            writer_agent=f.writer_agent,
            content=f.content  # Copy full content
        )
        db.add(new_file)
    
    # Emit event
    event = JobEvent(
        job_id=job_id,
        event_type="branch",
        payload={"new_job_id": new_job.id, "instruction": request.instruction},
        dag_state_snapshot={"state": "branched", "new_job": new_job.id}
    )
    db.add(event)
    db.commit()
    
    return {
        "status": "branched",
        "parent_job_id": job_id,
        "new_job_id": new_job.id,
        "resume_token": new_job.resume_token
    }


@app.post("/api/jobs/{job_id}/approve-contract")
async def approve_contract(
    job_id: str,
    request: ContractApprovalRequest,
    db=Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Approve or reject draft BuildContract.
    
    Approval: Freezes contract and allows build to proceed.
    Rejection: Requires new contract generation.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.contract_status != "draft":
        raise HTTPException(status_code=400, detail=f"Contract not in draft status: {job.contract_status}")
    
    if request.approved:
        job.contract_status = "frozen"
        job.dag_state = "running"  # Can proceed
        
        # Update contract JSON with frozen status
        contract_data = job.contract_json
        contract_data["status"] = "frozen"
        job.contract_json = contract_data
        
        event_type = "contract_approved"
    else:
        job.dag_state = "waiting_for_user"
        event_type = "contract_rejected"
    
    job.updated_at = datetime.utcnow()
    job.last_activity_at = datetime.utcnow()
    
    # Emit event
    event = JobEvent(
        job_id=job_id,
        event_type=event_type,
        payload={
            "approved": request.approved,
            "feedback": request.feedback,
            "version": job.contract_version
        },
        dag_state_snapshot={
            "state": job.dag_state,
            "contract_status": job.contract_status
        }
    )
    db.add(event)
    db.commit()
    
    return {
        "status": "approved" if request.approved else "rejected",
        "job_id": job_id,
        "contract_version": job.contract_version,
        "dag_state": job.dag_state
    }


# ============== Helper Functions ==============

def _calculate_progress(job: Job) -> int:
    """Calculate overall progress percentage."""
    if not job.contract_progress:
        return 0
    
    total_percent = 0
    count = 0
    
    for key, progress in job.contract_progress.items():
        if "percent" in progress:
            total_percent += progress["percent"]
            count += 1
    
    return int(total_percent / count) if count > 0 else 0


async def _resume_build_async(job_id: str):
    """Background task to resume build."""
    # This would integrate with your DAG execution engine
    pass


async def _retry_nodes_async(job_id: str, node_ids: List[str]):
    """Background task to retry failed nodes."""
    # This would integrate with your DAG execution engine
    pass

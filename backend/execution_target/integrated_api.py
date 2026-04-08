"""
Integrated Execution Target API
Combines detection, dynamic execution, and learning
"""

from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel
import logging

from backend.execution_target.intent_analyzer import IntentAnalyzer
from backend.execution_target.dynamic_executor import DynamicExecutor, ExecutionMode
from backend.execution_target.target_learning import TargetLearningSystem
from backend.execution_target.learning_analytics import LearningAnalytics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/execution-target", tags=["execution-target"])

# Singleton instances
analyzer = IntentAnalyzer()
executor = DynamicExecutor()
learning = TargetLearningSystem()
analytics = LearningAnalytics(learning)

class JobExecutionRequest(BaseModel):
    """Request to execute a job with target detection"""
    job_id: str
    user_request: str
    allow_target_switching: bool = True

class TargetSwitchRequest(BaseModel):
    """Request to switch execution target mid-stream"""
    job_id: str
    new_target: str

@router.post("/execute-job")
async def execute_job_with_targets(request: JobExecutionRequest):
    """
    Execute a job with intelligent target selection
    
    1. Detects optimal targets
    2. Executes with dynamic executor
    3. Tracks choices for learning
    """
    
    try:
        # Step 1: Detect targets
        detection = analyzer.analyze(request.user_request)
        primary = detection["primary_target"]
        secondary = detection["secondary_targets"]
        confidence = detection["confidence"]
        
        logger.info(f"[{request.job_id}] Detected: {primary} (confidence: {confidence})")
        
        # Step 2: Execute with dynamic executor
        result = await executor.execute_targets(
            job_id=request.job_id,
            primary_target=primary,
            secondary_targets=secondary,
            mode=ExecutionMode.PARALLEL,
            allow_switching=request.allow_target_switching
        )
        
        # Step 3: Record learning (for future improvements)
        learning.record_choice(
            job_id=request.job_id,
            user_request=request.user_request,
            suggested_target=primary,
            user_choice=primary,
            suggested_confidence=confidence,
            outcome="success" if result["success"] else "failure"
        )
        
        return {
            "job_id": request.job_id,
            "detection": detection,
            "execution_result": result,
            "learning_recorded": True
        }
        
    except Exception as e:
        logger.error(f"Error executing job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/switch-target")
async def switch_target(request: TargetSwitchRequest):
    """
    Switch execution target mid-stream
    """
    
    try:
        success = await executor.switch_target(request.job_id, request.new_target)
        
        if not success:
            raise HTTPException(status_code=400, detail="Cannot switch target")
        
        return {
            "job_id": request.job_id,
            "new_target": request.new_target,
            "switched": True
        }
        
    except Exception as e:
        logger.error(f"Error switching target: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/job/{job_id}/status")
async def get_job_status(job_id: str):
    """Get current execution status"""
    
    status = executor.get_execution_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"job_id": job_id, "status": status}

@router.get("/job/{job_id}/result")
async def get_job_result(job_id: str):
    """Get execution result after completion"""
    
    result = executor.get_execution_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job result not found")
    
    return result

@router.get("/learning/stats")
async def get_learning_stats():
    """Get system learning statistics"""
    
    return {
        "learning_stats": learning.get_learning_stats(),
        "pattern_analysis": analytics.analyze_patterns()
    }


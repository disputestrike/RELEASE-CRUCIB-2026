"""
Fix for auto_runner.py data type issue
Converts Python list to JSON string before database insertion
"""

import json
from typing import List, Dict, Any

def serialize_blocked_steps(blocked_steps: List[str]) -> str:
    """
    Convert list of blocked step names to JSON string for database storage.
    
    Args:
        blocked_steps: List of step names that are blocked
        
    Returns:
        JSON string representation of the list
    """
    try:
        return json.dumps(blocked_steps) if blocked_steps else "[]"
    except Exception as e:
        print(f"Error serializing blocked steps: {str(e)}")
        return "[]"

def prepare_job_failure_state(job_id: str, blocked_steps: List[str], error_msg: str) -> Dict[str, Any]:
    """
    Prepare job failure state with properly serialized fields.
    
    Args:
        job_id: ID of the job
        blocked_steps: List of blocked steps
        error_msg: Error message
        
    Returns:
        Dictionary ready for database update
    """
    blocked_steps_json = serialize_blocked_steps(blocked_steps)
    
    return {
        "status": "failed",
        "blocked_steps": blocked_steps_json,
        "failure_reason": f"{error_msg} | Blocked: {blocked_steps_json}"
    }

# PATCH APPLICATION INSTRUCTIONS
# ================================
# 
# In backend/orchestration/auto_runner.py, line ~300:
# 
# CHANGE FROM:
# ```python
# blocked_steps = [step for step in dag_steps if step in blocked_from_deps]
# await update_job_state(job_id, "failed", {...})
# ```
#
# CHANGE TO:
# ```python
# from backend.orchestration.auto_runner_fix import prepare_job_failure_state
#
# blocked_steps = [step for step in dag_steps if step in blocked_from_deps]
# failure_state = prepare_job_failure_state(
#     job_id, 
#     blocked_steps,
#     f"Steps blocked by failed dependencies"
# )
# await update_job_state(job_id, failure_state["status"], failure_state)
# ```


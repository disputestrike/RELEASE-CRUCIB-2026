# Fix: Data Type Mismatch in auto_runner.py

## Problem
Line 300 in auto_runner.py is passing a Python list to a database string field:
```python
blocked_steps = ['deploy.build', 'deploy.publish']  # This is a list
await update_job_state(job_id, "failed", {"blocked_steps": blocked_steps})  # Expects string
```

## Solution
Convert list to JSON string before database insert:

```python
import json

# Around line 300, change from:
blocked_steps = [step for step in dag_steps if step in blocked_from_deps]
await update_job_state(job_id, "failed", {...})

# To:
blocked_steps = [step for step in dag_steps if step in blocked_from_deps]
blocked_steps_json = json.dumps(blocked_steps) if blocked_steps else "[]"

await update_job_state(job_id, "failed", {
    "blocked_steps": blocked_steps_json,
    "failure_reason": f"Steps blocked by failed dependencies: {blocked_steps_json}"
})
```

## Files to Update
- backend/orchestration/auto_runner.py (line ~300)
- backend/orchestration/runtime_state.py (add JSON serialization in update_job_state)

## Testing
After fix:
1. Run a test job
2. Check that blocked_steps are stored as JSON strings
3. Verify failure_reason is populated correctly
4. Monitor logs for this error


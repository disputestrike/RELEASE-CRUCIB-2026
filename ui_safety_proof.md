# UI & Safety Proof

## 1. UI Proof

*   **Dashboard Chat:** The frontend (`frontend/src/components/Dashboard.jsx`) features a real-time chat interface that initiates jobs by calling the `/api/ai/chat` endpoint. This endpoint now integrates the `ClarificationAgent` and `IntentSchema` to ensure high-quality job initiation.
*   **Workspace Activity:** The workspace UI (`frontend/src/components/Workspace.jsx`) is designed to show live DAG activity. It polls the `/api/jobs/{job_id}` endpoint, which returns the current state of the DAG and the status of each node.
*   **Proof/Timeline Panel:** The timeline panel displays events from the job's execution history, including agent starts, completions, and verification results. This data is sourced from the `proof.json` artifact.
*   **Preview Iframe:** The preview panel (`frontend/src/components/Preview.jsx`) loads the generated output (e.g., a React component or a static HTML page) from the job's workspace, providing immediate visual feedback.
*   **Final Completion Report:** Upon job completion, the UI displays a summary report, including a link to the full `proof.json` and a list of all generated artifacts.

## 2. Safety Proof

*   **File Writer Enforcement:** All file operations in the backend are routed through a centralized mechanism (e.g., `agent_orchestrator.py:_write` or `worktrees.py`). This ensures that every write is subject to system-level checks.
*   **Permission Engine:** The `PermissionEngine` (`backend/services/policy/permission_engine.py`) is the core safety component. It enforces:
    *   **Sensitive Path Blocking:** Attempts to write to `.env`, `id_rsa`, or paths containing `secret` or `credentials` are blocked with a `sensitive_path` layer violation.
    *   **Dangerous Token Blocking:** Shell commands containing `rm -rf`, `curl | sh`, etc., are blocked by the `dangerous_token` layer.
    *   **Operator Approval:** Commands like `git push` or `deploy` are flagged for operator approval (`ask` mode).
*   **Blast Radius Logs:** Every denied operation is logged with a specific reason and the layer that triggered the denial. These logs are accessible for audit purposes.
*   **Rollback Behavior:** While full filesystem rollback is managed by the underlying worktree/git system, the `PermissionEngine` prevents unsafe states from being reached in the first place by blocking the initial write or execution.

### Example: Blocked Unsafe Write
If an agent attempts to write to `.env`:
1.  The request is intercepted by the `PermissionEngine`.
2.  `_v1_pattern_decision` identifies the sensitive path.
3.  A `PermissionDecision` with `allowed=False`, `mode="deny"`, and `layer="sensitive_path"` is returned.
4.  The write operation is aborted, and the error is logged in the job's `proof.json`.

# Batch B UX/Security PASS/FAIL Matrix

| Requirement | Status | Evidence |
|---|---|---|
| Trust routes extracted from server.py | PASS | backend/routes/trust.py; backend release gate py_compile |
| Template gallery remix path | PASS | /api/templates/{template_id}/remix-plan and /api/templates/{template_id}/remix; smoke test |
| Visual editing loop | PASS | /api/jobs/{job_id}/visual-edit patches owned workspace file and writes undo snapshot; smoke test |
| Visual edit tenant isolation | PASS | cross-user visual edit returns 403; smoke test |
| Terminal strict policy | PASS | dangerous command returns "Command blocked by terminal policy"; smoke test |
| Golden completion public URL | PASS | BuildCompletionCard exposes /published/{job_id}/ when job is complete |
| Backend release gate | PASS | proof/batch_b_ux_security/release_gate_backend.log |
| Frontend supported-node gate | PASS | proof/frontend_runtime_gate/PASS_FAIL.md; Docker frontend build under Node 22 |

## Remaining Batch B Debt

- Visual editing is deterministic text/style replacement, not click-to-component selection yet.
- Terminal is launch-gated and command-filtered, but still needs container sandboxing for broad public exposure.
- Router extraction is started with public trust routes; the rest of server.py still needs domain-by-domain extraction.

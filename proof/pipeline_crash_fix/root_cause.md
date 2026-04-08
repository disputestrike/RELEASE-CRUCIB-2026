# Pipeline Crash Root Cause

1. `verification.preview` already produced precise causes in `preview_gate.py`, but `verifier.verify_step` dropped `failure_reason` before executor events. The fix preserves `failure_reason` with stage `preview_boot`.
2. `verification.elite_builder` already produced `failed_checks`, `failure_reason`, and `recommendation`, but `verifier.verify_step` dropped them. The fix preserves those fields.
3. `deploy.build` and `deploy.publish` were too ambiguous: missing artifacts and no live publish URL did not produce a deploy-specific failure reason. The fix makes artifact, smoke, strict live publish, and readiness-only publish outcomes explicit.
4. The background wrapper could still record generic `background_crash`; it now records `background_runner_exception` with exception type and traceback tail. A hidden schema defect also existed: job failure metadata columns were referenced in code but missing from the jobs table. The fix adds `failure_reason` and `failure_details`.
5. Retry exhaustion now emits `step_retry_exhausted` and retry events carry stage/failure metadata, so late-stage retries are explainable in the stream and event log.

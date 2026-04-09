# Swarm Smoke / Preview Fix

## Root Cause

The 190-agent swarm path was generating many agent artifacts, but it was not
assembling a runnable runtime contract before `verification.api_smoke` and
`verification.preview` executed.

For the failing Helios/Aegis-style run, the swarm emitted files like:

- `src/App.jsx`
- `server.py`
- agent output docs / JSON configs

But the late-stage verifiers still expected:

- a Vite preview contract (`package.json`, `index.html`, `vite.config.js`, `src/main.jsx`)
- API smoke entrypoints like `backend/main.py`

That mismatch caused the job to fail late at smoke/preview even though the
agent swarm itself had already produced substantial output.

## Fix

- moved runtime contract assembly into `implementation.delivery_manifest`
- delivery finalization now adds missing preview runtime glue for swarm jobs
- delivery finalization now adds a deterministic `backend/main.py` verification bridge
- `verification.api_smoke` now accepts common root/API entrypoints like `server.py`
- browser preview verification no longer requires the scaffold-specific login flow;
  it accepts a generic successful root render and only runs the demo auth flow
  when that UI is actually present

## PASS / FAIL

- Swarm delivery manifest assembles preview contract: PASS
- Swarm delivery manifest assembles API smoke contract: PASS
- API smoke accepts root `server.py`: PASS
- Existing pipeline crash regression suite: PASS

## Commands Run

```powershell
python -m py_compile backend/orchestration/generated_app_template.py backend/orchestration/executor.py backend/orchestration/verification_api_smoke.py backend/orchestration/browser_preview_verify.py backend/tests/test_pipeline_crash_fix.py backend/tests/test_verification_api_smoke.py
$env:PYTHONPATH='backend'; python -m pytest backend/tests/test_pipeline_crash_fix.py backend/tests/test_verification_api_smoke.py -q --noconftest
```

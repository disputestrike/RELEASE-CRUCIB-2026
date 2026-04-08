# Live production golden path root cause and fix

Generated: 2026-04-08T12:05:01Z

## Root causes found from live replay

1. Railway Auto-Runner runtime health checked `http://127.0.0.1:8000/api/health` even when Railway assigned another `$PORT`.
2. `FrontendAgent` could return an empty `files` object without falling back to the deterministic Vite preview scaffold.
3. The deterministic scaffold did not materialize enough elite gate proof by itself.
4. Final job failure metadata wrote Python lists/dicts directly to Postgres `TEXT` columns, causing asyncpg `DataError`.
5. Production `NODE_ENV=production` caused `npm install` to omit devDependencies, so `vite` was not installed.
6. The Railway image had the Playwright Python package, but not the Chromium browser binary required for live preview verification.

## Fixes applied

1. Runtime health now uses `CRUCIBAI_HEALTHCHECK_URL` when set, then Railway `$PORT`, then local port `8000`.
2. Empty frontend agent output now writes the deterministic preview scaffold.
3. The scaffold includes `ErrorBoundary`; delivery manifest writes `proof/ELITE_EXECUTION_DIRECTIVE.md`; backend sketches get security header proof hooks.
4. Structured job metadata fields are JSON-encoded before Postgres text binding.
5. Browser preview verification runs `npm install --include=dev --no-fund --no-audit`.
6. Docker production image runs `python -m playwright install --with-deps chromium`; preflight now reports `playwright_chromium` separately.

## Final live result

The final live production replay passed:

- Railway health: PASS
- LLM readiness: PASS
- Live LLM invocation: PASS
- Plan creation: PASS
- Auto-Runner start: PASS
- Preview boot: PASS
- Elite/proof verification: PASS
- Deploy build: PASS
- Deploy publish readiness: PASS
- Background runner stability: PASS

See `PASS_FAIL.md` and `final_summary.json` in this directory.

## Commands run

```powershell
python -m py_compile backend\orchestration\runtime_health.py scripts\live-production-golden-path.py
$env:DATABASE_URL='postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai'; $env:REDIS_URL='redis://127.0.0.1:6381/0'; python -m pytest backend\tests\test_runtime_health.py -q
python scripts\live-production-golden-path.py --base-url https://crucibai-production.up.railway.app --timeout-sec 900 --poll-sec 8
python -m py_compile backend\orchestration\runtime_state.py backend\orchestration\executor.py backend\orchestration\generated_app_template.py backend\orchestration\runtime_health.py scripts\live-production-golden-path.py
$env:DATABASE_URL='postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai'; $env:REDIS_URL='redis://127.0.0.1:6381/0'; python -m pytest backend\tests\test_runtime_health.py backend\tests\test_pipeline_crash_fix.py -q
python -m py_compile backend\orchestration\browser_preview_verify.py backend\orchestration\preflight_report.py backend\orchestration\runtime_health.py
$env:DATABASE_URL='postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai'; $env:REDIS_URL='redis://127.0.0.1:6381/0'; python -m pytest backend\tests\test_pipeline_crash_fix.py backend\tests\test_runtime_health.py -q
python scripts\live-production-golden-path.py --base-url https://crucibai-production.up.railway.app --timeout-sec 1200 --poll-sec 8
$env:DATABASE_URL='postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai'; $env:REDIS_URL='redis://127.0.0.1:6381/0'; .\scripts\release-gate.ps1 -BackendOnly
```

# Railway release checklist

Use after merging to `main` and deploying (Railway auto-deploy or manual).

## Automated smoke

From repo root (Python 3):

```bash
python scripts/railway_release_smoke.py --app-url https://YOUR_BACKEND.up.railway.app
```

Or set `APP_URL` and run without arguments.

**Pass criteria:** HTTP 2xx on `/api/health` and `/api/doctor/routes`.

## Build you must earn (release acceptance)

1. **Deploy truth** — Railway build shows the intended commit SHA; service env vars match production intent (including `ANTHROPIC_API_KEY` if you rely on the workspace tool loop).
2. **Smoke script** — `railway_release_smoke.py` exits 0 for your live URL.
3. **Tool loop proof** — One swarm step with a real `workspace_path` completes and the agent result includes `tool_loop: true` (and ideally `anthropic_usage` with `input_tokens` / `output_tokens`).
4. **Product path** — At least one full user-visible build or agent run finishes or fails with an actionable error (no silent hang).

## Optional Anthropic knobs

- **`CRUCIBAI_ANTHROPIC_EXTENDED_THINKING=1`** — extended thinking on turn 1 for high-stakes agents (Planner, Architect, …). Requires model/API support; leave unset if you see 400s.
- **`CRUCIBAI_ANTHROPIC_BETA_HEADERS`** — comma-separated beta flags only if Anthropic docs require them for your model (e.g. interleaved thinking experiments).

## Related scripts

- `scripts/prove_deployment_readiness.py` — artifact + optional deeper live probes (Braintree status, etc.).

# Railway Deployment Guide for CrucibAI

CrucibAI is PostgreSQL-only. Do not configure MongoDB for the current app.

## Required Railway Services

- Backend service built from the root `Dockerfile`.
- Railway Postgres plugin or external PostgreSQL instance.
- Optional Redis service for queue/cache acceleration.

## Required Variables

Set these in Railway service Variables:

| Variable | Required | Notes |
| --- | --- | --- |
| `DATABASE_URL` | Yes | Railway Postgres usually injects this automatically. |
| `JWT_SECRET` | Yes | Use a long random value, for example `openssl rand -hex 32`. |
| `REDIS_URL` | Recommended | Required for best queue/cache behavior. PostgreSQL fallback exists. |
| `FRONTEND_URL` | Recommended | Public frontend URL for redirects and CORS. |
| `CORS_ORIGINS` | Recommended | Comma-separated production origins. Do not use `*` for launch. |
| `ANTHROPIC_API_KEY` | Recommended | Primary AI build/chat provider. |
| `CEREBRAS_API_KEY` | Optional | Fast fallback/provider routing where prompt size allows. |
| `CRUCIBAI_TERMINAL_ENABLED` | Optional | Keep unset or `0` for public launch. Set `1` only for trusted sandboxed environments. |

## Deploy Steps

1. Connect `disputestrike/CrucibAI` to Railway.
2. Select the root `Dockerfile` builder.
3. Add the Postgres plugin and confirm `DATABASE_URL` is present.
4. Add `JWT_SECRET` and the optional variables above.
5. Deploy from `main`.
6. Check `/api/health/ready`; it should return healthy when Postgres is reachable.

## Troubleshooting

- 502 at startup usually means `DATABASE_URL` or `JWT_SECRET` is missing or invalid.
- If build/chat works slowly without Redis, add Redis and set `REDIS_URL`.
- If terminal routes return 403, that is expected in production unless `CRUCIBAI_TERMINAL_ENABLED=1`.
- If frontend build fails locally, check Node. The frontend supports Node `>=18 <=22`.

## Verification

Run these before launch:

```powershell
.\scripts\verify-local.ps1
$env:DATABASE_URL='postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai'
$env:REDIS_URL='redis://127.0.0.1:6381/0'
python -m pytest backend\tests\test_smoke.py -q
```

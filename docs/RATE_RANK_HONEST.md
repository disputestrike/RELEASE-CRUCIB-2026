# CrucibAI - Honest Rate, Rank, And Compare

Last updated: 2026-05-03

## Basis

This document rates the current CrucibAI release from evidence that is present in code, tests, and Railway-facing readiness paths. Public marketing claims are governed by `docs/MARKETING_CLAIMS_EVIDENCE.md`.

## Evidence

| Dimension | Evidence |
| --- | --- |
| Orchestration | Agent DAG, runtime routes, job routes, workspace routes, and route doctor. |
| Repeatability | `benchmarks/repeatability_prompts_v1.json` plus `backend/tests/test_repeatability_benchmark.py`. |
| Quality visibility | Proof, preview, truth-score, build-integrity, and trust routes. |
| Payments | PayPal billing route and PayPal billing tests. |
| Cost governance | `/api/cost/governance` and cost tracker services. |
| Railway deployment | `railway.json`, `Dockerfile`, and `scripts/railway_release_smoke.py`. |
| Public trust | `/api/trust/enterprise-readiness`, `/api/trust/public-proof-readiness`, `/api/trust/summary`. |

## Internal Rating

| Dimension | Score | Note |
| --- | ---: | --- |
| Orchestration | 9.5 | Strong multi-agent and routing foundation. |
| Speed | 9.0 | Speed tiers and router policy exist; live production timing should continue to be measured. |
| Quality visibility | 9.5 | Proof, preview, and readiness gates are visible to the product. |
| Error recovery | 9.0 | Fallback and repair systems exist on critical paths. |
| Real-time progress | 8.5 | SSE and job/event APIs are present. |
| Cost control | 9.0 | Cost governance and budgets are exposed. |
| Pricing and billing | 9.0 | PayPal is the active billing provider. |
| Full-app output | 9.0 | Full app, preview, export, and deploy paths exist. |
| Security and auth | 9.0 | Auth, ownership, terminal, and project boundaries are covered by targeted tests. |
| Observability | 9.0 | Health, metrics, doctor, and trust surfaces exist. |

Internal average: about **9.1/10**.

## Public Ranking Rule

CrucibAI can publicly say it is **top-tier and proof-gated** today.

CrucibAI should not publicly say **"#1"**, **"Number 1"**, **"better than all"**, or **"99.2 percent guaranteed success"** unless the current release passes the certification gate with timestamped competitor artifacts:

```powershell
python scripts/number1_certification_gate.py
```

## Current Public Position

Approved wording:

> CrucibAI is a top-tier AI product-building platform that turns ideas and imported code into apps, automations, previews, proof, and deployment paths, with Railway deployment, PayPal billing, and public trust endpoints.

Held wording:

> CrucibAI is the Number 1 AI coding platform with guaranteed 99.2 percent success.

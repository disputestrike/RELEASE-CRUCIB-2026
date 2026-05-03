# CrucibAI Marketing Claims Evidence Contract

Last updated: 2026-05-03

## Rule

CrucibAI public claims must be backed by one of these evidence types:

- A live Railway endpoint.
- A checked-in benchmark suite or release test.
- A signed proof manifest route.
- A reproducible smoke script.
- A customer-visible product route.

Do not publish unconditional claims such as "guaranteed outcome", "99.2% success", "Number 1", or "better than all" unless the current release has a timestamped proof bundle for that exact claim.

## Approved Claims

| Claim | Approved wording | Evidence |
| --- | --- | --- |
| Product category | "CrucibAI turns an idea or imported code into apps, automations, previews, proof, and deployment paths." | `/api/doctor/routes`, `/api/settings/capabilities`, workspace/job routes |
| Railway deployment | "Railway is the production deployment target." | `railway.json`, `Dockerfile`, `scripts/railway_release_smoke.py` |
| Repeatability | "The release benchmark covers 50 build categories with a 90 percent pass-rate gate." | `benchmarks/repeatability_prompts_v1.json`, `backend/tests/test_repeatability_benchmark.py`, `/api/trust/benchmark-summary` |
| Payments | "PayPal is the active billing provider." | `/api/billing/config`, `backend/routes/paypal_payments.py`, PayPal tests |
| Cost governance | "CrucibAI exposes plan pricing, action budgets, and cost-governance policy." | `/api/cost/governance` |
| Enterprise readiness | "CrucibAI exposes enterprise readiness, security posture, signed proof verification, and route-level trust APIs." | `/api/trust/enterprise-readiness`, `/api/trust/security-posture`, `/api/trust/proof-manifest/verify` |
| Competitive position | "CrucibAI is designed to compete as a top-tier AI product-building platform." | `docs/NUMBER1_CERTIFICATION_GATE.md`, product dominance benchmark suite |

## Claims That Need Gate Approval

| Claim | Status | Gate required |
| --- | --- | --- |
| "Number 1" / "#1" | Hold for public marketing | `python scripts/number1_certification_gate.py` with current competitor artifacts |
| "99.2% success" | Hold for public marketing | Current release proof that produces that percentage from real runs |
| "Guaranteed outcome" | Hold for public marketing | Legal/refund policy plus billing enforcement |
| "Defense-grade" | Hold for public marketing | Security review, compliance scope, and enterprise deployment package |
| "Production ready" | Allowed only with context | Railway smoke, route doctor, frontend build, backend release tests |

## Current Public Positioning

Use this:

> CrucibAI is a Railway-deployed AI product-building platform for apps, automations, previews, proof, and deployable outputs. It is built around measurable release gates, PayPal billing, cost governance, and public trust endpoints.

Avoid this until the exact proof exists:

> CrucibAI is guaranteed to be Number 1 with 99.2 percent success.

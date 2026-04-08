# Full Systems Testing

CrucibAI's broad pre-release gate is:

```powershell
.\scripts\full-systems-test.ps1
```

The gate writes proof under `proof/full_systems/` and fails on any required gate failure.

## Required Gates

- Git diff whitespace check
- Backend syntax compile for critical backend and proof scripts
- Full backend pytest suite
- Backend release gate
- Golden-path UX source audit that checks onboarding, beta gating, visual edit, terminal audit, public template/community trust, and public status/trust wiring
- Frontend runtime gate using the supported Node 22 Docker path
- Railway static readiness, full Docker build, local container health, and live `/api/health`
- Fortune 100 public trust preflight against production-facing health, trust, benchmark, status, security, curated template/community, and moderation surfaces
- Live production golden path against Railway:
  - health
  - LLM readiness
  - live LLM invocation
  - orchestrator plan
  - run-auto execution
  - preview verification
  - elite/proof verification
  - deploy build
  - deploy publish
  - public generated-app URL

## Useful Flags

Use these only when intentionally narrowing the gate during local diagnosis:

```powershell
.\scripts\full-systems-test.ps1 -SkipDocker
.\scripts\full-systems-test.ps1 -SkipLive
.\scripts\full-systems-test.ps1 -SkipFrontendDocker
.\scripts\full-systems-test.ps1 -SkipRailwayContainerHealth
```

The default command is the release-candidate path. A green default run means the repo has local full-suite proof, Docker/Node 22 proof, Railway readiness proof, and live production golden-path proof.

# CrucibAI Repeatability Benchmark

This benchmark is the first measurable gate for moving CrucibAI toward a 10/10
core pipeline score.

## What it proves

The benchmark runs ten app categories through the deterministic golden-path
fallback:

- generated files
- prompt term coverage
- preview gate
- elite proof gate
- deploy build readiness
- deploy publish readiness

It writes proof under:

`proof/benchmarks/repeatability_v1/`

## What it does not prove

The default benchmark does not spend live LLM credits and does not run a full
browser preview. It sets `CRUCIBAI_SKIP_BROWSER_PREVIEW=1` so the release gate
stays fast and reproducible on machines without a supported Node runtime.

For live production proof, use:

```powershell
python scripts\live-production-golden-path.py --base-url https://crucibai-production.up.railway.app --timeout-sec 1200 --poll-sec 8
```

For heavier browser validation, use:

```powershell
python scripts\run-repeatability-benchmark.py --run-browser-preview
```

## Current 25-prompt suite

The suite is stored in:

`benchmarks/repeatability_prompts_v1.json`

It covers:

- SaaS dashboard
- service marketplace
- booking workflow
- CRM pipeline
- AI chat workspace
- ecommerce storefront
- workflow automation hub
- bring-your-code repair
- internal operations tool
- conversion landing page

## Release gate

`scripts/release-gate.ps1 -BackendOnly` now runs:

```powershell
python -m pytest backend\tests\test_repeatability_benchmark.py -q
python scripts\run-repeatability-benchmark.py
```

The current hard gate is:

- pass rate >= 90%
- average score >= 90

## Expansion path

The next iteration should grow the suite from 25 to 50 prompts. Once the suite
is stable, add a scheduled live run that samples prompts against Railway and
stores production results in a separate proof folder so release gates do not
depend on live LLM/provider availability.

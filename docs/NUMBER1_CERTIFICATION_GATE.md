# Number 1 Certification Gate

Date: 2026-04-15
Owner: Engineering

## Purpose

Define an objective, repeatable gate for claiming "Number 1" status.

A claim is allowed only when all required gate categories pass.

## Gate Categories

1. Internal Engineering Integrity (required)
- Runtime/worktree/simulation/eventing route tests pass.
- Core observability hooks are present and tested.
- Completion audit document exists and is current.

2. Reliability and Repeatability (required)
- Repeatability benchmark meets release threshold.
- No failing critical backend tests in the active release suite.

3. Production Evidence (required)
- Live production golden-path proof exists and is recent.
- End-to-end proof pack generated from current release commit.

4. Competitive Evidence (required for public "Number 1" claim)
- Side-by-side benchmark against named competitors.
- Same prompt set, same scoring rubric, same constraints.
- Publicly reviewable methodology and timestamped outputs.

## Minimum Pass Rule

All four categories must pass to assert:

- "We are Number 1"
- "Better than all"

If category 4 is missing, the strongest valid statement is:

- "Top-tier and improving, but Number 1 not yet externally proven"

## Automation

Run:

```powershell
python scripts/number1_certification_gate.py
```

The gate now auto-runs competitor artifact generation from:

- `proof/benchmarks/repeatability_v1/summary.json`
- `proof/benchmarks/competitor_runs/*.json`

You can run the builder directly:

```powershell
python scripts/build_competitor_comparison.py
```

Outputs:
- `proof/benchmarks/number1_gate_latest.json`
- `proof/benchmarks/NUMBER1_GATE_SCORECARD.md`

## Current Status (from latest automated run)

See `proof/benchmarks/NUMBER1_GATE_SCORECARD.md`.

# Competitor Benchmark Methodology

Date: 2026-04-15
Owner: Engineering

## Objective

Measure CrucibAI against named competitors with the same prompt suite, scoring rubric, and run constraints.

## Competitors

- Claude
- OpenAI ChatGPT
- Gemini
- Cursor-style coding workflow baseline

## Prompt Suite

- Source: benchmarks/repeatability_prompts_v1.json
- Count: 50 prompts
- Categories: SaaS, marketplace, booking, CRM, AI chat, ecommerce, automation, code repair, ops tooling, landing page.

## Scoring Dimensions

1. Build completion
2. Functional correctness
3. Security posture
4. Deployment readiness
5. UX quality
6. Latency
7. Cost efficiency

## Execution Controls

- Same prompt text for all systems.
- Same timeout window per prompt.
- Same hardware/network region when possible.
- Logged raw outputs and timestamps.

## Evidence Format

- JSON artifact: proof/benchmarks/competitor_comparison_latest.json
- Required fields:
  - generated_at_utc
  - suite_name
  - systems
  - comparisons
  - winner
  - notes

## Claim Rule

Public "Number 1" claim requires:

- At least one completed competitor comparison run.
- Non-empty comparisons array.
- Clear winner field based on published rubric.

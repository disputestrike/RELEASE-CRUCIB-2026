# CrucibAI Proof Methodology

## Axes

| Axis | Description |
|---|---|
| `first_preview_target_seconds` | Time from prompt submission to first live preview URL (target ≤ 60 s) |
| `repeatability_pass_rate` | Fraction of 50 standard prompts that reproduce identically across 3 runs |
| `deploy_targets_supported` | List of deploy targets with documented, working deploy paths |
| `mobile_proof_run` | Whether a mobile proof-run (device viewport + touch test) is included |
| `migration_mode_supported` | Whether existing codebases can be imported and continued |
| `inspect_mode_supported` | Whether the platform exposes a live DOM/CSS inspect surface |
| `typed_tool_registry` | Whether the agent tool registry has typed schemas (vs. free-text dispatch) |

## How We Run

1. **Repeatability suite** — `scripts/run-repeatability-benchmark.py` executes 50 curated prompts with a fixed seed. Results land in `proof/benchmarks/repeatability_v1/summary.json`. The release gate requires pass_rate ≥ 0.90.
2. **Competitor snapshots** — `scripts/run_competitor_benchmarks.py --mode=seeded` writes a deterministic snapshot to `proof/benchmarks/competitors/{timestamp}.json`. Numbers reflect public marketing claims and are marked `source: seeded_public_marketing_claim`.
3. **Live snapshots** (future) — `--mode=live` with `COMPETITOR_CREDS=path/to/creds.yaml` will run authenticated flows. Until then, seeded data is the authoritative baseline.

## How to Reproduce

```bash
# 1. Clone the repo
git clone <repo-url> && cd CrucibAI

# 2. Run the repeatability benchmark
python scripts/run-repeatability-benchmark.py

# 3. Run the competitor snapshot
python scripts/run_competitor_benchmarks.py --mode=seeded

# 4. View results
cat proof/benchmarks/repeatability_v1/summary.json
ls  proof/benchmarks/competitors/
```

The scorecard is served publicly at `GET /public/benchmarks/scorecard` — no authentication required.

## Submitting a Correction

If a competitor cell is wrong, open a community correction via `POST /api/community/publish` with:

```json
{
  "title": "Correction: bolt deploy_targets_supported",
  "content": "Bolt now supports Cloudflare Pages (source: <URL>)",
  "tags": ["benchmark-correction", "bolt"]
}
```

The community publish loop requires `trust_score ≥ 0.7`. Accepted corrections are reviewed by the CrucibAI team and incorporated into the next seeded baseline.

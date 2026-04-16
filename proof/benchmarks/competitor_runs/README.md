# Competitor Runs Input

Drop normalized competitor benchmark summaries in this folder.

Required JSON shape (one file per system):

```json
{
  "system": "claude",
  "generated_at_utc": "2026-04-15T00:00:00+00:00",
  "suite_name": "repeatability_prompts_v1",
  "prompt_count": 50,
  "average_score": 92.4,
  "pass_rate": 0.94,
  "latency_p50_sec": 8.1,
  "cost_per_prompt_usd": 0.14,
  "notes": "optional"
}
```

Run builder:

```powershell
python scripts/build_competitor_comparison.py
```

Outputs:
- proof/benchmarks/competitor_comparison_latest.json
- proof/benchmarks/COMPETITOR_COMPARISON_SCORECARD.md

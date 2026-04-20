# Product Dominance - Public Proof Index

Generated: 2026-04-20T19:24:14.232608+00:00

This index catalogs benchmark runs and signed proof artifacts for external validation.

## Primary Proof Pack

- Canonical run: `live_full100_v2_pooled_signed` (live signed benchmark pack)
- Summary: `proof/benchmarks/product_dominance_v1/live_full100_v2_pooled_signed/summary.json`
- Report: `proof/benchmarks/product_dominance_v1/live_full100_v2_pooled_signed/BENCHMARK_REPORT.md`
- Manifest: `proof/benchmarks/product_dominance_v1/live_full100_v2_pooled_signed/proof_manifest.json`

## Verification Quickstart

1. Set the verification secret used during manifest signing:

```powershell
$env:CRUCIB_PROOF_HMAC_SECRET = 'local-proof-test-secret'
```

2. Verify manifest integrity:

```powershell
python -c \"import json, pathlib; from backend.services.proof_manifest import verify_manifest; p=pathlib.Path('proof/benchmarks/product_dominance_v1/live_full100_v2_pooled_signed/proof_manifest.json'); m=json.loads(p.read_text(encoding='utf-8')); print(verify_manifest(m, secret='local-proof-test-secret'))\"
```

## Run Catalog

| Run | Mode | Total Runs | Avg Score | Success Rate | Avg Time (s) | Provider Mode | Keys Exercised | Signed Manifest |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `live_full100_v2_pooled_signed` | live | 100 | 97.29 | 100.00% | 3.43 | pooled | 5 | yes |
| `live_full100_v1_pooled_signed` | live | 100 | 90.52 | 83.00% | 2.99 | pooled | 5 | yes |
| `signed_smoke` | simulated | 1 | 96.20 | 100.00% | 98.00 | single_key | 0 | yes |
| `live_full30_v3_pooled` | live | 30 | 93.97 | 100.00% | 6.73 | pooled | 5 | yes |
| `live_full30_v2` | live | 30 | 87.89 | 100.00% | 6.37 | - | - | no |
| `live_full30_v1` | live | 30 | 84.83 | 100.00% | 3.68 | - | - | no |
| `live_first10_v6b` | live | 10 | 85.00 | 100.00% | 3.17 | - | - | no |
| `live_first10_v6` | live | 10 | 85.00 | 100.00% | 3.17 | - | - | no |
| `live_first10_v5` | live | 10 | 69.00 | 100.00% | 3.17 | - | - | no |
| `live_first10_v4` | live | 10 | 26.70 | 0.00% | 1.58 | - | - | no |
| `live_first10_v3` | live | 10 | 36.10 | 0.00% | 0.03 | - | - | no |
| `live_first10_v2` | live | 10 | 67.13 | 70.00% | 0.08 | - | - | no |
| `live_first10` | live | 10 | 78.00 | 100.00% | 0.03 | - | - | no |
| `live_probe_1` | live | 1 | 78.00 | 100.00% | 0.04 | - | - | no |
| `smoke_first10` | simulated | 10 | 97.10 | 100.00% | 78.10 | - | - | no |

## Signed Manifests

- `live_full100_v2_pooled_signed`
  - manifest_id: `product-dominance-1776712933`
  - payload_sha256: `e1986cc8b8f4a746b7bf1849d4e5814a75a4c91e4a7107658194688419b75a0c`
- `live_full100_v1_pooled_signed`
  - manifest_id: `product-dominance-1776711434`
  - payload_sha256: `d727b17e1f7af8db4e26b9dae6bb2ac6425eb319504ab3966360d03821b413d1`
- `signed_smoke`
  - manifest_id: `product-dominance-1776710891`
  - payload_sha256: `c717980ddafefe69037f3500e54bcaa230ae87c67afc1fc583c19c0839513903`
- `live_full30_v3_pooled`
  - manifest_id: `live_full30_v3_pooled-1776710888`
  - payload_sha256: `7e843c3b3bcc3c2c99a31e5b0a2944f258fe552cb3a644cff92fc50a0b98969e`

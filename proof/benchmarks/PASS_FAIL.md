# Benchmark Gate — PASS/FAIL policy

## What counts as pass / fail
- **PASS**: every previously-passing case still passes on `main`.
- **FAIL (regression, blocks merge)**: any of
  - A case that was passing in `baseline.json` is now failing in `latest.json`.
  - A suite's `pass` count dropped vs baseline.
  - The top-level `fail_count` increased vs baseline.

The gate is implemented in `scripts/gate_benchmark.py` and invoked by
`.github/workflows/bench.yml` on every PR to `main` and every push to `main`.

## Anatomy of a suite
A suite is a subdirectory under `proof/benchmarks/`. It must contain *either*:
- `cases.json` — a JSON array of declarative cases, each with:
  - `id` — unique within the suite
  - `kind` — `"shell"` (run a command) or `"http"` (httpx request)
  - `kind=shell`:  `cmd` (list of argv), `expect_exit` (default 0), `timeout_s`
  - `kind=http`:   `url`, `method` (default GET), `expect_status` (default 200), `timeout_s`
- `run.py` — an executable that prints a single JSON line to stdout shaped as:
  ```json
  {"suite": "<name>", "pass": <int>, "fail": <int>,
   "cases": [{"id": "...", "pass": true, "detail": {}}, ...]}
  ```

## How to add a new case
1. Create the directory under `proof/benchmarks/<name>/`.
2. Drop in a `cases.json` or a `run.py`.
3. Run locally:
   ```
   python scripts/run_benchmarks.py --out /tmp/latest.json
   python scripts/gate_benchmark.py /tmp/latest.json proof/benchmarks/baseline.json
   ```
4. If the gate is green, PR. CI will re-run and (if green) merge.

## How to intentionally update the baseline
Baseline updates are deliberate: they happen when you want the new "pass set"
to become the floor.

1. Make your code changes that improve the benchmarks (more cases passing).
2. Open a PR with the label **`baseline-update`**.
3. CI will refresh `proof/benchmarks/baseline.json` from the latest run before
   the gate step, so the PR still merges green.
4. Commit the refreshed `baseline.json` as part of the PR.

Never update `baseline.json` to hide a regression. Every regression should be
either reverted, or fixed in the same PR.

## Where it runs
GitHub Actions workflow: `.github/workflows/bench.yml` — job `bench`.

#!/usr/bin/env python3
"""Generate a public-facing proof index for product dominance benchmark artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_ROOT = REPO_ROOT / "proof" / "benchmarks" / "product_dominance_v1"
OUTPUT_PATH = BENCH_ROOT / "PUBLIC_PROOF_INDEX.md"
JSON_OUTPUT_PATH = BENCH_ROOT / "PUBLIC_PROOF_INDEX.json"
LANDING_OUTPUT_PATH = BENCH_ROOT / "PUBLIC_PROOF_LANDING.html"


def _fmt_number(value: object, digits: int = 2) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return "-"


def _fmt_percent(value: object, digits: int = 2) -> str:
    if isinstance(value, (int, float)):
        return f"{value * 100:.{digits}f}%"
    return "-"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_rows() -> list[dict]:
    rows: list[dict] = []
    for child in sorted(BENCH_ROOT.iterdir()):
        if not child.is_dir():
            continue
        if child.name.endswith("-pytest_bench_run"):
            continue

        summary_path = child / "summary.json"
        if not summary_path.exists():
            continue

        summary = _load_json(summary_path)
        aggregate = summary.get("aggregate", {})
        provider_pool = aggregate.get("provider_pool", {})

        manifest_path = child / "proof_manifest.json"
        manifest_id = "-"
        payload_sha = "-"
        has_manifest = manifest_path.exists()
        if has_manifest:
            manifest = _load_json(manifest_path)
            manifest_id = str(manifest.get("manifest_id", "-"))
            payload_sha = str(manifest.get("payload_sha256", "-"))

        rows.append(
            {
                "run": child.name,
                "generated_at": str(summary.get("generated_at", "")),
                "mode": str(summary.get("mode", "-")),
                "total_runs": int(aggregate.get("total_runs", 0)),
                "avg_score": aggregate.get("average_score"),
                "success_rate": aggregate.get("success_rate"),
                "avg_time_s": aggregate.get("average_time_seconds"),
                "provider_mode": str(provider_pool.get("execution_mode", "-")),
                "keys_exercised": provider_pool.get("keys_exercised_count", "-"),
                "has_manifest": has_manifest,
                "manifest_id": manifest_id,
                "payload_sha": payload_sha,
            }
        )

    rows.sort(key=lambda r: r["generated_at"], reverse=True)
    return rows


def choose_canonical_run(rows: list[dict]) -> dict:
    for row in rows:
        if (
            row.get("mode") == "live"
            and bool(row.get("has_manifest"))
            and int(row.get("total_runs") or 0) >= 100
        ):
            return row
    for row in rows:
        if bool(row.get("has_manifest")):
            return row
    return rows[0] if rows else {}


def render_markdown(rows: list[dict]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    canonical = choose_canonical_run(rows)
    canonical_run = str(canonical.get("run") or "live_full100_v1_pooled_signed")
    lines: list[str] = []
    lines.append("# Product Dominance - Public Proof Index")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append("")
    lines.append("This index catalogs benchmark runs and signed proof artifacts for external validation.")
    lines.append("")
    lines.append("## Primary Proof Pack")
    lines.append("")
    lines.append(f"- Canonical run: `{canonical_run}` (live signed benchmark pack)")
    lines.append(f"- Summary: `proof/benchmarks/product_dominance_v1/{canonical_run}/summary.json`")
    lines.append(f"- Report: `proof/benchmarks/product_dominance_v1/{canonical_run}/BENCHMARK_REPORT.md`")
    lines.append(f"- Manifest: `proof/benchmarks/product_dominance_v1/{canonical_run}/proof_manifest.json`")
    lines.append("")
    lines.append("## Verification Quickstart")
    lines.append("")
    lines.append("1. Set the verification secret used during manifest signing:")
    lines.append("")
    lines.append("```powershell")
    lines.append("$env:CRUCIB_PROOF_HMAC_SECRET = 'local-proof-test-secret'")
    lines.append("```")
    lines.append("")
    lines.append("2. Verify manifest integrity:")
    lines.append("")
    lines.append("```powershell")
    lines.append(
        f"python -c \\\"import json, pathlib; from backend.services.proof_manifest import verify_manifest; p=pathlib.Path('proof/benchmarks/product_dominance_v1/{canonical_run}/proof_manifest.json'); m=json.loads(p.read_text(encoding='utf-8')); print(verify_manifest(m, secret='local-proof-test-secret'))\\\""
    )
    lines.append("```")
    lines.append("")
    lines.append("## Run Catalog")
    lines.append("")
    lines.append("| Run | Mode | Total Runs | Avg Score | Success Rate | Avg Time (s) | Provider Mode | Keys Exercised | Signed Manifest |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    for row in rows:
        lines.append(
            "| "
            + f"`{row['run']}`"
            + " | "
            + row["mode"]
            + " | "
            + str(row["total_runs"])
            + " | "
            + _fmt_number(row["avg_score"])
            + " | "
            + _fmt_percent(row["success_rate"])
            + " | "
            + _fmt_number(row["avg_time_s"])
            + " | "
            + row["provider_mode"]
            + " | "
            + str(row["keys_exercised"])
            + " | "
            + ("yes" if row["has_manifest"] else "no")
            + " |"
        )

    lines.append("")
    lines.append("## Signed Manifests")
    lines.append("")
    manifest_rows = [r for r in rows if r["has_manifest"]]
    if not manifest_rows:
        lines.append("No signed manifests found.")
    else:
        for row in manifest_rows:
            lines.append(f"- `{row['run']}`")
            lines.append(f"  - manifest_id: `{row['manifest_id']}`")
            lines.append(f"  - payload_sha256: `{row['payload_sha']}`")

    lines.append("")
    return "\n".join(lines)


def _summary_for_run(rows: list[dict], run_name: str) -> dict:
    for row in rows:
        if row.get("run") == run_name:
            return row
    return {}


def render_json_catalog(rows: list[dict]) -> dict:
    canonical = choose_canonical_run(rows)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "canonical_run": canonical,
        "runs": rows,
        "signed_runs": [row for row in rows if row.get("has_manifest")],
    }


def render_html_landing(rows: list[dict]) -> str:
    canonical = choose_canonical_run(rows)
    canonical_run = str(canonical.get("run") or "live_full100_v1_pooled_signed")
    avg_score = _fmt_number(canonical.get("avg_score"))
    success_rate = _fmt_percent(canonical.get("success_rate"))
    total_runs = canonical.get("total_runs") or "-"

    table_rows = []
    for row in rows:
        table_rows.append(
            "<tr>"
            f"<td>{row['run']}</td>"
            f"<td>{row['mode']}</td>"
            f"<td>{row['total_runs']}</td>"
            f"<td>{_fmt_number(row['avg_score'])}</td>"
            f"<td>{_fmt_percent(row['success_rate'])}</td>"
            f"<td>{_fmt_number(row['avg_time_s'])}</td>"
            f"<td>{row['provider_mode']}</td>"
            f"<td>{'yes' if row['has_manifest'] else 'no'}</td>"
            "</tr>"
        )

    html = """<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>CrucibAI Public Proof</title>
    <style>
        :root {
            --bg: #f4f1e8;
            --ink: #0f172a;
            --muted: #475569;
            --panel: #fffdf7;
            --line: #d6d3c7;
            --accent: #0f766e;
            --accent-soft: #d1fae5;
            --shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: 'Segoe UI', 'Trebuchet MS', system-ui, sans-serif;
            color: var(--ink);
            background: radial-gradient(circle at 20% -10%, #fff8db 0, transparent 45%), var(--bg);
        }
        .wrap { max-width: 1120px; margin: 0 auto; padding: 28px 18px 44px; }
        .hero {
            background: linear-gradient(125deg, #083344 0%, #115e59 60%, #134e4a 100%);
            color: #f8fafc;
            border-radius: 18px;
            padding: 26px;
            box-shadow: var(--shadow);
        }
        .hero h1 { margin: 0 0 8px; font-size: 2rem; letter-spacing: 0.2px; }
        .hero p { margin: 0; color: #ccfbf1; }
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-top: 16px;
        }
        .card {
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.24);
            border-radius: 12px;
            padding: 12px;
        }
        .card .k { font-size: 0.78rem; color: #ccfbf1; text-transform: uppercase; letter-spacing: 0.08em; }
        .card .v { font-size: 1.35rem; margin-top: 5px; font-weight: 700; }
        .panel {
            margin-top: 16px;
            background: var(--panel);
            border-radius: 14px;
            border: 1px solid var(--line);
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        .panel h2 {
            margin: 0;
            padding: 14px 16px;
            border-bottom: 1px solid var(--line);
            font-size: 1.04rem;
            background: #fffcf2;
        }
        .panel .body { padding: 14px 16px; }
        .quick {
            background: #062b2a;
            color: #e2e8f0;
            border-radius: 10px;
            padding: 10px;
            font-family: Consolas, 'Courier New', monospace;
            font-size: 0.84rem;
            overflow-x: auto;
        }
        table { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
        th, td { padding: 8px; border-bottom: 1px solid var(--line); text-align: left; }
        th { background: #f8f5eb; }
        tr:hover td { background: var(--accent-soft); }
        .foot { color: var(--muted); font-size: 0.84rem; margin-top: 14px; }
        a { color: var(--accent); }
    </style>
</head>
<body>
    <div class=\"wrap\">
        <section class=\"hero\">
            <h1>CrucibAI Public Proof Bundle</h1>
            <p>Signed benchmark evidence with reproducible verification instructions and complete run catalog.</p>
            <div class=\"cards\">
                <div class=\"card\"><div class=\"k\">Canonical Run</div><div class=\"v\">__RUN_NAME__</div></div>
                <div class=\"card\"><div class=\"k\">Total Runs</div><div class=\"v\">__TOTAL_RUNS__</div></div>
                <div class=\"card\"><div class=\"k\">Avg Score</div><div class=\"v\">__AVG_SCORE__</div></div>
                <div class=\"card\"><div class=\"k\">Success Rate</div><div class=\"v\">__SUCCESS_RATE__</div></div>
            </div>
        </section>

        <section class=\"panel\">
            <h2>Primary Artifacts</h2>
            <div class=\"body\">
                <ul>
                    <li><a href=\"__CANONICAL_RUN__/summary.json\">Canonical summary.json</a></li>
                    <li><a href=\"__CANONICAL_RUN__/BENCHMARK_REPORT.md\">Canonical BENCHMARK_REPORT.md</a></li>
                    <li><a href=\"__CANONICAL_RUN__/proof_manifest.json\">Canonical proof_manifest.json</a></li>
                    <li><a href=\"PUBLIC_PROOF_INDEX.md\">PUBLIC_PROOF_INDEX.md</a></li>
                    <li><a href=\"PUBLIC_PROOF_INDEX.json\">PUBLIC_PROOF_INDEX.json</a></li>
                </ul>
            </div>
        </section>

        <section class=\"panel\">
            <h2>Verification Quickstart</h2>
            <div class=\"body\">
                <div class=\"quick\">$env:CRUCIB_PROOF_HMAC_SECRET = 'local-proof-test-secret'</div>
                <div style=\"height:8px\"></div>
                <div class=\"quick\">python -c \"import json, pathlib; from backend.services.proof_manifest import verify_manifest; p=pathlib.Path('proof/benchmarks/product_dominance_v1/__CANONICAL_RUN__/proof_manifest.json'); m=json.loads(p.read_text(encoding='utf-8')); print(verify_manifest(m, secret='local-proof-test-secret'))\"</div>
            </div>
        </section>

        <section class=\"panel\">
            <h2>Run Catalog</h2>
            <div class=\"body\">
                <table>
                    <thead>
                        <tr><th>Run</th><th>Mode</th><th>Runs</th><th>Avg Score</th><th>Success Rate</th><th>Avg Time</th><th>Provider</th><th>Signed</th></tr>
                    </thead>
                    <tbody>
                        __TABLE_ROWS__
                    </tbody>
                </table>
            </div>
        </section>

        <p class=\"foot\">Generated __GENERATED_AT__</p>
    </div>
</body>
</html>
"""

    return (
        html.replace("__RUN_NAME__", canonical_run)
        .replace("__CANONICAL_RUN__", canonical_run)
        .replace("__TOTAL_RUNS__", str(total_runs))
        .replace("__AVG_SCORE__", str(avg_score))
        .replace("__SUCCESS_RATE__", str(success_rate))
        .replace("__TABLE_ROWS__", "\n            ".join(table_rows))
        .replace("__GENERATED_AT__", datetime.now(timezone.utc).isoformat())
    )


def main() -> int:
    if not BENCH_ROOT.exists():
        raise FileNotFoundError(f"Benchmark root not found: {BENCH_ROOT}")

    rows = collect_rows()
    md = render_markdown(rows)
    catalog = render_json_catalog(rows)
    html = render_html_landing(rows)
    OUTPUT_PATH.write_text(md, encoding="utf-8")
    JSON_OUTPUT_PATH.write_text(json.dumps(catalog, indent=2, sort_keys=True), encoding="utf-8")
    LANDING_OUTPUT_PATH.write_text(html, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "output": str(OUTPUT_PATH.relative_to(REPO_ROOT)).replace("\\\\", "/"),
                "json_output": str(JSON_OUTPUT_PATH.relative_to(REPO_ROOT)).replace("\\\\", "/"),
                "landing_output": str(LANDING_OUTPUT_PATH.relative_to(REPO_ROOT)).replace("\\\\", "/"),
                "runs_indexed": len(rows),
                "signed_manifests": sum(1 for r in rows if r["has_manifest"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

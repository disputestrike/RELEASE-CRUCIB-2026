#!/usr/bin/env python3
"""Exercise CrucibAI's cross-mode proof gates.

This script is intentionally local and deterministic. It proves that the
validator rejects thin/scaffold output and accepts complete artifacts across the
core public build modes: SaaS/web UI, marketing website, mobile Expo, automation,
and backend/API.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.orchestration.build_integrity_validator import validate_workspace_integrity
from backend.orchestration.generated_app_template import build_frontend_file_set
from backend.orchestration.targeted_dag_retry import build_targeted_retry_plan


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write(path, json.dumps(data, indent=2, sort_keys=True))


def make_base_web(root: Path, *, package_name: str = "crucibai-proof") -> None:
    write_json(
        root / "package.json",
        {
            "name": package_name,
            "private": True,
            "scripts": {"dev": "vite --host", "build": "vite build", "preview": "vite preview", "test": "vitest run"},
            "dependencies": {
                "react": "^19.0.0",
                "react-dom": "^19.0.0",
                "react-router-dom": "^7.0.0",
                "recharts": "^2.0.0",
                "lucide-react": "^0.400.0",
                "sonner": "^1.0.0",
            },
            "devDependencies": {"vite": "^7.0.0", "@vitejs/plugin-react": "^5.0.0"},
        },
    )
    write(root / "index.html", '<div id="root"></div>')
    write(root / "dist" / "index.html", '<html><body><div id="root"></div></body></html>')
    write(root / "Dockerfile", 'FROM node:22-alpine\nCMD ["npm", "run", "preview"]\n')
    write(root / "README.md", "How to run: npm install, npm run build, npm run preview. Deployment: Railway/Vercel.")
    write(
        root / "ideas.md",
        """
        Design option A: Obsidian Operations.
        Design option B: Arctic Clarity.
        Design option C: Product Theater.
        Chosen direction: Arctic Clarity because it supports trustworthy product surfaces.
        """,
    )
    write(
        root / "src" / "index.css",
        """:root{--primary:#4f46e5;--background:#f8fafc;--foreground:#111827;--chart-1:#4f46e5;--sidebar:#fff;--radius:8px}
        .buttonVariants{font-family:Inter,sans-serif}.card{border-radius:var(--radius)}
        """,
    )
    write(
        root / "src" / "main.jsx",
        "import React from 'react'; import { createRoot } from 'react-dom/client'; import App from './App.jsx'; import './index.css'; createRoot(document.getElementById('root')).render(<App />);",
    )


def make_saas(root: Path) -> None:
    make_base_web(root, package_name="crucibai-saas-proof")
    write(
        root / "src" / "App.jsx",
        """
        import { BrowserRouter, Routes, Route } from 'react-router-dom';
        import Home from './pages/Home.jsx';
        import Dashboard from './pages/Dashboard.jsx';
        import Analytics from './pages/Analytics.jsx';
        import Team from './pages/Team.jsx';
        import Pricing from './pages/Pricing.jsx';
        import Settings from './pages/Settings.jsx';
        export default function App(){return <BrowserRouter><Routes>
          <Route path="/" element={<Home/>}/><Route path="/dashboard" element={<Dashboard/>}/>
          <Route path="/analytics" element={<Analytics/>}/><Route path="/team" element={<Team/>}/>
          <Route path="/pricing" element={<Pricing/>}/><Route path="/settings" element={<Settings/>}/>
        </Routes></BrowserRouter>}
        """,
    )
    pages = {
        "Home": "hero feature feature cta testimonial stats product image <img src='/hero.png' alt='product' />",
        "Dashboard": "kpi kpi kpi chart Recharts AreaChart table activity customers",
        "Analytics": "chart funnel cohort top pages retention LineChart BarChart",
        "Team": "member avatar role invite search permissions",
        "Pricing": "pricing plans popular plan comparison faq billing",
        "Settings": "profile notifications security billing integrations preferences",
    }
    for page, body in pages.items():
        write(root / "src" / "pages" / f"{page}.jsx", f"export default function {page}(){{return <section>{body}</section>}}\n")


def make_site(root: Path) -> None:
    make_base_web(root, package_name="crucibai-site-proof")
    write(
        root / "src" / "App.jsx",
        """
        export default function App(){return <main>
          <nav>Navigation</nav>
          <section className="hero"><img src="/product.webp" alt="Product" /><h1>Launch website</h1><button>CTA</button></section>
          <section>feature feature feature</section>
          <section>testimonial pricing contact footer</section>
        </main>}
        """,
    )


def make_api(root: Path) -> None:
    write(root / "requirements.txt", "fastapi\nuvicorn\npydantic\npytest\n")
    write(
        root / "backend" / "main.py",
        """
        from fastapi import FastAPI, APIRouter, HTTPException
        app = FastAPI(openapi_url='/openapi.json')
        router = APIRouter()
        @app.get('/health')
        def health():
            return {'status':'ok'}
        @router.get('/items')
        def items():
            try:
                return []
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc))
        app.include_router(router, prefix='/api')
        """,
    )
    write(root / "Dockerfile", 'FROM python:3.11-slim\nCMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0"]\n')
    write(root / "README.md", "How to run: uvicorn backend.main:app. Deployment: Railway.")


def make_automation(root: Path) -> None:
    write_json(
        root / "package.json",
        {"scripts": {"build": "echo ok", "start": "node automation/executor.js", "test": "echo ok"}},
    )
    write(root / "Dockerfile", 'FROM node:22-alpine\nCMD ["npm", "start"]\n')
    write(
        root / "automation" / "workflow.json",
        json.dumps(
            {
                "trigger": {"type": "webhook"},
                "workflow": {"steps": [{"type": "run_agent", "agent": "builder"}]},
                "executor": "automation/executor.js",
            },
            indent=2,
        ),
    )
    write(root / "automation" / "executor.js", "export function run_agent(input){ return { ok: true, input }; }\n")
    write(root / "automation" / "README.md", "Workflow executor runtime with run_agent bridge, webhook trigger, budget, retry policy, and deployment notes.")


def make_mobile(root: Path) -> None:
    files = dict(
        build_frontend_file_set(
            {
                "goal": "Build a mobile app for field teams with dashboard and detail screens",
                "build_target": "mobile_expo",
            }
        )
    )
    for rel, text in files.items():
        write(root / rel, text)


def make_thin_saas(root: Path) -> None:
    write_json(root / "package.json", {"scripts": {"build": "vite build"}, "dependencies": {"react": "latest"}})
    write(root / "index.html", '<div id="root"></div>')
    write(root / "src" / "main.jsx", "import App from './App.jsx'")
    write(root / "src" / "App.jsx", "export default function App(){return <div>sample page placeholder</div>}")
    write(root / "dist" / "index.html", '<div id="root"></div>')


def check_case(label: str, root: Path, goal: str, *, expect_pass: bool, build_target: str | None = None) -> Dict[str, Any]:
    result = validate_workspace_integrity(str(root), goal=goal, phase="final", build_target=build_target)
    ok = bool(result.get("passed")) is expect_pass
    return {
        "label": label,
        "ok": ok,
        "expected_pass": expect_pass,
        "passed": bool(result.get("passed")),
        "score": result.get("score"),
        "profile": result.get("profile"),
        "recommendation": result.get("recommendation"),
        "issues": result.get("issues") or [],
        "retry_route": result.get("retry_route") or {},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    tmp = ROOT / ".proof_tmp" / "1010_readiness"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    cases: List[Dict[str, Any]] = []
    try:
        builders = [
            ("saas_ui_pass", make_saas, "Build a beautiful modern SaaS product UI with dashboard analytics pricing settings and team", True, None),
            ("website_pass", make_site, "Build a polished marketing website for a product launch", True, None),
            ("mobile_pass", make_mobile, "Build a mobile app for field teams with dashboard and detail screens", True, "mobile_expo"),
            ("automation_pass", make_automation, "Build an automation workflow agent that runs on a webhook trigger", True, "agent_workflow"),
            ("api_backend_pass", make_api, "Build a FastAPI backend API", True, "api_backend"),
            ("thin_saas_rejected", make_thin_saas, "Build a beautiful modern SaaS product UI with dashboard analytics pricing settings and team", False, None),
        ]
        for label, builder, goal, expect_pass, target in builders:
            root = tmp / label
            builder(root)
            cases.append(check_case(label, root, goal, expect_pass=expect_pass, build_target=target))

        retry_plan = build_targeted_retry_plan(
            {
                "score": 48,
                "profile": "saas_ui",
                "issues": ["missing route", "weak design"],
                "retry_targets": ["design", "frontend", "integration"],
                "retry_route": {"agent_groups": ["Design Agent", "Frontend Generation", "Integration Agent"]},
            }
        )
        cases.append(
            {
                "label": "targeted_retry_plan",
                "ok": retry_plan["strategy"] == "targeted_dag_retry"
                and [step["step_key"] for step in retry_plan["steps"]]
                == ["frontend.styling", "frontend.scaffold", "implementation.integration"],
                "plan": retry_plan,
            }
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    report = {
        "status": "passed" if all(case["ok"] for case in cases) else "failed",
        "cases": cases,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.report_path:
        report_path = Path(args.report_path)
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

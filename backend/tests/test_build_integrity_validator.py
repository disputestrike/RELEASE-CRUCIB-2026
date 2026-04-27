import json
import shutil
from pathlib import Path

from backend.orchestration.build_integrity_validator import (
    detect_build_profile,
    route_retry_targets,
    validate_plan_integrity,
    validate_workspace_integrity,
)
from backend.orchestration.build_target_inference import infer_build_target
from backend.orchestration.build_targets import normalize_build_target
from backend.orchestration.generation_contract import parse_generation_contract
from backend.orchestration.generated_app_template import build_frontend_file_set


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def case_root(name):
    root = Path(__file__).resolve().parents[2] / ".biv_test_tmp" / name
    shutil.rmtree(root, ignore_errors=True)
    return root


def make_saas_workspace(root):
    write(
        root / "package.json",
        json.dumps(
            {
                "scripts": {
                    "dev": "vite --host",
                    "build": "vite build",
                    "preview": "vite preview",
                    "test": "vitest run",
                },
                "dependencies": {
                    "react": "^19.0.0",
                    "react-dom": "^19.0.0",
                    "react-router-dom": "^7.0.0",
                    "recharts": "^2.0.0",
                    "lucide-react": "^0.400.0",
                    "sonner": "^1.0.0",
                },
                "devDependencies": {"vite": "^7.0.0"},
            }
        ),
    )
    write(root / "index.html", '<div id="root"></div>')
    write(root / "dist" / "index.html", '<div id="root"></div><script type="module" src="/assets/app.js"></script>')
    write(root / "Dockerfile", "FROM node:22-alpine\nCMD [\"npm\", \"run\", \"preview\"]\n")
    write(root / "README.md", "How to run: npm install, npm run build, npm run preview. Deployment: Docker/Vercel.")
    write(
        root / "ideas.md",
        """
        Design option A: Obsidian Control.
        Design option B: Arctic Clarity.
        Design option C: Velvet Tech.
        Chosen direction: Arctic Clarity because it supports SaaS dashboards.
        """,
    )
    write(
        root / "src" / "index.css",
        """
        :root {
          --primary: #4f46e5;
          --background: #f8fafc;
          --foreground: #111827;
          --chart-1: #4f46e5;
          --sidebar: #ffffff;
          --radius: 8px;
        }
        .buttonVariants { font-family: Inter, sans-serif; }
        """,
    )
    write(
        root / "src" / "main.jsx",
        """
        import React from 'react';
        import { createRoot } from 'react-dom/client';
        import App from './App.jsx';
        import './index.css';
        createRoot(document.getElementById('root')).render(<App />);
        """,
    )
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
        import NotFound from './pages/NotFound.jsx';
        export default function App() {
          return <BrowserRouter><Routes>
            <Route path="/" element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/team" element={<Team />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<NotFound />} />
          </Routes></BrowserRouter>
        }
        """,
    )
    write(root / "src" / "components" / "MarketingNav.jsx", "export default function MarketingNav(){return <nav>CTA</nav>}")
    write(root / "src" / "components" / "DashboardLayout.jsx", "export default function DashboardLayout({children}){return <main>{children}</main>}")
    write(root / "src" / "components" / "ErrorBoundary.jsx", "export default function ErrorBoundary({children}){try{return children}catch(e){return null}}")
    page_body = """
    export default function PAGE(){
      const data = ['hero','feature','cta','kpi','chart','table','activity','invite','role','search','plans','faq','security','billing','integrations','funnel','top pages'];
      return <section>{data.join(' ')} Recharts AreaChart BarChart LineChart PieChart Tailwind Radix component variants</section>
    }
    """
    for page in ["Home", "Dashboard", "Analytics", "Team", "Pricing", "Settings", "NotFound"]:
        write(root / "src" / "pages" / f"{page}.jsx", page_body.replace("PAGE", page))


def issue_codes(result):
    return {item["code"] for item in result.get("structured_issues", [])}


def test_biv_retry_route_maps_categories_to_agent_groups():
    route = route_retry_targets(["frontend", "integration", "security"])

    assert route["strategy"] == "targeted_dag_retry"
    assert route["targets"] == ["frontend", "integration", "security"]
    assert "Frontend Generation" in route["agent_groups"]
    assert "Integration Agent" in route["agent_groups"]
    assert "Security Checker" in route["agent_groups"]


def test_biv_final_gate_blocks_completion_and_routes_missing_entrypoint_retry():
    root = case_root("final_gate_missing_entrypoint")
    write(
        root / "package.json",
        json.dumps(
            {
                "scripts": {"build": "vite build", "preview": "vite preview"},
                "dependencies": {"react": "latest", "react-dom": "latest"},
            }
        ),
    )
    write(root / "index.html", '<div id="root"></div>')
    write(
        root / "src" / "App.jsx",
        "export default function App(){return <div>dashboard analytics pricing settings team chart</div>}",
    )
    write(root / "dist" / "index.html", '<div id="root"></div>')

    result = validate_workspace_integrity(
        str(root),
        goal="Build a modern SaaS product UI with dashboard analytics pricing settings and team",
        phase="final",
    )

    assert not result["passed"]
    assert result["recommendation"] == "hard_fail"
    assert "missing_entry_point" in issue_codes(result)
    assert "frontend" in result["retry_targets"]
    assert result["retry_route"]["strategy"] == "targeted_dag_retry"
    assert "Frontend Generation" in result["retry_route"]["agent_groups"]
    assert "Integration Agent" in result["retry_route"]["agent_groups"]


def test_detects_saas_profile_from_goal():
    assert detect_build_profile("Build a modern SaaS product UI with dashboard, analytics and pricing") == "saas_ui"


def test_plan_validation_requires_design_options_for_ui():
    result = validate_plan_integrity("Pages: home. Components: card. Dependencies: react.", goal="Build a SaaS dashboard")
    assert not result["passed"]
    assert "planning" in result["retry_targets"]
    assert any("design options" in issue for issue in result["issues"])


def test_saas_workspace_passes_integrity_gate():
    tmp_path = case_root("saas_pass")
    make_saas_workspace(tmp_path)
    result = validate_workspace_integrity(
        str(tmp_path),
        goal="Build a beautiful modern SaaS product UI with dashboard analytics pricing settings and team pages",
        phase="final",
    )
    assert result["passed"], result
    assert result["score"] >= 85
    assert result["profile"] == "saas_ui"


def test_thin_placeholder_saas_workspace_fails_with_retry_targets():
    tmp_path = case_root("saas_broken")
    write(tmp_path / "package.json", json.dumps({"scripts": {"build": "vite build"}, "dependencies": {"react": "latest"}}))
    write(tmp_path / "index.html", '<div id="root"></div>')
    write(tmp_path / "src" / "main.jsx", "import './App.jsx'")
    write(tmp_path / "src" / "App.jsx", "export default function App(){return <div>sample team page placeholder</div>}")

    result = validate_workspace_integrity(
        str(tmp_path),
        goal="Build a modern SaaS product UI with multiple pages, analytics, pricing, settings and team",
        phase="final",
    )
    assert not result["passed"]
    assert result["recommendation"] == "hard_fail"
    assert "frontend" in result["retry_targets"] or "integration" in result["retry_targets"]
    assert any("placeholder" in issue.lower() or "missing mounted pages" in issue.lower() for issue in result["issues"])


def test_automation_workspace_requires_trigger_and_workflow():
    tmp_path = case_root("automation_pass")
    write(
        tmp_path / "package.json",
        json.dumps({"scripts": {"build": "echo ok", "start": "node automation/executor.js", "test": "echo ok"}}),
    )
    write(tmp_path / "Dockerfile", "FROM node:22-alpine\nCMD [\"npm\", \"start\"]\n")
    write(
        tmp_path / "automation" / "README.md",
        "Workflow executor runtime with run_agent bridge, webhook trigger, retry policy, and deployment notes.",
    )

    result = validate_workspace_integrity(
        str(tmp_path),
        goal="Build an automation workflow agent that runs on a webhook trigger",
        phase="final",
        build_target="agent_workflow",
    )
    assert result["passed"], result

    broken = case_root("automation_broken")
    write(broken / "package.json", json.dumps({"scripts": {"build": "echo ok"}}))
    broken_result = validate_workspace_integrity(
        str(broken),
        goal="Build an automation workflow agent that runs on a webhook trigger",
        phase="final",
        build_target="agent_workflow",
    )
    assert not broken_result["passed"]
    assert "automation" in broken_result["retry_targets"]


def test_mobile_expo_target_generates_validator_visible_artifacts():
    assert normalize_build_target("mobile") == "mobile_expo"
    inferred, candidates, reason = infer_build_target("Build a mobile app in Expo for iOS and Android")
    assert inferred == "mobile_expo", (inferred, candidates, reason)
    contract = parse_generation_contract("Build a React Native mobile app for iOS and Android")
    assert contract["recommended_build_target"] == "mobile_expo"
    assert "mobile" in contract["platforms"]

    files = dict(
        build_frontend_file_set(
            {
                "goal": "Build a mobile app for field teams with dashboard and detail screens",
                "build_target": "mobile_expo",
            }
        )
    )

    assert "expo-mobile/package.json" in files
    assert "expo-mobile/app.json" in files
    assert "expo-mobile/eas.json" in files
    assert "expo-mobile/App.tsx" in files
    assert "expo-mobile/src/screens/HomeScreen.tsx" in files

    root = case_root("mobile_generated")
    for rel, text in files.items():
        write(root / rel, text)

    result = validate_workspace_integrity(
        str(root),
        goal="Build a mobile app for field teams with dashboard and detail screens",
        phase="structure",
        build_target="mobile_expo",
    )
    assert result["passed"], result
    assert result["profile"] == "mobile"


def test_biv_negative_cases_block_common_broken_web_outputs():
    cases = [
        (
            "missing_main",
            {
                "package.json": json.dumps({"scripts": {"build": "vite build"}, "dependencies": {"react": "latest"}}),
                "index.html": '<div id="root"></div>',
                "src/App.jsx": "export default function App(){return <div>Dashboard chart pricing settings team</div>}",
            },
            "missing_entry_point",
        ),
        (
            "missing_app_router",
            {
                "package.json": json.dumps({"scripts": {"build": "vite build"}, "dependencies": {"react": "latest"}}),
                "index.html": '<div id="root"></div>',
                "src/main.jsx": "import React from 'react';",
            },
            "missing_root_app",
        ),
        (
            "broken_import",
            {
                "package.json": json.dumps({"scripts": {"build": "vite build"}, "dependencies": {"react": "latest"}}),
                "index.html": '<div id="root"></div>',
                "src/main.jsx": "import App from './App.jsx';",
                "src/App.jsx": "import Missing from './pages/Missing.jsx'; export default function App(){return <Missing />}",
            },
            "broken_local_imports",
        ),
        (
            "missing_build_script",
            {
                "package.json": json.dumps({"scripts": {"dev": "vite --host"}, "dependencies": {"react": "latest"}}),
                "index.html": '<div id="root"></div>',
                "src/main.jsx": "import App from './App.jsx';",
                "src/App.jsx": "import './index.css'; export default function App(){return <div>dashboard analytics pricing settings team chart</div>}",
                "src/index.css": ":root{--primary:#000;--background:#fff;--foreground:#111;--chart-1:#333;--sidebar:#fff;--radius:8px}.buttonVariants{}",
            },
            "missing_build_script",
        ),
        (
            "missing_preview_artifact",
            {
                "package.json": json.dumps({"scripts": {"build": "vite build"}, "dependencies": {"react": "latest"}}),
                "index.html": '<div id="root"></div>',
                "src/main.jsx": "import App from './App.jsx';",
                "src/App.jsx": "export default function App(){return <div>dashboard analytics pricing settings team chart</div>}",
            },
            "missing_static_preview_artifact",
        ),
        (
            "client_secret",
            {
                "package.json": json.dumps({"scripts": {"build": "vite build"}, "dependencies": {"react": "latest"}}),
                "index.html": '<div id="root"></div>',
                "src/main.jsx": "import App from './App.jsx';",
                "src/App.jsx": "export default function App(){const apiKey='sk-1234567890abcdefghijklmnop'; return <div>dashboard analytics pricing settings team chart</div>}",
                "dist/index.html": '<div id="root"></div>',
            },
            "client_secret_exposed",
        ),
    ]

    for name, files, expected_code in cases:
        root = case_root(f"negative_{name}")
        for rel, text in files.items():
            write(root / rel, text)
        result = validate_workspace_integrity(
            str(root),
            goal="Build a modern SaaS product UI with dashboard analytics pricing settings and team",
            phase="final",
        )
        assert not result["passed"], (name, result)
        assert expected_code in issue_codes(result), (name, expected_code, result)


def test_biv_blocks_orphan_page_and_weak_design_tokens():
    root = case_root("negative_orphan_design")
    make_saas_workspace(root)
    write(root / "src" / "pages" / "Billing.jsx", "export default function Billing(){return <div>Billing</div>}")
    write(root / "src" / "index.css", "body{color:#111}")

    result = validate_workspace_integrity(
        str(root),
        goal="Build a beautiful modern SaaS product UI with dashboard analytics pricing settings and team pages",
        phase="final",
    )
    codes = issue_codes(result)
    assert not result["passed"]
    assert "orphan_product_files" in codes
    assert "weak_design_tokens" in codes

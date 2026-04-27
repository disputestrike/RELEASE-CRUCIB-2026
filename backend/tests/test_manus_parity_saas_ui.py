import json

from backend.orchestration.generated_app_template import build_frontend_file_set
from backend.orchestration.preview_gate import (
    _detect_saas_product_intent,
    _verify_saas_product_contract,
)


SAAS_GOAL = (
    "Design a beautiful modern SaaS product UI with clean design system, "
    "multiple pages, components, and responsive layout"
)


def _combined(files):
    return "\n".join(files.values()).lower()


def test_saas_ui_goal_uses_manus_parity_template():
    files = dict(build_frontend_file_set({"goal": SAAS_GOAL}))
    pkg = json.loads(files["package.json"])

    assert "ideas.md" in files
    assert "src/components/MarketingNav.jsx" in files
    assert "src/components/DashboardLayout.jsx" in files
    assert "src/pages/HomePage.jsx" in files
    assert "src/pages/DashboardPage.jsx" in files
    assert "src/pages/AnalyticsPage.jsx" in files
    assert "src/pages/TeamPage.jsx" in files
    assert "src/pages/PricingPage.jsx" in files
    assert "src/pages/SettingsPage.jsx" in files
    assert "src/pages/NotFoundPage.jsx" in files
    assert "recharts" in pkg["dependencies"]
    assert "lucide-react" in pkg["dependencies"]

    combined = _combined(files)
    assert "/analytics" in combined
    assert "/pricing" in combined
    assert "/settings" in combined
    assert "areachart" in combined
    assert "piechart" in combined
    assert "crucib_incomplete" not in combined
    assert "sample team page" not in combined


def test_saas_product_gate_rejects_thin_scaffold():
    files = {
        "package.json": json.dumps(
            {
                "dependencies": {
                    "react": "18",
                    "react-dom": "18",
                    "react-router-dom": "6",
                    "zustand": "4",
                }
            }
        ),
        "src/App.jsx": """
          import { MemoryRouter, Routes, Route } from 'react-router-dom';
          import HomePage from './pages/HomePage';
          import DashboardPage from './pages/DashboardPage';
          import TeamPage from './pages/TeamPage';
          export default function App() {
            return <MemoryRouter><Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/team" element={<TeamPage />} />
            </Routes></MemoryRouter>;
          }
        """,
        "src/pages/HomePage.jsx": f"<h1>Home</h1><p>{SAAS_GOAL}</p>",
        "src/pages/DashboardPage.jsx": "<h1>Dashboard</h1><textarea placeholder='Notes (persisted)' />",
        "src/pages/TeamPage.jsx": "Sample team page - included in the scaffold so routing never references a missing component.",
        "src/components/ShellLayout.jsx": "export default function ShellLayout(){ return null; }",
        "src/styles/tokens.css": ":root { --color-primary: #3b82f6; }",
        "src/main.jsx": "import { createRoot } from 'react-dom/client'; createRoot(document.getElementById('root')).render(null);",
    }
    combined = _combined(files)

    assert _detect_saas_product_intent(files, combined) is True
    issues, proof = _verify_saas_product_contract(files, combined)

    assert issues
    assert any("analytics" in issue and "pricing" in issue and "settings" in issue for issue in issues)
    assert any("scaffold/placeholder language" in issue for issue in issues)
    assert not any("SaaS product completeness gate passed" in p["title"] for p in proof)


def test_saas_product_gate_accepts_generated_template():
    files = dict(build_frontend_file_set({"goal": SAAS_GOAL}))
    combined = _combined(files)

    assert _detect_saas_product_intent(files, combined) is True
    issues, proof = _verify_saas_product_contract(files, combined)

    assert issues == []
    assert any("SaaS product completeness gate passed" in p["title"] for p in proof)

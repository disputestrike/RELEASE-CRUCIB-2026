import json
import shutil
import tempfile
from pathlib import Path

from backend.orchestration.contract_artifacts import (
    persist_contract_artifacts,
    persist_steering_contract_delta,
)
from backend.orchestration.contract_generator import BuildContractGenerator
from backend.orchestration.generated_app_template import build_frontend_file_set
from backend.orchestration.intent_classifier import IntentClassifier
from backend.orchestration.build_integrity_validator import validate_workspace_integrity
from backend.orchestration.build_target_inference import infer_build_target


WEBSITE_PROMPT = (
    "Build me a stunning multi-page website with hero, features grid, "
    "pricing, testimonials, and footer — beautiful modern design"
)

INTERNAL_ADMIN_PROMPT = "Build an internal admin tool with data tables, forms, and approval workflows"


def _write_file_set(root: Path, files):
    for rel, content in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_website_intent_generates_marketing_contract():
    dimensions = IntentClassifier().classify(WEBSITE_PROMPT)
    contract = BuildContractGenerator().generate(dimensions, WEBSITE_PROMPT, "job-website")

    assert contract.build_class == "web_marketing_site"
    assert "/features" in contract.required_routes
    assert "/pricing" in contract.required_routes
    assert "/testimonials" in contract.required_routes
    assert "src/styles/tokens.css" in contract.required_files
    assert "src/components/marketing/HeroSection.jsx" in contract.required_files
    assert not contract.required_backend_modules
    assert not contract.required_database_tables


def test_website_template_is_product_folder_not_app_scaffold():
    files = dict(build_frontend_file_set({"id": "job-website", "goal": WEBSITE_PROMPT}))
    joined = "\n".join(files.values())

    assert "ideas.md" in files
    assert "src/styles/tokens.css" in files
    assert "src/styles/global.css" in files
    assert "src/routes.jsx" in files
    assert "src/components/navigation/MarketingNav.jsx" in files
    assert "src/components/marketing/HeroSection.jsx" in files
    assert "src/components/marketing/FeatureGrid.jsx" in files
    assert "src/components/marketing/PricingCards.jsx" in files
    assert "src/components/marketing/TestimonialGrid.jsx" in files
    assert "src/components/marketing/Footer.jsx" in files
    assert "src/pages/LoginPage.jsx" not in files
    assert "src/pages/DashboardPage.jsx" not in files
    assert "src/pages/TeamPage.jsx" not in files
    assert "CRUCIB_INCOMPLETE" not in joined
    assert "agent completed tool loop" not in joined
    assert '"_placeholder": "generated"' not in joined


def test_internal_admin_prompt_uses_admin_contract_not_generic_web():
    target, _candidates, _reason = infer_build_target(INTERNAL_ADMIN_PROMPT)
    dimensions = IntentClassifier().classify(INTERNAL_ADMIN_PROMPT)
    contract = BuildContractGenerator().generate(dimensions, INTERNAL_ADMIN_PROMPT, "job-admin")

    assert target == "internal_admin_tool"
    assert dimensions.values["internal_admin"] is True
    assert dimensions.values["cli"] is False
    assert contract.build_class == "internal_admin_tool"
    assert "/records" in contract.required_routes
    assert "/forms" in contract.required_routes
    assert "/approvals" in contract.required_routes
    assert "src/components/tables/DataTable.jsx" in contract.required_files
    assert "db/migrations/001_initial.sql" in contract.required_files
    assert "records" in contract.required_database_tables
    assert "approval_requests" in contract.required_database_tables


def test_internal_admin_template_builds_real_admin_surface():
    files = dict(build_frontend_file_set({"id": "job-admin", "goal": INTERNAL_ADMIN_PROMPT, "build_target": "internal_admin_tool"}))
    joined = "\n".join(files.values())

    assert "export default function App" in files["src/App.jsx"]
    assert "BrowserRouter" in files["src/App.jsx"]
    assert "/records" in files["src/App.jsx"]
    assert "/forms" in files["src/App.jsx"]
    assert "/approvals" in files["src/App.jsx"]
    assert "src/components/tables/DataTable.jsx" in files
    assert "src/components/forms/AdminRecordForm.jsx" in files
    assert "src/components/approvals/ApprovalQueue.jsx" in files
    assert "backend/main.py" in files
    assert "db/migrations/001_initial.sql" in files
    assert "Application is being generated" not in joined
    assert "Generated workspace aligned to:" not in joined


def test_internal_admin_biv_blocks_placeholder_app():
    scratch = Path(tempfile.mkdtemp(prefix="crucibai_admin_bad_", dir="C:\\tmp"))
    try:
        workspace = scratch / "bad"
        (workspace / "src").mkdir(parents=True)
        (workspace / "src" / "App.jsx").write_text(
            "export default function App(){return <div><h1>Loading...</h1><p>Application is being generated. Please wait.</p></div>}",
            encoding="utf-8",
        )
        (workspace / "src" / "main.jsx").write_text(
            "import App from './App.jsx';\nconsole.log(App);",
            encoding="utf-8",
        )

        result = validate_workspace_integrity(
            str(workspace),
            goal=INTERNAL_ADMIN_PROMPT,
            build_target="internal_admin_tool",
            phase="final",
        )

        assert result["passed"] is False
        assert result["hard_block"] is True
        assert any("scaffold placeholders" in issue.lower() for issue in result["issues"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_contract_artifacts_reconcile_routes_and_dependencies():
    scratch = Path(tempfile.mkdtemp(prefix="crucibai_contract_", dir="C:\\tmp"))
    try:
        workspace = scratch / "site"
        files = build_frontend_file_set({"id": "job-website", "goal": WEBSITE_PROMPT})
        _write_file_set(workspace, files)

        result = persist_contract_artifacts(
            str(workspace),
            {"id": "job-website", "goal": WEBSITE_PROMPT},
        )

        assert result["contract"].build_class == "web_marketing_site"
        assert result["satisfied"] is True
        assert result["route_map"]
        assert result["dependency_graph"]
        assert result["missing"] == {}

        route_map = json.loads((workspace / ".crucibai" / "route_map.json").read_text(encoding="utf-8"))
        dependency_graph = json.loads((workspace / ".crucibai" / "dependency_graph.json").read_text(encoding="utf-8"))
        assert "/pricing" in route_map
        assert dependency_graph
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_steering_expands_contract_without_erasing_workspace():
    scratch = Path(tempfile.mkdtemp(prefix="crucibai_steer_", dir="C:\\tmp"))
    try:
        workspace = scratch / "site"
        files = build_frontend_file_set({"id": "job-website", "goal": WEBSITE_PROMPT})
        _write_file_set(workspace, files)
        persist_contract_artifacts(
            str(workspace),
            {"id": "job-website", "goal": WEBSITE_PROMPT},
        )

        result = persist_steering_contract_delta(
            str(workspace),
            {"id": "job-website", "goal": WEBSITE_PROMPT},
            "Add a backend API and database to collect newsletter signups.",
        )

        assert result["accepted"] is True
        assert result["delta"]["trigger"] == "human_request"
        assert result["contract"]["version"] == 2
        assert result["contract"]["build_class"] == "web_marketing_site"
        assert "src/components/marketing/HeroSection.jsx" in result["contract"]["required_files"]
        assert "backend/main.py" in result["contract"]["required_files"]
        assert "lead_capture" in result["contract"]["required_backend_modules"]
        assert "subscribers" in result["contract"]["required_database_tables"]
        assert (workspace / "src" / "pages" / "HomePage.jsx").exists()
        assert (workspace / ".crucibai" / "contract_deltas.jsonl").exists()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

"""
Unit tests for BuildContract-driven meta-factory.

Tests the core components:
- BuildContract versioning and progress tracking
- IntentClassifier dimension extraction
- BuildContractGenerator synthesis
- Contract satisfaction checking
"""

import pytest
from datetime import datetime
from backend.orchestration.build_contract import BuildContract, ContractDelta
from backend.orchestration.intent_classifier import IntentClassifier, IntentDimensions
from backend.orchestration.contract_generator import BuildContractGenerator


class TestBuildContract:
    """Tests for BuildContract dataclass."""
    
    def test_contract_creation(self):
        """Contract can be created with default values."""
        contract = BuildContract(
            build_id="test-123",
            build_class="saas",
            product_name="Test App",
            original_goal="Build a test app"
        )
        
        assert contract.build_id == "test-123"
        assert contract.version == 1
        assert contract.status == "draft"
        assert contract.minimum_score == 85
    
    def test_contract_freeze(self):
        """Contract can be frozen after approval."""
        contract = BuildContract(
            build_id="test-123",
            build_class="saas",
            product_name="Test App",
            original_goal="Build a test app"
        )
        
        assert contract.status == "draft"
        contract.freeze()
        assert contract.status == "frozen"
    
    def test_contract_delta_application(self):
        """ContractDelta creates new version without mutating original."""
        contract = BuildContract(
            build_id="test-123",
            build_class="saas",
            product_name="Test App",
            original_goal="Build a test app",
            required_files=["file1.tsx", "file2.tsx"]
        )
        contract.freeze()
        
        # Create delta
        delta = ContractDelta(
            delta_id="delta-1",
            timestamp=datetime.utcnow(),
            previous_version=1,
            new_version=2,
            changes=[{"field": "required_files", "old": ["file1.tsx", "file2.tsx"], "new": ["file1.tsx", "file2.tsx", "file3.tsx"]}],
            reason="Added missing file",
            trigger="repair_failed",
            approved_by="test_agent",
            context={"error": "missing file3"}
        )
        
        # Apply delta
        new_contract = contract.apply_delta(delta)
        
        # Original unchanged
        assert contract.version == 1
        assert contract.status == "frozen"
        assert len(contract.required_files) == 2
        
        # New contract updated
        assert new_contract.version == 2
        assert new_contract.status == "draft"  # Requires re-approval
        assert len(new_contract.required_files) == 3
    
    def test_contract_progress_update(self):
        """Progress tracking works correctly."""
        contract = BuildContract(
            build_id="test-123",
            build_class="saas",
            product_name="Test App",
            original_goal="Build a test app",
            required_files=["file1.tsx", "file2.tsx", "file3.tsx"]
        )
        
        # Initialize progress
        contract.contract_progress["required_files"]["missing"] = ["file1.tsx", "file2.tsx", "file3.tsx"]
        
        # Mark one as done
        contract.update_progress("required_files", "file1.tsx", done=True)
        
        progress = contract.contract_progress["required_files"]
        assert "file1.tsx" in progress["done"]
        assert "file1.tsx" not in progress["missing"]
        assert progress["percent"] == 33  # 1/3
    
    def test_contract_satisfaction_check(self):
        """Contract satisfaction detected when all items complete."""
        contract = BuildContract(
            build_id="test-123",
            build_class="saas",
            product_name="Test App",
            original_goal="Build a test app"
        )
        
        # Set up progress with all items done
        contract.contract_progress = {
            "required_files": {"done": ["file1.tsx"], "missing": [], "percent": 100},
            "required_routes": {"done": ["/"], "missing": [], "percent": 100}
        }
        
        assert contract.is_satisfied() is True
        
        # Add missing item
        contract.contract_progress["required_files"]["missing"].append("file2.tsx")
        assert contract.is_satisfied() is False


class TestIntentClassifier:
    """Tests for IntentClassifier dimension extraction."""
    
    def test_helios_classification(self):
        """Helios prompt decomposes into correct dimensions."""
        classifier = IntentClassifier()
        
        helios_prompt = """Build Helios Operations Cloud — multi-tenant B2B SaaS.
        
        MULTI-TENANT: Strict tenant isolation per organization (Org → Workspace → Project).
        CRM: Full CRM module (accounts, contacts, deals).
        COMPLIANCE: Immutable audit trail.
        WORKERS: Worker/job system for long tasks.
        INTEGRATIONS: Pluggable integration adapters.
        ANALYTICS: Analytics dashboards.
        React + TypeScript SPA, FastAPI backend, PostgreSQL, Redis."""
        
        result = classifier.classify(helios_prompt)
        
        # Check dimensions detected
        assert result.values.get("tenancy") is True
        assert result.values.get("crm") is True
        assert result.values.get("compliance") is True
        assert result.values.get("workers") is True
        assert result.values.get("integrations") is True
        assert result.values.get("analytics") is True
        assert result.values.get("frontend") is True
        assert result.values.get("backend") is True
        assert result.values.get("database") is True
        
        # Check specific patterns
        assert result.values.get("tenancy_model") == "org_workspace_project"
        assert result.values.get("frontend_framework") == "React+TypeScript"
        assert result.values.get("backend_framework") == "FastAPI"
        assert result.values.get("database_engine") == "PostgreSQL"
        
        # Risk factors detected
        assert "compliance" in result.risk_factors
        assert result.auto_approve is False  # Requires human approval
    
    def test_api_only_classification(self):
        """API-only prompt does NOT get SaaS UI dimensions."""
        classifier = IntentClassifier()
        
        api_prompt = "Build a REST API for user management with FastAPI and PostgreSQL"
        
        result = classifier.classify(api_prompt)
        
        # API dimensions
        assert result.values.get("api") is True or result.values.get("backend") is True
        assert result.values.get("database") is True
        
        # NO frontend dimensions
        assert result.values.get("frontend") is False or result.values.get("frontend") is None
        
        # Lower risk = auto-approve
        assert result.auto_approve is True
        assert len(result.risk_factors) == 0
    
    def test_cli_classification(self):
        """CLI tool prompt gets CLI dimensions only."""
        classifier = IntentClassifier()
        
        cli_prompt = "Build a CLI tool for CSV processing with Python Click"
        
        result = classifier.classify(cli_prompt)
        
        assert result.values.get("cli") is True
        assert result.values.get("frontend") is False or result.values.get("frontend") is None
        assert result.values.get("api") is False or result.values.get("api") is None


class TestBuildContractGenerator:
    """Tests for BuildContractGenerator synthesis."""
    
    def test_helios_contract_synthesis(self):
        """Helios dimensions synthesize into correct contract."""
        generator = BuildContractGenerator()
        classifier = IntentClassifier()
        
        helios_prompt = """Build Helios Operations Cloud — multi-tenant B2B SaaS.
        CRM, compliance, workers, integrations, analytics.
        React + TypeScript, FastAPI, PostgreSQL, Redis."""
        
        dimensions = classifier.classify(helios_prompt)
        contract = generator.generate(dimensions, helios_prompt, "helios-job-123")
        
        # Check contract generated correctly
        assert contract.build_id == "helios-job-123"
        assert contract.build_class == "regulated_saas"  # tenancy + compliance
        assert contract.product_name == "Helios Operations Cloud"
        assert contract.status == "draft"
        
        # Check stack
        assert contract.stack.get("frontend") == "React+TypeScript"
        assert contract.stack.get("backend") == "FastAPI"
        assert contract.stack.get("database") == "PostgreSQL"
        assert contract.stack.get("queue") == "Redis"
        
        # Check required files
        assert "client/src/main.tsx" in contract.required_files
        assert "backend/main.py" in contract.required_files
        assert "Dockerfile" in contract.required_files
        
        # Check required routes
        assert "/" in contract.required_routes
        assert "/dashboard" in contract.required_routes
        assert "/dashboard" in contract.required_routes
        assert "/crm" in contract.required_routes
        
        # Check database tables
        assert "users" in contract.required_database_tables
        assert "organizations" in contract.required_database_tables
        assert "accounts" in contract.required_database_tables
        
        # Check workers
        assert "email_digest" in contract.required_workers
        
        # Check proof types
        assert "build_pass" in contract.required_proof_types
        assert "preview_pass" in contract.required_proof_types
        
        # Check forbidden providers list is defined
        assert isinstance(contract.forbidden_providers, list)
        
        # Check goal criteria
        assert any(c["criterion"] == "tenant_isolation" for c in contract.goal_success_criteria)
        assert any(c["criterion"] == "crm_functionality" for c in contract.goal_success_criteria)
        
        # Check progress initialized
        assert len(contract.contract_progress["required_files"]["missing"]) > 0
    
    def test_api_only_contract_synthesis(self):
        """API-only dimensions do NOT get SaaS UI requirements."""
        generator = BuildContractGenerator()
        classifier = IntentClassifier()
        
        api_prompt = "Build a REST API for user management with FastAPI and PostgreSQL"
        
        dimensions = classifier.classify(api_prompt)
        contract = generator.generate(dimensions, api_prompt, "api-job-456")
        
        # NO frontend files
        assert "client/src/main.tsx" not in contract.required_files
        assert not contract.required_preview_routes
        
        # API-specific files
        assert "backend/main.py" in contract.required_files
        assert "/api/health" in contract.required_api_endpoints
        
        # Database required
        assert "users" in contract.required_database_tables
    
    def test_cli_contract_synthesis(self):
        """CLI dimensions get CLI requirements only."""
        generator = BuildContractGenerator()
        classifier = IntentClassifier()
        
        cli_prompt = "Build a CLI tool for CSV processing"
        
        dimensions = classifier.classify(cli_prompt)
        contract = generator.generate(dimensions, cli_prompt, "cli-job-789")
        
        assert contract.build_class == "cli_tool"
        
        # NO web requirements
        assert not contract.required_preview_routes
        assert not contract.required_screenshots
        assert not contract.required_visual_checks
        
        # CLI-specific requirements would be here
        assert "README.md" in contract.required_docs


class TestContractSatisfaction:
    """Integration tests for contract satisfaction checking."""
    
    def test_helios_contract_fully_satisfied(self):
        """Full Helios contract satisfaction check."""
        generator = BuildContractGenerator()
        classifier = IntentClassifier()
        
        helios_prompt = """Build Helios Operations Cloud — multi-tenant B2B SaaS.
        CRM, compliance, workers, integrations, analytics.
        React + TypeScript, FastAPI, PostgreSQL, Redis."""
        
        dimensions = classifier.classify(helios_prompt)
        contract = generator.generate(dimensions, helios_prompt, "helios-test")
        
        # Simulate all items being completed
        for file in contract.required_files:
            contract.update_progress("required_files", file, done=True)
        
        for route in contract.required_routes:
            contract.update_progress("required_routes", route, done=True)
        
        for table in contract.required_database_tables:
            contract.update_progress("required_database_tables", table, done=True)
        
        assert contract.is_satisfied() is True
    
    def test_contract_partially_satisfied_blocked(self):
        """Partial contract satisfaction blocks export."""
        generator = BuildContractGenerator()
        classifier = IntentClassifier()
        
        helios_prompt = "Build Helios Operations Cloud"
        dimensions = classifier.classify(helios_prompt)
        contract = generator.generate(dimensions, helios_prompt, "helios-partial")
        
        # Only complete some items
        if contract.required_files:
            contract.update_progress("required_files", contract.required_files[0], done=True)
        
        assert contract.is_satisfied() is False
        assert contract.contract_progress["required_files"]["percent"] <= 100


class TestHardCapRules:
    """Tests for scoring hard-cap rules."""
    
    def test_build_failed_capped_at_35(self):
        """Build failure caps score at 35."""
        contract = BuildContract(build_id="test", build_class="saas", product_name="Test", original_goal="Test")
        
        # Find the build_failed cap rule
        build_fail_cap = next((r for r in contract.hard_cap_rules if r["condition"] == "build_failed"), None)
        assert build_fail_cap is not None
        assert build_fail_cap["max_score"] == 35
    
    def test_preview_failed_capped_at_40(self):
        """Preview failure caps score at 40."""
        contract = BuildContract(build_id="test", build_class="saas", product_name="Test", original_goal="Test")
        
        preview_fail_cap = next((r for r in contract.hard_cap_rules if r["condition"] == "preview_failed"), None)
        assert preview_fail_cap is not None
        assert preview_fail_cap["max_score"] == 40
    
    def test_blocking_verifier_sets_success_false(self):
        """Blocking verifier failure sets success=False."""
        contract = BuildContract(build_id="test", build_class="saas", product_name="Test", original_goal="Test")
        
        blocking_rule = next((r for r in contract.hard_cap_rules if r["condition"] == "blocking_verifier_failed"), None)
        assert blocking_rule is not None
        assert blocking_rule["success"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
agent_real_behavior.py — Maps each AGENT_DAG agent to its primary output file path.

Used by:
  - swarm_agent_runner.py: to write extracted LLM output to the correct workspace file
  - workspace_assembly_pipeline.py: as the default_rel for parse_proposed_files()

The paths here are relative to the job workspace root.
"""

ARTIFACT_PATHS: dict[str, str] = {
    # Core generation agents
    "Frontend Generation": "src/App.jsx",
    "Backend Generation": "backend/main.py",
    "Database Agent": "db/migrations/001_initial.sql",
    "API Integration": "backend/api_integration.py",
    "Test Generation": "tests/test_app.py",
    "Design Agent": "src/design_system.json",
    "Layout Agent": "src/Layout.jsx",

    # Config / setup agents
    "Stack Selector": "STACK.md",
    "Planner": "PLAN.md",
    "Requirements Clarifier": "REQUIREMENTS.md",
    "Native Config Agent": "app.json",
    "Store Prep Agent": "SUBMIT_TO_APPLE.md",

    # Quality / analysis agents
    "Security Checker": "proof/SECURITY_CHECKLIST.md",
    "UX Auditor": "proof/UX_AUDIT.md",
    "Performance Analyzer": "proof/PERFORMANCE_REPORT.md",
    "Test Executor": "proof/TEST_RESULTS.md",

    # Deployment / ops agents
    "Deployment Agent": "deploy/DEPLOY_GUIDE.md",
    "DevOps Agent": "docker-compose.yml",
    "Error Recovery": "proof/ERROR_RECOVERY.md",

    # Export / content agents
    "Documentation Agent": "README.md",
    "SEO Agent": "src/SEO.jsx",
    "Content Agent": "src/content.json",
    "Brand Agent": "src/brand.json",
    "Memory Agent": "META/memory.md",
    "PDF Export": "exports/summary.md",
    "Excel Export": "exports/data.csv",
    "Markdown Export": "exports/export.md",

    # Specialized agents
    "Scraping Agent": "backend/scraper.py",
    "Automation Agent": "backend/automation.py",
    "Image Generation": "src/image_prompts.json",
    "Video Generation": "src/video_prompts.json",
    "Auth Setup Agent": "backend/auth.py",
    "File Tool Agent": "src/App.jsx",
    "Data Visualization Agent": "src/charts/Dashboard.jsx",
    "Analytics Agent": "backend/analytics.py",
    "GitHub Actions CI Agent": ".github/workflows/ci.yml",
}

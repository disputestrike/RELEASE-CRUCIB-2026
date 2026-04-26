"""Canonical code generation standard for CrucibAI build agents.

This module is intentionally importable by prompts, scaffolds, and tests so the
quality bar does not drift into copy-only documentation.
"""

from __future__ import annotations

from typing import Dict, List


STANDARD_VERSION = "2026.04-senior-product-codebase"


CODE_GENERATION_AGENT_APPENDIX = f"""

CRUCIBAI CODEBASE STANDARD ({STANDARD_VERSION})
You are not allowed to generate a shallow demo scaffold for product prompts.
Generate a maintainable senior-engineer codebase with enough files, domain
modules, reusable components, state, service layers, typed contracts, tests,
docs, persistent document-ingestion artifacts, and a tokenized design system.

Required shape for serious frontend apps:
- client/src/_core/config, constants, routes, providers
- client/src/components/ui, layout, forms, tables, feedback, navigation
- client/src/pages for screens; keep App thin (providers, routes, layout only)
- client/src/features/<domain>/components, hooks, services, types, utils, data, tests
- client/src/services, store, styles, types, utils

Required shape for full-stack apps:
- client, server, shared, db or drizzle, docs, tests
- routes/controllers/services/repositories/schemas/models/middleware/workers/integrations
- shared types, constants, validators, schemas

Quantity bar:
- small app: 15-30 source files
- medium app: 40-80 source files
- large admin/SaaS/workflow/internal tool: 80-150 source files
- enterprise/platform app: 150+ files when needed

Mandatory generated docs:
- README.md
- CODE_MANIFEST.md listing every file, purpose, feature, and category
- FEATURE_COVERAGE.md mapping requested features to files, state, services, tests
- ARCHITECTURE.md explaining frontend/backend/shared boundaries
- REQUIREMENTS_FROM_DOCUMENTS.md when documents are uploaded or referenced
- DESIGN_BRIEF_FROM_DOCUMENTS.md when documents influence design
- TECHNICAL_SPEC_FROM_DOCUMENTS.md when documents influence architecture

Document ingestion persistence:
- never discard uploaded/source documents after reading
- create docs/source_documents, docs/extracted_text, docs/summaries,
  docs/requirements, docs/design_brief, docs/technical_spec, docs/research_notes
- create runtime/ingestion/ingestion_manifest.json, source_map.json, extraction_log.json
- persist original file name/type, extracted text summary, requirements, design notes,
  technical constraints, business rules, timestamp, ingestion status, and feature traceability

Quality gates:
- no giant App file, route file, or all-in-one component
- no direct random fetch calls in components; use services/apiClient
- reusable UI primitives for buttons, inputs, selects, modals, drawers, cards, badges, tabs, tooltips
- layout, data-table, form, and feedback components for serious apps
- state covers selected item, filters, loading, errors, forms, modal/drawer state
- design tokens for colors, type, spacing, radius, shadows, z-index, transitions, breakpoints
- tests for routes, services, schemas, route rendering, forms, tables/filters
- document-derived features must trace back to persisted ingestion artifacts
- no fake placeholder logic, TODO-only files, dead imports, temp/final/fixed filenames
- inspect the final file tree before saying done; if the prompt is complex and the tree is thin, keep generating
""".strip()


STANDARD_DOC = f"""# CrucibAI Code Generation Standard

Version: `{STANDARD_VERSION}`

Generated projects must look like real senior-engineer-built applications, not
thin demos. The builder must scale code quantity and folder depth to the prompt.
If documents are uploaded or referenced, the generated project must persist the
source document artifacts, extraction metadata, summaries, requirements, design
briefs, and technical specifications inside the project.

## Required Shape

Frontend-heavy apps should include `_core`, reusable components, pages, features,
services, store, styles, types, utils, tests, and documentation. Full-stack apps
should include `client`, `server`, `shared`, `db` or `drizzle`, `docs`, and
`tests`, with layered server boundaries.

## Non-Negotiables

- App entry files stay thin.
- Domain logic lives in feature modules.
- UI calls typed services, not raw fetch sprinkled through components.
- Backend routes coordinate; services own business logic; repositories own data.
- Every serious app includes reusable UI primitives, feedback states, forms,
  tables, design tokens, state, docs, and tests.
- File count must match complexity.
- Document ingestion artifacts must be saved under `docs/` and `runtime/ingestion/`.

## Completion Inspection

Before marking complete, verify file quantity, feature separation, services,
types/schemas, tokenized styles, tests, docs, document traceability, and
maintainable file sizes.
"""


REQUIRED_DOC_FILES = [
    "README.md",
    "CODE_MANIFEST.md",
    "FEATURE_COVERAGE.md",
    "ARCHITECTURE.md",
    "REQUIREMENTS_FROM_DOCUMENTS.md",
    "DESIGN_BRIEF_FROM_DOCUMENTS.md",
    "TECHNICAL_SPEC_FROM_DOCUMENTS.md",
]


QUALITY_STRUCTURE_PATHS = [
    "README.md",
    "src/_core/config/appConfig.js",
    "src/_core/constants/routes.js",
    "src/components/ui/Button.jsx",
    "src/components/ui/Input.jsx",
    "src/components/ui/Card.jsx",
    "src/components/layout/PageHeader.jsx",
    "src/components/layout/ContentPanel.jsx",
    "src/components/tables/DataTable.jsx",
    "src/components/feedback/EmptyState.jsx",
    "src/components/forms/FormField.jsx",
    "src/features/dashboard/components/MetricsGrid.jsx",
    "src/features/users/components/UserTable.jsx",
    "src/features/users/hooks/useUsers.js",
    "src/features/users/services/userService.js",
    "src/services/apiClient.js",
    "src/services/authService.js",
    "src/store/useAppStore.js",
    "src/styles/tokens.css",
    "src/styles/global.css",
    "docs/CODE_GENERATION_STANDARD.md",
    "docs/CODE_MANIFEST.md",
    "docs/FEATURE_COVERAGE.md",
    "docs/ARCHITECTURE.md",
    "docs/REQUIREMENTS_FROM_DOCUMENTS.md",
    "docs/DESIGN_BRIEF_FROM_DOCUMENTS.md",
    "docs/TECHNICAL_SPEC_FROM_DOCUMENTS.md",
    "docs/source_documents/.gitkeep",
    "docs/extracted_text/.gitkeep",
    "docs/summaries/.gitkeep",
    "docs/requirements/.gitkeep",
    "docs/design_brief/.gitkeep",
    "docs/technical_spec/.gitkeep",
    "docs/research_notes/.gitkeep",
    "runtime/ingestion/ingestion_manifest.json",
    "runtime/ingestion/source_map.json",
    "runtime/ingestion/extraction_log.json",
]


COMPLEXITY_FILE_MINIMUMS: Dict[str, int] = {
    "small": 15,
    "medium": 40,
    "large": 80,
    "enterprise": 150,
}


def classify_prompt_complexity(goal: str) -> str:
    """Coarse complexity tier for generation quantity decisions."""
    g = (goal or "").lower()
    enterprise_markers = (
        "enterprise",
        "multi-tenant",
        "compliance",
        "audit",
        "rbac",
        "workflow",
        "approval",
        "admin",
        "permissions",
        "analytics",
        "reports",
        "billing",
        "automation",
        "integration",
    )
    count = sum(1 for marker in enterprise_markers if marker in g)
    if count >= 7:
        return "enterprise"
    if count >= 4:
        return "large"
    if count >= 2:
        return "medium"
    return "small"


def expected_minimum_files(goal: str) -> int:
    return COMPLEXITY_FILE_MINIMUMS[classify_prompt_complexity(goal)]


def required_quality_paths() -> List[str]:
    return list(QUALITY_STRUCTURE_PATHS)

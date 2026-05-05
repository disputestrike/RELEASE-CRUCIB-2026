"""
Execution modes / build targets — broad product surface with honest per-run guarantees.

The platform vision is multi-stack; each Auto-Runner job selects a *target* so UX and docs
stay aligned (what this run proves vs what’s on the roadmap for that track).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Canonical ids stored on plans as plan["crucib_build_target"]
DEFAULT_BUILD_TARGET = "vite_react"

_ALIASES = {
    "vite": "vite_react",
    "react": "vite_react",
    "web": "vite_react",
    "full_system": "full_system_generator",
    "fullsystem": "full_system_generator",
    "multi_stack": "full_system_generator",
    "generator": "full_system_generator",
    "next": "next_app_router",
    "nextjs": "next_app_router",
    "next.js": "next_app_router",
    "app_router": "next_app_router",
    "api": "api_backend",
    "backend": "api_backend",
    "internal": "internal_admin_tool",
    "internal_admin": "internal_admin_tool",
    "internal_tool": "internal_admin_tool",
    "admin": "internal_admin_tool",
    "admin_tool": "internal_admin_tool",
    "admin_panel": "internal_admin_tool",
    "agents": "agent_workflow",
    "automation": "agent_workflow",
    "mobile": "mobile_expo",
    "mobile_app": "mobile_expo",
    "expo": "mobile_expo",
    "react_native": "mobile_expo",
    "react-native": "mobile_expo",
    "ios": "mobile_expo",
    "android": "mobile_expo",
    "marketing": "static_site",
    "landing": "static_site",
}


def normalize_build_target(raw: Optional[str]) -> str:
    s = (
        (raw or DEFAULT_BUILD_TARGET)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )
    if not s:
        return DEFAULT_BUILD_TARGET
    s = _ALIASES.get(s, s)
    if s not in BUILD_TARGETS:
        return DEFAULT_BUILD_TARGET
    return s


def build_target_catalog() -> List[Dict[str, Any]]:
    """Ordered list for GET /api/orchestrator/build-targets."""
    return [BUILD_TARGETS[k] for k in DISPLAY_ORDER]


DISPLAY_ORDER = [
    "full_system_generator",
    "vite_react",
    "next_app_router",
    "static_site",
    "internal_admin_tool",
    "mobile_expo",
    "api_backend",
    "agent_workflow",
]

BUILD_TARGETS: Dict[str, Dict[str, Any]] = {
    "full_system_generator": {
        "id": "full_system_generator",
        "label": "Workspace build",
        "tagline": "Single runtime build path for complex prompts across frontend, backend, data, infra, tests, and docs.",
        "guarantees": [
            "Routes complex prompts through one persistent build loop instead of the old fixed agent DAG.",
            "Uses file, search, edit, shell, verification, and repair events as the runtime contract.",
            "Fails explicitly when build proof still fails instead of silently downgrading to a scaffold or legacy pack.",
        ],
        "on_this_run": [
            "Verifier depth still depends on the generated stack and what the runtime can execute inside this pipeline.",
            "Generated files may span frontend/, backend/, infra/, tests/, and docs/ in one job.",
        ],
        "roadmap": [
            "Deeper runtime verification per stack family instead of one web-first preview contract.",
        ],
    },
    "vite_react": {
        "id": "vite_react",
        "label": "Full-stack web (Vite + React)",
        "tagline": "Default Auto-Runner path — SPA, Sandpack preview, FastAPI sketch, SQL, verifiers.",
        "guarantees": [
            "Vite + React (JS) frontend scaffold with router-ready pages",
            "Python FastAPI backend sketch and SQL migration stubs",
            "Workspace preview (Sandpack) and compile-style verification gates",
        ],
        "on_this_run": [
            "Primary app lives at repo root (package.json + src/) as today.",
        ],
        "roadmap": [
            "Optional Turbopack / RSC experiments as a separate track.",
        ],
    },
    "next_app_router": {
        "id": "next_app_router",
        "label": "Next.js App Router (track)",
        "tagline": "Same verified Vite root for this DAG, plus a parallel Next starter under next-app-stub/.",
        "guarantees": [
            "Everything in the Vite + React track (root build still drives preview gate).",
            "A copy-pasteable Next.js 14 App Router starter in next-app-stub/ (own package.json).",
            "Docs describing how to grow the Next track without breaking the default pipeline.",
        ],
        "on_this_run": [
            "Root workspace: Vite app (unchanged) — npm run build at root is what verifiers expect today.",
            "next-app-stub/: run cd next-app-stub && npm install && npm run dev locally for App Router.",
        ],
        "roadmap": [
            "First-class Next pipeline (single package.json, RSC, deploy targets) as a future DAG mode.",
        ],
    },
    "static_site": {
        "id": "static_site",
        "label": "Marketing / static site",
        "tagline": "Vite SPA oriented to landing-style pages; same stack, copy and layout tuned for sites.",
        "guarantees": [
            "Vite + React scaffold with hero/sections-friendly structure",
            "Deploy-oriented files and proof stubs consistent with other web targets",
        ],
        "on_this_run": [
            "Still the same technical stack as vite_react — differentiation is planner emphasis and README.",
        ],
        "roadmap": [
            "Dedicated Astro/11ty track, CMS hooks, and edge deploy packs.",
        ],
    },
    "internal_admin_tool": {
        "id": "internal_admin_tool",
        "label": "Internal admin tool",
        "tagline": "Back-office workspace with data tables, forms, approval workflows, API contracts, and database schema.",
        "guarantees": [
            "Generates an admin/work-ops interface instead of a marketing site or generic full-stack shell.",
            "Includes browser-addressable admin routes for dashboard, records, forms, approvals, and settings.",
            "Adds API and database contract artifacts for records, form submissions, approval requests, and audit events.",
        ],
        "on_this_run": [
            "Root workspace remains a Vite + React preview so the existing preview gate can render it.",
            "Backend/database files are generated as contract-backed artifacts and validated by the final gates.",
        ],
        "roadmap": [
            "Provider-specific database provisioning and live migration execution when credentials are configured.",
        ],
    },
    "mobile_expo": {
        "id": "mobile_expo",
        "label": "Mobile app (Expo track)",
        "tagline": "Generates a gated Expo/React Native starter alongside the verified web preview so mobile work has concrete artifacts.",
        "guarantees": [
            "Adds a standalone expo-mobile/ project with Expo metadata, app entry, screens, navigation-ready structure, and run/build scripts.",
            "Documents App Store / Google Play packaging requirements instead of pretending submission is automatic.",
            "Runs through the Build Integrity Validator mobile profile before completion.",
        ],
        "on_this_run": [
            "Root workspace still includes a Vite preview bundle so existing browser preview gates remain compatible.",
            "Mobile source lives under expo-mobile/ and is validated as the requested target.",
            "Native store submission remains a guided artifact until signing credentials and EAS/App Store integrations are configured.",
        ],
        "roadmap": [
            "First-class EAS cloud build execution, signing credential management, TestFlight/Internal testing handoff, and store metadata validation.",
        ],
    },
    "api_backend": {
        "id": "api_backend",
        "label": "API & backend-first",
        "tagline": "Emphasizes FastAPI routes, OpenAPI-shaped sketches, and persistence; minimal UI.",
        "guarantees": [
            "Python API sketch with route modules and health-style patterns",
            "SQL / migration files when the goal implies data",
            "Minimal UI only when the request is truly API-first",
        ],
        "on_this_run": [
            "Frontend bundle is still generated (for Sandpack) but may stay minimal.",
        ],
        "roadmap": [
            "Optional “no frontend step” mode with API-only verification.",
            "gRPC / GraphQL / eventing packs.",
        ],
    },
    "agent_workflow": {
        "id": "agent_workflow",
        "label": "Agents & automation",
        "tagline": "Automation files and runtime proof through the single build path.",
        "guarantees": [
            "Automation source files under the workspace",
            "Same scaffold as web runs so proofs and preview still apply",
        ],
        "on_this_run": [
            "Automation is represented as files and proof events in the single runtime.",
        ],
        "roadmap": [
            "User-defined agent graphs, schedules, and external tool connectors.",
        ],
    },
}


def build_target_meta(target_id: str) -> Dict[str, Any]:
    tid = normalize_build_target(target_id)
    row = BUILD_TARGETS[tid]
    return {
        "id": row["id"],
        "label": row["label"],
        "tagline": row["tagline"],
        "guarantees": list(row["guarantees"]),
        "on_this_run": list(row["on_this_run"]),
        "roadmap": list(row["roadmap"]),
    }

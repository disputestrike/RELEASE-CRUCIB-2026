"""
goal_enricher.py — Enrich underspecified build goals before generation.

The remaining failure mode after the reliability layer is underspecified goals:
  "Build me an app" → agent doesn't know what to build → produces nothing meaningful

This module takes any user goal and enriches it with:
  1. Detected intent dimensions (from IntentClassifier)
  2. Build type classification (from intent_to_build_type)
  3. Stack-appropriate boilerplate instructions
  4. App name + brand tokens

The enriched goal is what gets passed to the GenerateAgent — not the raw user input.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def enrich_goal(goal: str) -> Dict[str, Any]:
    """
    Enrich a raw user goal into a complete build brief.
    Returns: { enriched_goal, app_name, brand_tokens, build_type, is_complex, timeout_seconds }
    """
    from backend.orchestration.intent_to_build_type import classify_goal
    from backend.orchestration.build_reliability import extract_app_name, generate_brand_tokens

    classified = classify_goal(goal)
    app_name = extract_app_name(goal)
    brand = generate_brand_tokens(app_name)

    build_type = classified["type"]
    stack = classified["stack"]
    label = classified["label"]

    # Add stack-specific boilerplate so agent never writes the wrong framework
    stack_instructions = _stack_instructions(stack, classified)

    # Detect missing critical requirements and fill them in
    extra_requirements = _infer_requirements(goal, classified)

    enriched = f"""# Build Goal: {app_name}
Type: {label}
Stack: {stack}

## User Request
{goal.strip()}

## Inferred Requirements
{extra_requirements}

## Technical Instructions
{stack_instructions}

## Branding
App name: {app_name}
Primary color: {brand['colors']['primary']}
Background: {brand['colors']['bg']}
Text: {brand['colors']['text']}
CSS variable to define: --color-primary: {brand['colors']['primary']};
"""

    return {
        "enriched_goal": enriched,
        "app_name": app_name,
        "brand_tokens": brand,
        "build_type": build_type,
        "label": label,
        "stack": stack,
        "is_complex": classified["is_complex"],
        "timeout_seconds": classified["timeout_seconds"],
        "build_command": classified["build_command"],
        "install_command": classified["install_command"],
    }


def _stack_instructions(stack: str, classified: Dict[str, Any]) -> str:
    """Return stack-specific build instructions that prevent common failures."""
    base = classified.get("entry_point", "src/main.tsx")

    if "fastapi" in stack:
        return f"""Frontend: React + Vite + TypeScript. Entry: {base}.
Backend: FastAPI (Python). Entry: backend/main.py.
Write frontend first (npm install + npm run build must pass).
Write backend/main.py with all routes, backend/requirements.txt with all deps.
Do NOT mix frontend and backend in the same directory.
tsconfig.json must have "strict": false and "noEmit": true.
"""
    elif "nextjs" in stack:
        return f"""Framework: Next.js 14 App Router. Entry: app/page.tsx.
Use "use client" directive for interactive components.
Write next.config.js, package.json, tailwind.config.ts.
Build command: npm run build (next build).
tsconfig.json: "strict": false.
"""
    elif "expo" in stack:
        return f"""Framework: Expo (React Native). Entry: App.tsx.
Write app.json, package.json with expo SDK 51+.
Use StyleSheet.create() for all styles (no inline style objects in lists).
Build command: npx expo export --platform web.
"""
    else:
        return f"""Framework: React + Vite + TypeScript. Entry: {base}.
tsconfig.json must have "strict": false and "noEmit": true, "skipLibCheck": true.
vite.config.ts must import and use @vitejs/plugin-react.
package.json must include react, react-dom, @vitejs/plugin-react, vite, typescript.
Build command: tsc && vite build (exit code 0 = success, dist/ folder created).
All imports must use relative paths without .ts/.tsx extensions.
Every imported component must exist as a file before running build.
"""


def _infer_requirements(goal: str, classified: Dict[str, Any]) -> str:
    """Infer missing requirements based on goal type and fill them in."""
    goal_lower = goal.lower()
    reqs = []
    build_type = classified["type"]

    # Universal requirements
    reqs.append("- Responsive design (works on mobile and desktop)")
    reqs.append("- Clean, professional UI with consistent spacing and typography")
    reqs.append(f"- Navigation between all main sections of the {classified['label']}")

    # Type-specific
    if build_type in ("enterprise_saas", "crm", "project_management"):
        if "auth" not in goal_lower and "login" not in goal_lower:
            reqs.append("- Auth UI: login form + dashboard (mock auth, no real backend calls needed)")
        if "sidebar" not in goal_lower:
            reqs.append("- Sidebar navigation with all main sections")

    if build_type == "ecommerce":
        if "cart" not in goal_lower:
            reqs.append("- Shopping cart with add/remove/quantity")
        if "checkout" not in goal_lower:
            reqs.append("- Checkout flow (3 steps: cart → shipping → confirmation)")

    if build_type == "analytics_dashboard":
        reqs.append("- At least 4 KPI cards with mock data")
        reqs.append("- One line or bar chart using recharts or Chart.js")

    if build_type == "realtime_chat":
        reqs.append("- Message list with timestamps and sender names")
        reqs.append("- Message input with send button")
        reqs.append("- Sidebar with channel/room list")

    if build_type in ("content_platform", "blog"):
        reqs.append("- Post list with title, excerpt, date, author")
        reqs.append("- Single post view with full content")
        if "search" not in goal_lower:
            reqs.append("- Search bar")

    # Quality gates
    reqs.append("- No TODO comments or placeholder implementations")
    reqs.append("- Every route in the nav must render real content (no empty pages)")

    return "\n".join(reqs)

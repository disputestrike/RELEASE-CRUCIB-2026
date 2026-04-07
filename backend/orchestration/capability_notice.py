"""
Advisory lines when a goal reads like a full platform spec beyond the fixed Auto-Runner scaffold.
Shown in plan API so users calibrate expectations (preview + proof still work on emitted code).

``build_target`` ties notices to the selected execution mode (broad platform, honest per-run scope).
"""
from __future__ import annotations

from typing import List, Optional

from .build_targets import build_target_meta, normalize_build_target


def _long_goal_line(tid: str) -> str:
    """Long-goal advisory — run still completes; wording matches execution target."""
    t = normalize_build_target(tid)
    if t == "next_app_router":
        return (
            "This goal is very long. The job still runs to completion: root Vite workspace (preview/verify), "
            "Python FastAPI and SQL sketches when implied, plus next-app-stub/ for App Router. "
            "Use continuation runs or edits to cover every line item in a huge spec."
        )
    if t == "static_site":
        return (
            "This goal is very long. The job still runs to completion: marketing-style Vite-oriented pages "
            "and verification gates. Extend with more runs or edits for full campaign/CMS depth."
        )
    if t == "api_backend":
        return (
            "This goal is very long. The job still runs to completion: Python FastAPI-style routes, "
            "SQL stubs, verification gates. Add integrations and scale patterns in-repo or follow-up runs."
        )
    if t == "agent_workflow":
        return (
            "This goal is very long. The job still runs to completion: workflow/agent sketches (files, docs, hooks). "
            "Host heavier runtimes in your stack if you need them beyond this pass."
        )
    return (
        "This goal is very long. The job still runs to completion: Vite + React (JS) app, Python FastAPI sketch, "
        "SQL migrations, and verification gates. Nothing here stops the run—use continuation runs or edits "
        "to cover every production extra in a huge spec."
    )


def _preview_workspace_hint(tid: str) -> str:
    t = normalize_build_target(tid)
    if t == "api_backend":
        return (
            "If preview looks empty or minimal, use Sync in the workspace header after the build completes. "
            "Sandpack may show a thin UI while the main output is the API sketch in the project tree."
        )
    return (
        "Live preview uses Sandpack on the root Vite bundle when a web UI is emitted (files under the job’s "
        "project folder). If preview is empty after the run, use Sync in the workspace header and Refresh "
        "in the Preview panel."
    )


def capability_notice_lines(goal: str, build_target: Optional[str] = None) -> List[str]:
    g = (goal or "").strip()
    tid = normalize_build_target(build_target)
    meta = build_target_meta(tid)
    lines: List[str] = []

    lines.append(
        "CrucibAI is aimed at apps, websites, backend services, automation, and agents — not a single narrow niche. "
        "Each Auto-Runner job picks an **execution target** for this run’s pipeline; approved jobs run to completion."
    )
    lines.append(f"This run: {meta['label']} — {meta['tagline']}")

    if not g:
        return lines[:14]

    gl = g.lower()

    if len(g) > 3500:
        lines.append(_long_goal_line(tid))

    triggers = [
        ("langgraph", "LangGraph / custom agent frameworks: extend in-repo or a follow-up run if you need full runtime wiring."),
        ("crewai", "CrewAI-style crews: optional sketches in this pass; customize step keys in your fork if needed."),
        ("pinecone", "Vector DBs (Pinecone/Weaviate): connect in your project or a follow-up run (not auto-wired by default)."),
        ("weaviate", "Vector DBs (Pinecone/Weaviate): connect in your project or a follow-up run (not auto-wired by default)."),
        ("testcontainers", "Testcontainers / k6: add to your CI or extend the DAG in a follow-up run."),
        ("playwright", "Playwright E2E: add as a project step or follow-up run (not a default DAG step)."),
        ("k6", "k6 / load testing: run in your CI or extend the pipeline when you need it."),
        ("phase_8", "Phase-gated reports (PHASE_X_REPORT.md): add as explicit steps if your process requires them."),
        ("omega build", "Very large “Omega”-style platform goals: this pass emits scaffold + proofs—grow with continuation runs."),
        ("self-improving", "Self-improving / scheduled optimization: implement in your deployment layer beyond the default runner."),
        ("slack", "Slack / email escalation: add webhooks or SMTP in your app (not pre-wired in the default runner)."),
        ("soc 2", "SOC 2 / audit packs: checklist sketches here—harden with your compliance process."),
    ]
    for needle, msg in triggers:
        if needle in gl and msg not in lines:
            lines.append(msg)

    if tid == "next_app_router":
        lines.append(
            "You chose the Next.js App Router track: the workspace still includes a full root Vite app for "
            "today’s preview/verify path, plus a next-app-stub/ folder to grow App Router code. A native Next-first DAG is on the roadmap."
        )

    if len(lines) > 2:
        lines.append(_preview_workspace_hint(tid))

    return lines[:16]

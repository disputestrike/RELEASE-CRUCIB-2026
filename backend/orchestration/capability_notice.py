"""
Advisory lines when a goal reads like a full platform spec beyond the fixed Auto-Runner scaffold.
Shown in plan API so users calibrate expectations (preview + proof still work on emitted code).

``build_target`` ties notices to the selected execution mode (broad platform, honest per-run scope).
"""
from __future__ import annotations

from typing import List, Optional

from .build_targets import build_target_meta, normalize_build_target


def _long_goal_line(tid: str) -> str:
    """Mega-spec honesty — wording matches selected execution target (not always 'Vite + React')."""
    t = normalize_build_target(tid)
    if t == "next_app_router":
        return (
            "This goal is very long. This run still emits a bounded bundle: root Vite workspace "
            "(today’s preview/verify path), Python FastAPI and SQL sketches when implied, plus "
            "next-app-stub/ for App Router—not every bullet in a mega-spec as its own subsystem."
        )
    if t == "static_site":
        return (
            "This goal is very long. This run emits a bounded marketing-style scaffold (Vite-oriented pages) "
            "and verification gates—not every campaign or CMS bullet as its own subsystem."
        )
    if t == "api_backend":
        return (
            "This goal is very long. This run emphasizes a bounded API sketch (Python FastAPI-style routes, "
            "SQL stubs, verification gates)—not every integration or scale pattern in your spec as a "
            "shipped subsystem."
        )
    if t == "agent_workflow":
        return (
            "This goal is very long. This run emits bounded workflow/agent sketches (files, docs, hooks) "
            "inside the DAG bundle—not a full custom runtime for every automation bullet in your spec."
        )
    return (
        "This goal is very long. This run emits a bounded bundle: Vite + React (JS) frontend sketch, "
        "Python FastAPI backend sketch, SQL migrations, and verification gates—not every bullet in a "
        "mega-spec as its own subsystem."
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
        "Each Auto-Runner job picks an **execution target** so you get clear guarantees for *this run* while we expand native tracks (Next-only pipelines, mobile, deeper automation, etc.)."
    )
    lines.append(f"This run: {meta['label']} — {meta['tagline']}")

    if not g:
        return lines[:14]

    gl = g.lower()

    if len(g) > 3500:
        lines.append(_long_goal_line(tid))

    triggers = [
        ("langgraph", "LangGraph / custom agent frameworks are not generated end-to-end by this pipeline."),
        ("crewai", "CrewAI-style crews are optional sketches; the DAG uses fixed step keys."),
        ("pinecone", "Vector DBs (Pinecone/Weaviate) are not wired automatically."),
        ("weaviate", "Vector DBs (Pinecone/Weaviate) are not wired automatically."),
        ("testcontainers", "Testcontainers / k6 load tests are not run in the default DAG."),
        ("playwright", "Playwright E2E is not a default DAG step (can be added later)."),
        ("k6", "k6 / load testing is not run in the default DAG."),
        ("phase_8", "Phase-gated reports (PHASE_X_REPORT.md) are not auto-emitted unless added as steps."),
        ("omega build", "Full “Omega” platform scope exceeds the template; expect scaffold + proofs, not full product."),
        ("self-improving", "Self-improving / weekly optimization jobs are not part of the default runner."),
        ("slack", "Slack/email human escalation is not wired in the default runner."),
        ("soc 2", "SOC 2 / audit packs are checklist sketches only unless you extend the pipeline."),
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

"""Public community/template trust routes.

This router is intentionally static for launch: templates and case studies are
curated by the CrucibAI team until moderation workflows are staffed and audited.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

COMMUNITY_TEMPLATES = [
    {
        "id": "dashboard",
        "name": "Dashboard",
        "description": "Sidebar, metrics cards, proof-ready preview, and publish path.",
        "prompt": "Create a dashboard with a sidebar, stat cards, and a chart area. React and Tailwind.",
        "tags": ["saas", "analytics"],
        "difficulty": "starter",
        "proof_score": 100,
        "moderation_status": "approved",
        "remix_endpoint": "/api/community/templates/dashboard/remix-plan",
    },
    {
        "id": "saas-shell",
        "name": "SaaS shell",
        "description": "Auth shell, settings area, pricing surface, and deploy-ready structure.",
        "prompt": "Create a SaaS app shell with top nav, user menu, and settings page. React and Tailwind.",
        "tags": ["saas", "auth"],
        "difficulty": "intermediate",
        "proof_score": 100,
        "moderation_status": "approved",
        "remix_endpoint": "/api/community/templates/saas-shell/remix-plan",
    },
    {
        "id": "crm",
        "name": "CRM dashboard",
        "description": "Contacts, pipeline board, activity feed, and clean data states.",
        "prompt": "Create a CRM dashboard with contacts list, deals pipeline, and activity feed. React and Tailwind.",
        "tags": ["crm", "business"],
        "difficulty": "intermediate",
        "proof_score": 100,
        "moderation_status": "approved",
        "remix_endpoint": "/api/community/templates/crm/remix-plan",
    },
    {
        "id": "workflow-agent",
        "name": "Workflow agent",
        "description": "Automation starter that calls the same build AI inside a workflow.",
        "prompt": "Create an automation dashboard that runs an agent step, reviews output, and sends a summary.",
        "tags": ["automation", "agents"],
        "difficulty": "advanced",
        "proof_score": 100,
        "moderation_status": "approved",
        "remix_endpoint": "/api/community/templates/workflow-agent/remix-plan",
    },
]


CASE_STUDIES = [
    {
        "id": "live-golden-path",
        "title": "Live golden path proof",
        "summary": "Railway production run completed prompt, plan, build, preview, proof, publish, and public URL.",
        "proof": "proof/live_production_golden_path/PASS_FAIL.md",
        "status": "verified",
    },
    {
        "id": "repeatability-v1",
        "title": "50-prompt repeatability benchmark",
        "summary": "Deterministic benchmark suite covers 50 app categories with a 90% release threshold.",
        "proof": "proof/benchmarks/repeatability_v1/PASS_FAIL.md",
        "status": "verified",
    },
    {
        "id": "full-systems-gate",
        "title": "Full systems release gate",
        "summary": "Backend, frontend, Railway, public trust preflight, and live golden path run as required gates.",
        "proof": "proof/full_systems/PASS_FAIL.md",
        "status": "verified",
    },
]


def create_community_router() -> APIRouter:
    router = APIRouter(prefix="/api/community", tags=["community"])

    @router.get("/templates")
    async def community_templates():
        return {
            "status": "ready",
            "moderation": "curated_pre_publish",
            "templates": COMMUNITY_TEMPLATES,
        }

    @router.get("/templates/{template_id}/remix-plan")
    async def community_template_remix_plan(template_id: str):
        template = next(
            (item for item in COMMUNITY_TEMPLATES if item["id"] == template_id), None
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return {
            "template_id": template_id,
            "name": template["name"],
            "prompt": f"Remix template '{template['name']}': {template['prompt']}",
            "tags": template["tags"],
            "difficulty": template["difficulty"],
            "proof_score": template["proof_score"],
            "moderation_status": template["moderation_status"],
            "route": "/app/workspace",
        }

    @router.get("/case-studies")
    async def community_case_studies():
        return {"status": "ready", "case_studies": CASE_STUDIES}

    @router.get("/moderation-policy")
    async def community_moderation_policy():
        return {
            "status": "ready",
            "policy": "Curated templates only for launch; public submissions require moderation before listing.",
            "checks": [
                "owner permission",
                "secret scan",
                "security proof",
                "preview proof",
                "copyright and abuse review",
            ],
        }

    return router

from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


CapabilityStatus = str


@dataclass(frozen=True)
class CapabilityEntry:
    name: str
    type: str
    status: CapabilityStatus
    description: str
    required_config: List[str] = field(default_factory=list)
    supported_actions: List[str] = field(default_factory=list)
    artifact_outputs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class PreviewType:
    name: str
    status: CapabilityStatus
    mime_types: List[str]
    artifact_outputs: List[str]
    renderer: str
    unsupported_reason: Optional[str] = None


@dataclass(frozen=True)
class WorkflowTemplate:
    key: str
    name: str
    status: CapabilityStatus
    description: str
    required_capabilities: List[str]
    required_connectors: List[str]
    steps: List[Dict[str, Any]]
    schedule: Dict[str, Any]


@dataclass(frozen=True)
class ComputerUseAction:
    action: str
    status: CapabilityStatus
    required_fields: List[str]
    audit_fields: List[str]
    notes: List[str] = field(default_factory=list)


def _configured(name: str) -> bool:
    return bool(os.environ.get(name))


def _status_for_env(env_name: str) -> CapabilityStatus:
    return "available" if _configured(env_name) else "requires_config"


def _google_oauth_status() -> CapabilityStatus:
    return "available" if (_configured("GOOGLE_CLIENT_ID") and _configured("GOOGLE_CLIENT_SECRET")) else "requires_config"


def _notion_status() -> CapabilityStatus:
    return "available" if _configured("NOTION_API_KEY") else "requires_config"


def _computer_use_status() -> CapabilityStatus:
    # Docker installs Playwright Chromium for production. If a deployment strips
    # browser dependencies, the run endpoint still reports the exact failure.
    return "available"


def build_capability_registry() -> Dict[str, Any]:
    """Return the canonical honest capability registry for product surfaces.

    This registry intentionally describes foundations and readiness. It does not
    execute external integrations and it does not mark future connectors as live.
    """

    entries = [
        CapabilityEntry(
            name="daily_work_automation_foundation",
            type="automation",
            status="available",
            description="Multi-step workflow definitions, action logging, retries, persisted run summaries, and manual/scheduled run contracts.",
            supported_actions=["http", "email", "slack", "run_agent", "approval"],
            artifact_outputs=["run_summary", "step_log", "error_report"],
            notes=[
                "HTTP actions are generic connector hooks, not native SaaS integrations.",
                "Email and Slack actions require provider credentials before they can send.",
            ],
        ),
        CapabilityEntry(
            name="http_connector",
            type="connector",
            status="available",
            description="Generic outbound HTTP action for user-owned endpoints and future connector adapters.",
            supported_actions=["GET", "POST", "PUT", "PATCH", "DELETE"],
            artifact_outputs=["response_summary", "status_code"],
        ),
        CapabilityEntry(
            name="email_connector",
            type="connector",
            status="available" if (_configured("RESEND_API_KEY") or _configured("SENDGRID_API_KEY")) else "requires_config",
            description="Email action adapter using Resend or SendGrid when configured.",
            required_config=["RESEND_API_KEY or SENDGRID_API_KEY"],
            supported_actions=["send_email"],
            artifact_outputs=["delivery_status"],
        ),
        CapabilityEntry(
            name="slack_connector",
            type="connector",
            status="available" if _configured("SLACK_BOT_TOKEN") else "requires_config",
            description="Slack action adapter using incoming webhook or bot token when configured.",
            required_config=["SLACK_BOT_TOKEN or per-action webhook_url"],
            supported_actions=["post_message"],
            artifact_outputs=["delivery_status"],
        ),
        CapabilityEntry(
            name="gmail_connector",
            type="connector",
            status=_google_oauth_status(),
            description="Gmail OAuth connector with encrypted credential storage, validation, and inbox workflow contracts.",
            required_config=["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "user OAuth consent"],
            supported_actions=["oauth_connect", "validate_connection", "read_messages", "draft_reply", "summarize_threads"],
            artifact_outputs=["message_digest"],
            notes=["Use /api/connectors/google/oauth-url?connector=gmail to start OAuth. Actions require a connected user credential."],
        ),
        CapabilityEntry(
            name="calendar_connector",
            type="connector",
            status=_google_oauth_status(),
            description="Calendar OAuth connector with encrypted credential storage, validation, and schedule workflow contracts.",
            required_config=["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "user OAuth consent"],
            supported_actions=["oauth_connect", "validate_connection", "list_events", "summarize_schedule"],
            artifact_outputs=["calendar_digest"],
            notes=["Use /api/connectors/google/oauth-url?connector=calendar to start OAuth. Chief-of-staff execution requires a connected credential."],
        ),
        CapabilityEntry(
            name="notion_connector",
            type="connector",
            status=_notion_status(),
            description="Notion connector with encrypted integration-token storage and validation.",
            required_config=["NOTION_API_KEY or user integration token", "workspace authorization"],
            supported_actions=["save_token", "validate_connection", "read_pages", "read_databases", "read_tasks"],
            artifact_outputs=["task_digest", "page_summary"],
            notes=["Use /api/connectors/notion/credentials to store a user token, then /api/connectors/notion/validate."],
        ),
        CapabilityEntry(
            name="computer_use_task_layer",
            type="computer_use",
            status=_computer_use_status(),
            description="Governed Playwright runner for safe browser actions with policy checks, status, screenshots, and audit fields.",
            supported_actions=["see", "click", "type", "wait", "screenshot", "navigate"],
            artifact_outputs=["audit_log", "screenshot", "error_capture"],
            notes=["Use /api/capabilities/computer-use/queue/run. Interaction actions require explicit allow_interaction policy."],
        ),
        CapabilityEntry(
            name="rich_preview_support",
            type="preview",
            status="available",
            description="Preview capability map for apps, docs, PDFs, slides, structured files, and generated assets.",
            supported_actions=["resolve_preview_type", "report_unsupported_state"],
            artifact_outputs=["preview_descriptor"],
        ),
        CapabilityEntry(
            name="image_asset_generation_hook",
            type="asset_generation",
            status=_status_for_env("TOGETHER_API_KEY"),
            description="Provider-backed image/asset generation with request persistence and artifact metadata.",
            required_config=["TOGETHER_API_KEY"],
            supported_actions=["validate_asset_request", "generate_image", "store_artifact_metadata"],
            artifact_outputs=["image_url", "data_url", "asset_metadata"],
            notes=["Use /api/capabilities/assets/requests/generate. No fake image URL is returned when provider credentials are missing."],
        ),
        CapabilityEntry(
            name="nano_banana_asset_provider",
            type="asset_generation",
            status="requires_config",
            description="Configurable secondary image-generation provider slot.",
            required_config=["NANO_BANANA_ENDPOINT", "NANO_BANANA_API_KEY", "usage policy"],
            supported_actions=["generate_image"],
            artifact_outputs=["image", "asset_metadata"],
        ),
        CapabilityEntry(
            name="skill_tool_registry",
            type="registry",
            status="available",
            description="Machine-readable registry for skills, tools, connectors, statuses, config, actions, and artifact outputs.",
            supported_actions=["list_capabilities", "filter_by_status", "validate_workflow", "list_skill_md", "reload_skill_md"],
            artifact_outputs=["capability_registry", "skill_md_registry"],
            notes=["File-backed Skill MD loader is available at /api/skills/md/list and /api/skills/md/reload."],
        ),
        CapabilityEntry(
            name="dynamic_skill_agent",
            type="skill",
            status="available",
            description="Creates reusable instruction-skill contracts when a user asks for a capability not already covered.",
            supported_actions=["resolve_gap", "generate_skill_contract", "persist_user_skill", "activate_user_skill"],
            artifact_outputs=["skill_md", "user_skill", "execution_contract"],
            notes=[
                "Dynamic skills are instruction and orchestration contracts, not fake executable integrations.",
                "Use /api/skills/generate with auto_create=true to persist a generated skill.",
            ],
        ),
        CapabilityEntry(
            name="knowledge_ingestion",
            type="knowledge",
            status="available",
            description="Persistent knowledge ingestion for document text, URL records, base64 text files, and PDF text extraction when pypdf is installed.",
            required_config=["pypdf for PDF text extraction"],
            supported_actions=["ingest_document", "ingest_url", "chunk_text", "search_knowledge", "delete_source"],
            artifact_outputs=["knowledge_source", "knowledge_chunks", "search_results"],
            notes=["Binary PDF extraction reports a warning instead of pretending success when the extractor is unavailable."],
        ),
        CapabilityEntry(
            name="scheduled_task_foundation",
            type="schedule",
            status="available",
            description="Schedule definition model for owner, next run, last result, and enabled state.",
            supported_actions=["cron", "run_at", "manual"],
            artifact_outputs=["schedule_descriptor", "last_run_result"],
            notes=["Requires worker deployment for automatic execution in a given environment."],
        ),
    ]

    return {
        "version": "2026-04-25.wave2",
        "status_values": ["available", "disabled", "requires_config"],
        "capabilities": [asdict(e) for e in entries],
        "summary": {
            "available": sum(1 for e in entries if e.status == "available"),
            "requires_config": sum(1 for e in entries if e.status == "requires_config"),
            "disabled": sum(1 for e in entries if e.status == "disabled"),
            "coming_soon": sum(1 for e in entries if e.status == "coming_soon"),
        },
    }


def list_preview_types() -> List[Dict[str, Any]]:
    previews = [
        PreviewType(
            name="app_site",
            status="available",
            mime_types=["text/html", "application/javascript", "text/css"],
            artifact_outputs=["iframe_preview", "sandpack_preview", "dev_server_url"],
            renderer="PreviewPanel",
        ),
        PreviewType(
            name="document",
            status="available",
            mime_types=["text/plain", "text/markdown", "application/json"],
            artifact_outputs=["text_preview", "markdown_preview", "json_preview"],
            renderer="WorkspaceFileViewer",
        ),
        PreviewType(
            name="pdf",
            status="available",
            mime_types=["application/pdf"],
            artifact_outputs=["download_url", "browser_pdf_preview"],
            renderer="browser_native_pdf",
        ),
        PreviewType(
            name="slides",
            status="requires_config",
            mime_types=["application/vnd.openxmlformats-officedocument.presentationml.presentation"],
            artifact_outputs=["download_url"],
            renderer="slides_renderer",
            unsupported_reason="Inline slide preview requires a renderer/converter in the deployment environment.",
        ),
        PreviewType(
            name="structured_file",
            status="available",
            mime_types=["application/json", "text/csv", "application/x-yaml"],
            artifact_outputs=["structured_text_preview"],
            renderer="WorkspaceFileViewer",
        ),
        PreviewType(
            name="generated_asset",
            status="requires_config",
            mime_types=["image/png", "image/jpeg", "image/webp", "image/svg+xml"],
            artifact_outputs=["image_preview", "asset_metadata"],
            renderer="WorkspaceFileViewer",
            unsupported_reason="Asset generation requires a configured provider before new assets can be created.",
        ),
    ]
    return [asdict(p) for p in previews]


def list_computer_use_actions() -> List[Dict[str, Any]]:
    actions = [
        ComputerUseAction(
            action="see",
            status="available",
            required_fields=["target"],
            audit_fields=["action_id", "target", "screenshot_ref", "timestamp", "status"],
        ),
        ComputerUseAction(
            action="click",
            status="available",
            required_fields=["target", "selector_or_coordinates"],
            audit_fields=["action_id", "target", "selector_or_coordinates", "timestamp", "status", "error"],
            notes=["Requires allow_interaction policy on the run request."],
        ),
        ComputerUseAction(
            action="type",
            status="available",
            required_fields=["target", "text"],
            audit_fields=["action_id", "target", "redacted_text_summary", "timestamp", "status", "error"],
            notes=["Requires allow_interaction policy and refuses likely password/secret fields."],
        ),
        ComputerUseAction(
            action="screenshot",
            status="available",
            required_fields=["target"],
            audit_fields=["action_id", "target", "artifact_ref", "timestamp", "status", "error"],
        ),
        ComputerUseAction(
            action="navigate",
            status="available",
            required_fields=["target"],
            audit_fields=["action_id", "target", "url", "timestamp", "status", "error"],
        ),
        ComputerUseAction(
            action="wait",
            status="available",
            required_fields=["milliseconds"],
            audit_fields=["action_id", "milliseconds", "timestamp", "status"],
        ),
    ]
    return [asdict(a) for a in actions]


def list_workflow_templates() -> List[Dict[str, Any]]:
    templates = [
        WorkflowTemplate(
            key="chief_of_staff_morning_brief",
            name="Chief-of-Staff Morning Brief",
            status="requires_config",
            description="Scan messages, tasks, and calendar-style sources, summarize priorities, and produce a morning brief.",
            required_capabilities=["daily_work_automation_foundation", "scheduled_task_foundation"],
            required_connectors=["gmail_connector", "calendar_connector", "notion_connector"],
            schedule={"type": "cron", "cron_expression": "0 8 * * 1-5", "timezone": "user_default", "enabled": False},
            steps=[
                {"key": "scan_messages", "type": "connector", "connector": "gmail_connector", "status": "requires_config"},
                {"key": "scan_tasks", "type": "connector", "connector": "notion_connector", "status": "requires_config"},
                {"key": "scan_calendar", "type": "connector", "connector": "calendar_connector", "status": "requires_config"},
                {"key": "summarize_priorities", "type": "run_agent", "agent_name": "Chief of Staff Agent", "status": "available"},
                {"key": "produce_brief", "type": "artifact", "artifact_type": "morning_brief", "status": "available"},
            ],
        )
    ]
    return [asdict(t) for t in templates]


def list_asset_providers() -> List[Dict[str, Any]]:
    return [
        {
            "name": "together_ai",
            "type": "image_generation",
            "status": _status_for_env("TOGETHER_API_KEY"),
            "required_config": ["TOGETHER_API_KEY"],
            "supported_actions": ["generate_image"],
            "artifact_outputs": ["image_url", "image_file", "metadata"],
        },
        {
            "name": "nano_banana",
            "type": "image_generation",
            "status": "available" if (_configured("NANO_BANANA_ENDPOINT") and _configured("NANO_BANANA_API_KEY")) else "requires_config",
            "required_config": ["NANO_BANANA_ENDPOINT", "NANO_BANANA_API_KEY"],
            "supported_actions": ["generate_image"],
            "artifact_outputs": ["image_url", "image_file", "metadata"],
        },
    ]


def get_capability_by_name(name: str) -> Optional[Dict[str, Any]]:
    registry = build_capability_registry()
    for cap in registry["capabilities"]:
        if cap["name"] == name:
            return deepcopy(cap)
    return None


def validate_workflow_definition(workflow: Dict[str, Any]) -> Dict[str, Any]:
    actions = workflow.get("actions") or workflow.get("steps") or []
    registry = build_capability_registry()
    capability_status = {c["name"]: c["status"] for c in registry["capabilities"]}
    known_action_types = {"http", "email", "slack", "run_agent", "approval"}
    normalized_steps = []
    blockers = []
    for idx, raw in enumerate(actions):
        step = raw if isinstance(raw, dict) else {}
        action_type = str(step.get("type") or "unknown").lower()
        status = "available" if action_type in known_action_types else "disabled"
        if action_type == "email" and capability_status.get("email_connector") != "available":
            status = "requires_config"
        if action_type == "slack" and capability_status.get("slack_connector") != "available":
            status = "requires_config"
        if status != "available":
            blockers.append({"step_index": idx, "type": action_type, "status": status})
        normalized_steps.append(
            {
                "index": idx,
                "type": action_type,
                "status": status,
                "approval_required": bool(step.get("approval_required")),
                "config_keys": sorted(list((step.get("config") or {}).keys())),
            }
        )
    return {
        "can_execute_now": not blockers,
        "steps": normalized_steps,
        "blockers": blockers,
        "result_contract": {
            "step_status": ["pending", "running", "success", "failed", "waiting_approval"],
            "persisted_results": ["output_summary", "log_lines", "error_message", "duration_seconds"],
        },
    }

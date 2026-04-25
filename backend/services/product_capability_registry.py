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


def _status_for_env(env_name: str, *, coming_soon: bool = False) -> CapabilityStatus:
    if coming_soon:
        return "coming_soon"
    return "available" if _configured(env_name) else "requires_config"


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
            status="coming_soon",
            description="Future Gmail connector for inbox-driven workflows.",
            required_config=["Google OAuth client", "tenant consent", "scoped credential store"],
            supported_actions=["read_messages", "draft_reply"],
            artifact_outputs=["message_digest"],
            notes=["Not live. Do not show as executable until OAuth and credential storage exist."],
        ),
        CapabilityEntry(
            name="calendar_connector",
            type="connector",
            status="coming_soon",
            description="Future calendar connector for schedule-aware briefs and automations.",
            required_config=["Calendar OAuth client", "tenant consent", "scoped credential store"],
            supported_actions=["list_events", "summarize_schedule"],
            artifact_outputs=["calendar_digest"],
            notes=["Not live. Chief-of-staff template depends on this before real execution."],
        ),
        CapabilityEntry(
            name="notion_connector",
            type="connector",
            status="coming_soon",
            description="Future Notion connector for tasks, docs, and project context.",
            required_config=["Notion OAuth or integration token", "workspace authorization"],
            supported_actions=["read_pages", "read_tasks"],
            artifact_outputs=["task_digest", "page_summary"],
        ),
        CapabilityEntry(
            name="computer_use_task_layer",
            type="computer_use",
            status="disabled",
            description="Safe see/click/type action queue contract with status and audit fields; execution is intentionally disabled until a governed runner is attached.",
            supported_actions=["see", "click", "type", "wait", "screenshot", "navigate"],
            artifact_outputs=["audit_log", "screenshot", "error_capture"],
            notes=["Action model only. Real computer-use execution is not claimed live."],
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
            description="Provider abstraction for future image/asset generation with artifact metadata.",
            required_config=["TOGETHER_API_KEY"],
            supported_actions=["create_asset_request", "store_artifact_metadata"],
            artifact_outputs=["image", "asset_metadata"],
            notes=["No fake image URL is returned by this registry."],
        ),
        CapabilityEntry(
            name="nano_banana_asset_provider",
            type="asset_generation",
            status="coming_soon",
            description="Reserved provider slot for Nano Banana-style image generation.",
            required_config=["provider endpoint", "provider API key", "usage policy"],
            supported_actions=["generate_image"],
            artifact_outputs=["image", "asset_metadata"],
        ),
        CapabilityEntry(
            name="skill_tool_registry",
            type="registry",
            status="available",
            description="Machine-readable registry for skills, tools, connectors, statuses, config, actions, and artifact outputs.",
            supported_actions=["list_capabilities", "filter_by_status", "validate_workflow"],
            artifact_outputs=["capability_registry"],
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
        "status_values": ["available", "disabled", "requires_config", "coming_soon"],
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
            status="disabled",
            required_fields=["target"],
            audit_fields=["action_id", "target", "screenshot_ref", "timestamp", "status"],
        ),
        ComputerUseAction(
            action="click",
            status="disabled",
            required_fields=["target", "selector_or_coordinates"],
            audit_fields=["action_id", "target", "selector_or_coordinates", "timestamp", "status", "error"],
        ),
        ComputerUseAction(
            action="type",
            status="disabled",
            required_fields=["target", "text"],
            audit_fields=["action_id", "target", "redacted_text_summary", "timestamp", "status", "error"],
        ),
        ComputerUseAction(
            action="screenshot",
            status="disabled",
            required_fields=["target"],
            audit_fields=["action_id", "target", "artifact_ref", "timestamp", "status", "error"],
        ),
        ComputerUseAction(
            action="wait",
            status="disabled",
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
            "status": "coming_soon",
            "required_config": ["provider endpoint", "provider API key"],
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

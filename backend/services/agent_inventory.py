from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List

from agent_dag import AGENT_DAG

KEYWORD_DOMAIN_RULES = [
    ("Core Builders", ["planner", "clarifier", "selector", "generation", "database", "api integration", "design agent", "layout agent", "image generation", "video generation"]),
    ("Infrastructure", ["docker", "kubernetes", "ci/cd", "monitor", "environment", "secret", "schema validator", "database optimization", "railway", "deploy", "terraform", "nginx", "caching"]),
    ("Security", ["security", "oauth", "auth", "csrf", "penetration", "soc2", "hipaa", "audit"]),
    ("Testing", ["test", "qa", "verification", "validator", "proof", "repair", "recovery"]),
    ("Design/UX", ["ux", "ui", "design", "layout", "copy", "brand", "accessibility", "wcag"]),
    ("3D & Graphics", ["3d", "webgl", "shader", "ar/vr", "animation", "physics"]),
    ("ML/AI", ["ml", "model", "training", "inference", "eval", "prompt"]),
    ("Blockchain", ["blockchain", "web3", "defi", "smart contract"]),
    ("IoT", ["iot", "sensor", "firmware", "edge", "device"]),
    ("Enterprise", ["multi-tenant", "rbac", "sso", "enterprise", "billing", "commerce"]),
    ("Real-Time", ["websocket", "real-time", "stream", "realtime"]),
    ("Data/Analytics", ["analytics", "data", "etl", "report", "excel", "pdf", "export"]),
]


def classify_agent(agent_name: str) -> str:
    name = agent_name.lower()
    for domain, keywords in KEYWORD_DOMAIN_RULES:
        if any(keyword in name for keyword in keywords):
            return domain
    return "Other"


def infer_status(agent_name: str, config: Dict[str, Any]) -> str:
    deps = config.get("depends_on") or []
    prompt = str(config.get("system_prompt") or "")
    has_realish = len(prompt.strip()) > 80
    domain = classify_agent(agent_name)
    if domain == "Core Builders" and has_realish:
        return "PROD"
    if has_realish and len(deps) <= 4:
        return "ADV"
    return "SPEC"


def build_inventory() -> List[Dict[str, Any]]:
    inventory: List[Dict[str, Any]] = []
    for name, config in AGENT_DAG.items():
        domain = classify_agent(name)
        status = infer_status(name, config)
        inventory.append(
            {
                "name": name,
                "domain": domain,
                "status": status,
                "dependency_count": len(config.get("depends_on") or []),
                "dependencies": list(config.get("depends_on") or []),
                "has_prompt": bool(str(config.get("system_prompt") or "").strip()),
                "prompt_length": len(str(config.get("system_prompt") or "")),
                "description": str(config.get("description") or ""),
            }
        )
    inventory.sort(key=lambda row: (row["domain"], row["name"]))
    return inventory


def build_domain_summary(inventory: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, Counter] = {}
    for row in inventory:
        domain = row["domain"]
        buckets.setdefault(domain, Counter())
        buckets[domain]["count"] += 1
        buckets[domain][row["status"].lower()] += 1
        if row["has_prompt"]:
            buckets[domain]["with_prompt"] += 1
    summary = []
    for domain in sorted(buckets):
        c = buckets[domain]
        count = c["count"]
        summary.append(
            {
                "domain": domain,
                "count": count,
                "prod": c["prod"],
                "adv": c["adv"],
                "spec": c["spec"],
                "with_prompt": c["with_prompt"],
                "prompt_coverage": round((c["with_prompt"] / count * 100.0), 1) if count else 0.0,
            }
        )
    return summary


def export_inventory_markdown() -> str:
    inventory = build_inventory()
    summary = build_domain_summary(inventory)
    lines = []
    lines.append("# Agent Inventory (Live Audit)\n")
    lines.append(f"**Total agents discovered in AGENT_DAG:** {len(inventory)}\n")
    lines.append("This is a generated, engineering-first inventory based on the current codebase, not marketing copy.\n")
    lines.append("## Domain Summary\n")
    lines.append("| Domain | Count | PROD | ADV | SPEC | Prompt Coverage |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for row in summary:
        lines.append(f"| {row['domain']} | {row['count']} | {row['prod']} | {row['adv']} | {row['spec']} | {row['prompt_coverage']}% |")
    lines.append("\n## Full Inventory\n")
    lines.append("| Agent | Domain | Status | Prompt | Dependencies |")
    lines.append("|---|---|---|---:|---:|")
    for row in inventory:
        lines.append(f"| {row['name']} | {row['domain']} | {row['status']} | {row['prompt_length']} | {row['dependency_count']} |")
    return "\n".join(lines) + "\n"

"""Parse user goals into an explicit multi-stack generation contract."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List, Tuple

_CATEGORY_PATTERNS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "frontend_frameworks": {
        "react": ("react",),
        "vue": ("vue",),
        "angular": ("angular",),
        "svelte": ("svelte",),
        "next.js": ("next.js", "nextjs", "app router"),
        "nuxt": ("nuxt",),
        "remix": ("remix",),
        "astro": ("astro",),
        "solidjs": ("solidjs", "solid.js", "solid"),
        "qwik": ("qwik",),
        "htmx": ("htmx",),
        "alpine.js": ("alpine.js", "alpinejs", "alpine"),
    },
    "frontend_languages": {
        "typescript": ("typescript", "ts "),
        "javascript": ("javascript", "js "),
        "html": ("html",),
        "css": ("css",),
        "tailwind": ("tailwind",),
    },
    "platforms": {
        "mobile": (
            "mobile app",
            "native app",
            "react native",
            "react-native",
            "expo",
            "ios app",
            "android app",
            "app store",
            "google play",
            "testflight",
            "eas build",
        ),
        "web": ("web app", "website", "browser app", "spa"),
    },
    "backend_frameworks": {
        "express": ("express",),
        "fastify": ("fastify",),
        "nestjs": ("nestjs", "nest.js"),
        "hapi": ("hapi",),
        "fastapi": ("fastapi",),
        "flask": ("flask",),
        "django": ("django",),
        "spring boot": ("spring boot",),
        "quarkus": ("quarkus",),
        "gin": ("gin",),
        "echo": ("echo",),
        "chi": (" chi ", " chi,", " chi.", " chi/"),
        "actix": ("actix",),
        "rocket": ("rocket",),
        "axum": ("axum",),
        "asp.net core": ("asp.net core", "aspnet core", ".net", "c#"),
        "laravel": ("laravel",),
        "symfony": ("symfony",),
        "rails": ("rails",),
        "phoenix": ("phoenix",),
    },
    "backend_languages": {
        "node.js": ("node", "node.js"),
        "python": ("python", "fastapi", "django", "flask"),
        "java": ("java", "spring", "quarkus"),
        "go": (" golang", "go ", "go,", "go.", "gin", "echo", "chi"),
        "rust": ("rust", "actix", "rocket", "axum"),
        "c#": ("c#", ".net", "asp.net"),
        "php": ("php", "laravel", "symfony"),
        "ruby": ("ruby", "rails", "sinatra"),
        "elixir": ("elixir", "phoenix"),
    },
    "sql_databases": {
        "postgresql": ("postgres", "postgresql", "pgvector", "supabase"),
        "mysql": ("mysql", "mariadb"),
        "sqlite": ("sqlite",),
        "sql server": ("sql server", "mssql"),
        "oracle": ("oracle",),
        "cockroachdb": ("cockroach", "cockroachdb"),
    },
    "nosql_databases": {
        "mongodb": ("mongodb", "mongo"),
        "firebase": ("firebase", "firestore"),
        "dynamodb": ("dynamodb",),
        "cassandra": ("cassandra",),
        "couchdb": ("couchdb",),
    },
    "graph_databases": {
        "neo4j": ("neo4j",),
    },
    "cache": {
        "redis": ("redis", "valkey", "bullmq"),
        "memcached": ("memcached",),
    },
    "queues": {
        "rabbitmq": ("rabbitmq",),
        "kafka": ("kafka",),
        "aws sqs": ("sqs", "aws sqs"),
        "bullmq": ("bullmq",),
        "celery": ("celery",),
        "pulsar": ("pulsar",),
        "nats": ("nats",),
    },
    "search": {
        "elasticsearch": ("elasticsearch", "elastic"),
        "meilisearch": ("meilisearch",),
        "typesense": ("typesense",),
        "algolia": ("algolia",),
        "opensearch": ("opensearch",),
    },
    "time_series": {
        "prometheus": ("prometheus",),
        "influxdb": ("influxdb", "influx"),
        "timescaledb": ("timescaledb",),
        "questdb": ("questdb",),
    },
    "warehouses": {
        "bigquery": ("bigquery",),
        "snowflake": ("snowflake",),
        "redshift": ("redshift",),
        "duckdb": ("duckdb",),
        "druid": ("druid",),
    },
    "vector_databases": {
        "pinecone": ("pinecone",),
        "weaviate": ("weaviate",),
        "milvus": ("milvus",),
        "chroma": ("chroma",),
        "pgvector": ("pgvector",),
        "qdrant": ("qdrant",),
    },
    "storage": {
        "aws s3": ("s3", "aws s3"),
        "gcs": ("google cloud storage", "gcs"),
        "azure blob": ("azure blob", "blob storage"),
        "minio": ("minio",),
        "supabase storage": ("supabase storage",),
        "cloudinary": ("cloudinary",),
    },
    "realtime": {
        "websockets": ("websocket", "websockets"),
        "socket.io": ("socket.io", "socketio"),
        "automerge": ("automerge", "crdt"),
        "liveblocks": ("liveblocks",),
    },
    "auth": {
        "auth0": ("auth0",),
        "okta": ("okta",),
        "supabase auth": ("supabase auth",),
        "clerk": ("clerk",),
        "firebase auth": ("firebase auth",),
        "cognito": ("cognito",),
        "oauth2": ("oauth2", "oauth"),
        "jwt": ("jwt",),
    },
    "payments": {
        "paypal": ("paypal",),
        "lemonsqueezy": ("lemonsqueezy", "lemon squeezy"),
        "paddle": ("paddle",),
        "razorpay": ("razorpay",),
    },
    "notifications": {
        "sendgrid": ("sendgrid",),
        "mailgun": ("mailgun",),
        "resend": ("resend",),
        "twilio": ("twilio",),
        "postmark": ("postmark",),
        "ses": ("aws ses", "ses "),
    },
    "monitoring": {
        "elk": ("elk", "elasticsearch/logstash/kibana", "logstash", "kibana"),
        "datadog": ("datadog",),
        "new relic": ("new relic",),
        "sentry": ("sentry",),
        "grafana/loki": ("grafana", "loki"),
        "splunk": ("splunk",),
    },
    "orms": {
        "alembic": ("alembic",),
        "sequelize": ("sequelize",),
        "prisma": ("prisma",),
        "typeorm": ("typeorm",),
        "sqlalchemy": ("sqlalchemy",),
        "django orm": ("django orm",),
        "hibernate": ("hibernate",),
        "entity framework": ("entity framework",),
    },
    "deployment": {
        "docker": ("docker",),
        "docker compose": ("docker compose", "docker-compose"),
        "kubernetes": ("kubernetes", "k8s"),
        "github actions": ("github actions",),
        "gitlab ci": ("gitlab ci",),
        "jenkins": ("jenkins",),
        "terraform": ("terraform",),
        "cloudformation": ("cloudformation",),
    },
    "testing": {
        "jest": ("jest",),
        "vitest": ("vitest",),
        "mocha": ("mocha",),
        "pytest": ("pytest",),
        "unittest": ("unittest",),
        "cypress": ("cypress",),
        "playwright": ("playwright",),
        "puppeteer": ("puppeteer",),
    },
    "apis": {
        "graphql": ("graphql",),
        "openapi": ("openapi", "swagger"),
        "rest": (" rest", "rest ", "http methods"),
        "grpc": ("grpc", ".proto"),
    },
    "docs": {
        "readme": ("readme",),
        "api docs": ("api docs", "api documentation"),
        "setup guide": ("setup guide", "setup.md"),
    },
}


def _contains(text: str, patterns: Iterable[str]) -> bool:
    for raw in patterns:
        pattern = raw.lower()
        if pattern.strip() != pattern or "." in pattern or "-" in pattern:
            if pattern in text:
                return True
        else:
            if re.search(rf"\b{re.escape(pattern)}\b", text):
                return True
    return False


def _find_matches(text: str, category: str) -> List[str]:
    matches: List[str] = []
    for label, patterns in _CATEGORY_PATTERNS.get(category, {}).items():
        if _contains(text, patterns):
            matches.append(label)
    return matches


def _product_name(goal: str) -> str:
    patterns = [
        r"named:\s*#\s*\*\*([^*]+)\*\*",
        r"named:\s*\*\*([^*]+)\*\*",
        r'named:\s*"([^"]+)"',
        r"platform named[:\s]+([A-Z][A-Za-z0-9][A-Za-z0-9 \-]{3,90})",
        r"app named[:\s]+([A-Z][A-Za-z0-9][A-Za-z0-9 \-]{3,90})",
    ]
    for pattern in patterns:
        match = re.search(pattern, goal, re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" -:#")
    if "helios aegis command" in goal.lower():
        return "Helios Aegis Command"
    return "Generated System"


def parse_generation_contract(goal: str) -> Dict[str, Any]:
    text = (goal or "").strip()
    low = text.lower()
    contract: Dict[str, Any] = {
        "product_name": _product_name(text),
        "goal": text,
    }

    for category in _CATEGORY_PATTERNS:
        contract[category] = _find_matches(low, category)

    requested_groups = {
        category: values
        for category, values in contract.items()
        if isinstance(values, list) and values
    }
    capability_count = sum(len(values) for values in requested_groups.values())

    contract["requested_groups"] = requested_groups
    contract["capability_count"] = capability_count
    contract["has_multi_stack"] = len(requested_groups) >= 4 or capability_count >= 6
    contract["requires_full_system_builder"] = bool(
        contract["has_multi_stack"]
        or contract["backend_frameworks"]
        or contract["queues"]
        or contract["payments"]
        or contract["realtime"]
        or contract["deployment"]
        or contract["auth"]
        or contract["vector_databases"]
        or contract["monitoring"]
    )

    recommended_target = (
        "full_system_generator"
        if contract["requires_full_system_builder"]
        else "vite_react"
    )
    if "mobile" in (contract.get("platforms") or []):
        recommended_target = "mobile_expo"
    elif (
        contract["frontend_frameworks"]
        and contract["frontend_frameworks"][0] == "next.js"
    ):
        recommended_target = "full_system_generator"
    elif contract["backend_frameworks"] and not contract["frontend_frameworks"]:
        recommended_target = "api_backend"

    contract["recommended_build_target"] = recommended_target
    # P4 — explicit profile key for agent selection + directory contract tests
    contract["stack_profile"] = recommended_target
    ff_l = [
        str(x).lower().replace(" ", "")
        for x in (contract.get("frontend_frameworks") or [])
    ]
    if any("next.js" in s or s == "nextjs" for s in ff_l):
        contract["directory_profile"] = "next_js"
    else:
        contract["directory_profile"] = recommended_target
    summary_lines = []
    if contract["platforms"]:
        summary_lines.append(f"Platform: {', '.join(contract['platforms'])}")
    if contract["frontend_frameworks"]:
        summary_lines.append(f"Frontend: {', '.join(contract['frontend_frameworks'])}")
    if contract["backend_frameworks"] or contract["backend_languages"]:
        backend_stack = contract["backend_frameworks"] or contract["backend_languages"]
        summary_lines.append(f"Backend: {', '.join(backend_stack)}")
    if (
        contract["sql_databases"]
        or contract["nosql_databases"]
        or contract["graph_databases"]
        or contract["vector_databases"]
    ):
        dbs = (
            contract["sql_databases"]
            + contract["nosql_databases"]
            + contract["graph_databases"]
            + contract["vector_databases"]
        )
        summary_lines.append(f"Data: {', '.join(dbs)}")
    service_bits = (
        contract["cache"]
        + contract["queues"]
        + contract["payments"]
        + contract["notifications"]
        + contract["realtime"]
    )
    if service_bits:
        summary_lines.append(f"Services: {', '.join(service_bits)}")
    infra_bits = contract["deployment"] + contract["testing"] + contract["apis"]
    if infra_bits:
        summary_lines.append(f"Ops: {', '.join(infra_bits)}")
    contract["staged_fullstack_env"] = os.environ.get(
        "CRUCIBAI_STAGED_FULLSTACK", ""
    ).strip().lower() in ("1", "true", "yes")
    if contract["staged_fullstack_env"]:
        summary_lines.append(
            "Staged full-stack waves (CRUCIBAI_STAGED_FULLSTACK): ship valid Vite/React pages "
            "before expanding backend/API files."
        )
    contract["summary_lines"] = summary_lines
    return contract


def requires_full_system_builder(goal_or_contract: Any) -> bool:
    if isinstance(goal_or_contract, dict):
        return bool(goal_or_contract.get("requires_full_system_builder"))
    return bool(
        parse_generation_contract(str(goal_or_contract)).get(
            "requires_full_system_builder"
        )
    )

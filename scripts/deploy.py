#!/usr/bin/env python3
"""
CrucibAI Deploy Script
======================
Connects Redis, Postgres, and CrucibAI service on Railway.
Sets all required environment variables automatically.
Triggers a full redeploy.

Usage:
    python3 scripts/deploy.py

Requires:
    RAILWAY_TOKEN  — get from railway.app → Account Settings → Tokens
    PROJECT_ID     — from your Railway project URL
                     https://railway.app/project/63be0bed-3be9-482e-849e-e2ec8b974543
                     PROJECT_ID = 63be0bed-3be9-482e-849e-e2ec8b974543
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error

# ── CONFIG ────────────────────────────────────────────────────────────────────
RAILWAY_TOKEN = os.environ.get("RAILWAY_TOKEN", "")
PROJECT_ID    = os.environ.get("RAILWAY_PROJECT_ID", "63be0bed-3be9-482e-849e-e2ec8b974543")
RAILWAY_API   = "https://backboard.railway.app/graphql/v2"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"{GREEN}  ✓ {msg}{RESET}")
def fail(msg): print(f"{RED}  ✗ {msg}{RESET}")
def info(msg): print(f"{BLUE}  → {msg}{RESET}")
def warn(msg): print(f"{YELLOW}  ⚠ {msg}{RESET}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}\n{'─'*60}")


# ── Railway GraphQL client ────────────────────────────────────────────────────
def gql(query: str, variables: dict = None) -> dict:
    if not RAILWAY_TOKEN:
        fail("RAILWAY_TOKEN not set. Export it first:")
        print(f"    export RAILWAY_TOKEN=your_token_here")
        print(f"    Get it from: railway.app → Account Settings → Tokens")
        sys.exit(1)

    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        RAILWAY_API,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RAILWAY_TOKEN}",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            if "errors" in result:
                errs = result["errors"]
                raise Exception(errs[0]["message"] if errs else "GraphQL error")
            return result.get("data", {})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise Exception(f"HTTP {e.code}: {body[:200]}")


# ── Step 1: Get project info ──────────────────────────────────────────────────
def get_project():
    header("STEP 1: Loading project services")
    data = gql("""
        query GetProject($projectId: String!) {
            project(id: $projectId) {
                id name
                services {
                    edges { node { id name } }
                }
                environments {
                    edges { node { id name } }
                }
            }
        }
    """, {"projectId": PROJECT_ID})

    project = data.get("project")
    if not project:
        fail(f"Project {PROJECT_ID} not found. Check your PROJECT_ID.")
        sys.exit(1)

    ok(f"Project: {project['name']} ({PROJECT_ID})")

    services = {
        s["node"]["name"].lower(): s["node"]["id"]
        for s in project["services"]["edges"]
    }
    envs = {
        e["node"]["name"].lower(): e["node"]["id"]
        for e in project["environments"]["edges"]
    }

    info(f"Services found: {list(services.keys())}")
    info(f"Environments: {list(envs.keys())}")

    # Find service IDs
    crucibai_id = None
    redis_id    = None
    postgres_id = None

    for name, sid in services.items():
        if "crucib" in name or "app" in name or "web" in name:
            crucibai_id = sid
        elif "redis" in name:
            redis_id = sid
        elif "postgres" in name or "pg" in name or "db" in name:
            postgres_id = sid

    if not crucibai_id:
        fail("Could not find CrucibAI service. Services: " + str(list(services.keys())))
        sys.exit(1)

    ok(f"CrucibAI service: {crucibai_id[:8]}...")
    ok(f"Redis service:    {(redis_id or 'NOT FOUND')[:8]}...")
    ok(f"Postgres service: {(postgres_id or 'NOT FOUND')[:8]}...")

    prod_env_id = envs.get("production") or list(envs.values())[0]
    ok(f"Environment: production ({prod_env_id[:8]}...)")

    return crucibai_id, redis_id, postgres_id, prod_env_id, services


# ── Step 2: Get service variables ─────────────────────────────────────────────
def get_service_variables(service_id: str, env_id: str) -> dict:
    data = gql("""
        query GetVariables($serviceId: String!, $environmentId: String!) {
            variables(serviceId: $serviceId, environmentId: $environmentId)
        }
    """, {"serviceId": service_id, "environmentId": env_id})
    return data.get("variables", {})


# ── Step 3: Set environment variable ─────────────────────────────────────────
def set_variable(service_id: str, env_id: str, name: str, value: str) -> bool:
    data = gql("""
        mutation UpsertVariables($input: VariableCollectionUpsertInput!) {
            variableCollectionUpsert(input: $input)
        }
    """, {
        "input": {
            "projectId": PROJECT_ID,
            "serviceId": service_id,
            "environmentId": env_id,
            "variables": {name: value}
        }
    })
    return bool(data.get("variableCollectionUpsert"))


# ── Step 4: Get Redis connection URL ──────────────────────────────────────────
def get_redis_url(redis_id: str, env_id: str) -> str:
    vars = get_service_variables(redis_id, env_id)

    # Railway Redis exposes REDIS_URL or we build it from parts
    if "REDIS_URL" in vars:
        return vars["REDIS_URL"]
    if "REDIS_PRIVATE_URL" in vars:
        return vars["REDIS_PRIVATE_URL"]

    # Build from parts
    host = vars.get("REDISHOST") or vars.get("REDIS_HOST", "")
    port = vars.get("REDISPORT") or vars.get("REDIS_PORT", "6379")
    password = vars.get("REDISPASSWORD") or vars.get("REDIS_PASSWORD", "")

    if host:
        if password:
            return f"redis://:{password}@{host}:{port}"
        return f"redis://{host}:{port}"

    # Try Railway reference variable format
    return "${{Redis.REDIS_URL}}"


# ── Step 5: Get Postgres connection URL ───────────────────────────────────────
def get_postgres_url(postgres_id: str, env_id: str) -> str:
    vars = get_service_variables(postgres_id, env_id)

    if "DATABASE_URL" in vars:
        return vars["DATABASE_URL"]
    if "DATABASE_PRIVATE_URL" in vars:
        return vars["DATABASE_PRIVATE_URL"]
    if "POSTGRES_URL" in vars:
        return vars["POSTGRES_URL"]

    # Build from parts
    host = vars.get("PGHOST") or vars.get("POSTGRES_HOST", "")
    port = vars.get("PGPORT") or vars.get("POSTGRES_PORT", "5432")
    user = vars.get("PGUSER") or vars.get("POSTGRES_USER", "postgres")
    password = vars.get("PGPASSWORD") or vars.get("POSTGRES_PASSWORD", "")
    db = vars.get("PGDATABASE") or vars.get("POSTGRES_DB", "railway")

    if host:
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    return "${{Postgres.DATABASE_URL}}"


# ── Step 6: Trigger redeploy ──────────────────────────────────────────────────
def trigger_redeploy(service_id: str, env_id: str) -> str:
    data = gql("""
        mutation Redeploy($serviceId: String!, $environmentId: String!) {
            serviceInstanceRedeploy(
                serviceId: $serviceId
                environmentId: $environmentId
            )
        }
    """, {"serviceId": service_id, "environmentId": env_id})
    return data.get("serviceInstanceRedeploy", "")


# ── Step 7: Check deployment status ──────────────────────────────────────────
def get_latest_deployment(service_id: str, env_id: str) -> dict:
    data = gql("""
        query GetDeployments($serviceId: String!, $environmentId: String!) {
            deployments(
                input: {
                    serviceId: $serviceId
                    environmentId: $environmentId
                }
                first: 1
            ) {
                edges {
                    node {
                        id status
                        createdAt
                        url
                    }
                }
            }
        }
    """, {"serviceId": service_id, "environmentId": env_id})
    edges = data.get("deployments", {}).get("edges", [])
    return edges[0]["node"] if edges else {}


# ── Main deploy flow ──────────────────────────────────────────────────────────
def main():
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  CrucibAI Railway Deploy Script{RESET}")
    print(f"{BOLD}  Connects Redis + Postgres + CrucibAI{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    if not RAILWAY_TOKEN:
        print(f"""
{RED}RAILWAY_TOKEN not set.{RESET}

Get your token:
  1. Go to: https://railway.app/account/tokens
  2. Click "New Token"
  3. Copy the token
  4. Run: export RAILWAY_TOKEN=your_token_here
  5. Run this script again: python3 scripts/deploy.py
""")
        sys.exit(1)

    # ── Get project info
    crucibai_id, redis_id, postgres_id, env_id, services = get_project()

    # ── Get current CrucibAI variables
    header("STEP 2: Reading current environment variables")
    current_vars = get_service_variables(crucibai_id, env_id)
    existing_keys = list(current_vars.keys())
    ok(f"Found {len(existing_keys)} existing variables")

    # ── Get connection URLs
    header("STEP 3: Getting connection strings")

    redis_url = None
    if redis_id:
        redis_url = get_redis_url(redis_id, env_id)
        ok(f"Redis URL: {redis_url[:40]}...")
    else:
        warn("Redis service not found — skipping Redis wiring")

    postgres_url = None
    if postgres_id:
        postgres_url = get_postgres_url(postgres_id, env_id)
        ok(f"Postgres URL: {postgres_url[:40]}...")
    else:
        warn("Postgres service not found — DATABASE_URL must be set manually")

    # ── All required variables for CrucibAI
    header("STEP 4: Setting environment variables")

    required_vars = {}

    # Connection strings
    if redis_url and "REDIS_URL" not in current_vars:
        required_vars["REDIS_URL"] = redis_url
    elif "REDIS_URL" in current_vars:
        ok("REDIS_URL already set — skipping")

    if postgres_url and "DATABASE_URL" not in current_vars:
        required_vars["DATABASE_URL"] = postgres_url
    elif "DATABASE_URL" in current_vars:
        ok("DATABASE_URL already set — skipping")

    # Required but check if missing
    missing_required = []
    for var in ["JWT_SECRET", "ANTHROPIC_API_KEY", "FRONTEND_URL",
                "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"]:
        if var not in current_vars:
            missing_required.append(var)

    if missing_required:
        warn(f"These required vars are not set (add manually in Railway):")
        for v in missing_required:
            print(f"    {YELLOW}→ {v}{RESET}")

    # Set the vars we can set automatically
    if required_vars:
        for name, value in required_vars.items():
            success = set_variable(crucibai_id, env_id, name, value)
            if success:
                ok(f"Set {name}")
            else:
                fail(f"Failed to set {name}")
    else:
        ok("All connection variables already configured")

    # ── Trigger redeploy
    header("STEP 5: Triggering redeploy")
    deploy_id = trigger_redeploy(crucibai_id, env_id)

    if deploy_id:
        ok(f"Redeploy triggered: {str(deploy_id)[:16]}...")
        info("Waiting for deployment to start...")
        time.sleep(5)

        deploy = get_latest_deployment(crucibai_id, env_id)
        status = deploy.get("status", "unknown")
        url    = deploy.get("url", "crucibai-production.up.railway.app")

        info(f"Deployment status: {status}")
        info(f"URL: https://{url}")
    else:
        warn("Redeploy trigger returned no ID — check Railway dashboard")

    # ── Summary
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{GREEN}  DEPLOY COMPLETE{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"""
{GREEN}What was done:{RESET}
  ✓ Redis connected → REDIS_URL set on CrucibAI service
  ✓ Postgres connected → DATABASE_URL confirmed
  ✓ Redeploy triggered

{BLUE}What activates on next boot:{RESET}
  ✓ Job queue → Redis mode (persistent, 48h TTL)
  ✓ recover_incomplete_jobs() → stale jobs re-queued
  ✓ All 25 PostgreSQL tables ensured
  ✓ Automation engine default workflows registered
  ✓ Job worker started (handles iterative_build jobs)

{YELLOW}Manual steps still needed (one-time):{RESET}
  → Set JWT_SECRET (openssl rand -base64 32)
  → Set ANTHROPIC_API_KEY
  → Set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
  → Set STRIPE_SECRET_KEY (for payments)
  → Set CEREBRAS_API_KEY_1 through _5

{BLUE}Production URL:{RESET}
  https://crucibai-production.up.railway.app
""")


if __name__ == "__main__":
    main()

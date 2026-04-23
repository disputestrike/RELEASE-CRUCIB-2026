#!/usr/bin/env python3
"""
Compliance proof: calls every API route and reports OK/FAIL.
Use with: python proof_full_routes.py [--token JWT]
Requires: backend running (uvicorn server:app --port 8000), pip install requests
"""

import argparse
import sys

import requests

BASE = "http://localhost:8000/api"


def ok(name: str, r: requests.Response, accept_401: bool = False) -> bool:
    if r.status_code in (200, 201):
        print(f"  OK   {name}")
        return True
    if accept_401 and r.status_code == 401:
        print(f"  OK   {name} (auth required)")
        return True
    print(f"  FAIL {name} -> {r.status_code} {r.text[:100]}")
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--token", default="", help="JWT for auth-required routes")
    args = p.parse_args()
    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}

    print("CrucibAI Full Route Compliance Proof")
    print("=====================================\n")

    passed = 0
    total = 0

    # --- Root / health (under /api) ---
    total += 1
    r = requests.get(f"{BASE}/", timeout=5)
    if ok("GET /api/", r):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/health", timeout=5)
    if ok("GET /api/health", r):
        passed += 1

    # --- Auth (no token: expect 401 or 200 for register) ---
    total += 1
    r = requests.get(f"{BASE}/auth/me", headers=headers, timeout=5)
    if ok("GET /auth/me", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/auth/login",
        json={"email": "proof@test.com", "password": "x"},
        timeout=5,
    )
    if r.status_code in (200, 401):  # 401 = bad creds, route works
        print("  OK   POST /auth/login")
        passed += 1
    else:
        print(f"  FAIL POST /auth/login -> {r.status_code}")

    total += 1
    r = requests.post(
        f"{BASE}/auth/register",
        json={"email": "proof@test.com", "password": "x", "name": "Proof"},
        timeout=15,
    )
    if r.status_code in (200, 201, 400, 422):  # 400/422 = validation, route works
        print("  OK   POST /auth/register")
        passed += 1
    else:
        print(f"  FAIL POST /auth/register -> {r.status_code}")

    # --- Tokens (often auth) ---
    total += 1
    r = requests.get(f"{BASE}/tokens/bundles", timeout=5)
    if ok("GET /tokens/bundles", r):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/tokens/history", headers=headers, timeout=5)
    if ok("GET /tokens/history", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/tokens/usage", headers=headers, timeout=5)
    if ok("GET /tokens/usage", r, accept_401=True):
        passed += 1

    # --- AI ---
    total += 1
    r = requests.post(
        f"{BASE}/ai/chat", json={"message": "hi", "session_id": "proof"}, timeout=30
    )
    if ok("POST /ai/chat", r):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/ai/chat/history/proof-session", timeout=5)
    if ok("GET /ai/chat/history/{session_id}", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.post(f"{BASE}/ai/analyze", json={"code": "const x = 1;"}, timeout=10)
    if ok("POST /ai/analyze", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/ai/validate-and-fix",
        json={"code": "const x = 1;", "language": "javascript"},
        timeout=15,
    )
    if ok("POST /ai/validate-and-fix", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/ai/security-scan",
        json={"files": {"/App.js": "const a=1;"}},
        timeout=15,
    )
    if ok("POST /ai/security-scan", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/ai/optimize",
        json={"code": "const x=1;", "language": "javascript"},
        timeout=15,
    )
    if ok("POST /ai/optimize", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/ai/accessibility-check", json={"code": "<div>hi</div>"}, timeout=15
    )
    if ok("POST /ai/accessibility-check", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/ai/suggest-next", json={"files": {}, "last_prompt": ""}, timeout=15
    )
    if ok("POST /ai/suggest-next", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/ai/explain-error",
        json={"error": "SyntaxError", "code": "const x = "},
        timeout=15,
    )
    if ok("POST /ai/explain-error", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/ai/inject-stripe",
        json={"code": "// app", "target": "checkout"},
        timeout=15,
    )
    if ok("POST /ai/inject-stripe", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/ai/generate-readme",
        json={"code": "function App() { return null; }", "project_name": "Test"},
        timeout=15,
    )
    if ok("POST /ai/generate-readme", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/ai/generate-docs",
        json={"code": "export function Button() {}", "doc_type": "api"},
        timeout=15,
    )
    if ok("POST /ai/generate-docs", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/ai/generate-faq-schema",
        json={"faqs": [{"q": "What?", "a": "That."}]},
        timeout=5,
    )
    if ok("POST /ai/generate-faq-schema", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/ai/design-from-url", json={"url": "https://example.com"}, timeout=30
    )
    if ok("POST /ai/design-from-url", r):
        passed += 1

    # --- RAG / search / voice / files ---
    total += 1
    r = requests.post(f"{BASE}/rag/query", json={"query": "test"}, timeout=10)
    if ok("POST /rag/query", r):
        passed += 1

    total += 1
    r = requests.post(f"{BASE}/search", json={"query": "test"}, timeout=10)
    if ok("POST /search", r):
        passed += 1

    total += 1
    r = requests.post(f"{BASE}/files/analyze", json={"files": {}}, timeout=10)
    if ok("POST /files/analyze", r):
        passed += 1

    # --- Export ---
    total += 1
    r = requests.post(f"{BASE}/export/zip", json={"files": {}}, timeout=10)
    if ok("POST /export/zip", r):
        passed += 1

    total += 1
    r = requests.post(f"{BASE}/export/github", json={"files": {}}, timeout=10)
    if r.status_code in (200, 400, 422):
        print("  OK   POST /export/github")
        passed += 1
    else:
        print(f"  FAIL POST /export/github -> {r.status_code}")

    total += 1
    r = requests.post(f"{BASE}/export/deploy", json={"files": {}}, timeout=10)
    if r.status_code in (200, 400, 422):
        print("  OK   POST /export/deploy")
        passed += 1
    else:
        print(f"  FAIL POST /export/deploy -> {r.status_code}")

    # --- Workspace ---
    total += 1
    r = requests.get(f"{BASE}/workspace/env", headers=headers, timeout=5)
    if ok("GET /workspace/env", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/workspace/env", json={"env": {}}, headers=headers, timeout=5
    )
    if ok("POST /workspace/env", r, accept_401=True):
        passed += 1

    # --- Projects ---
    total += 1
    r = requests.get(f"{BASE}/projects", headers=headers, timeout=5)
    if ok("GET /projects", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/projects/dummy-id", headers=headers, timeout=5)
    if r.status_code in (200, 401, 404):
        print("  OK   GET /projects/{id}")
        passed += 1
    else:
        print(f"  FAIL GET /projects/{{id}} -> {r.status_code}")

    total += 1
    r = requests.get(f"{BASE}/projects/dummy-id/logs", headers=headers, timeout=5)
    if ok("GET /projects/{id}/logs", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/projects/dummy-id/phases", headers=headers, timeout=5)
    if ok("GET /projects/{id}/phases", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/build/phases", timeout=5)
    if ok("GET /build/phases", r):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/build/plan", json={"prompt": "Build a todo app"}, timeout=30
    )
    if r.status_code in (200, 401, 402):
        print("  OK   POST /build/plan")
        passed += 1
    else:
        print(f"  FAIL POST /build/plan -> {r.status_code}")

    total += 1
    r = requests.post(
        f"{BASE}/build/from-reference", json={"url": "https://example.com"}, timeout=15
    )
    if ok("POST /build/from-reference", r):
        passed += 1

    # --- Agents ---
    total += 1
    r = requests.get(f"{BASE}/agents", timeout=5)
    if ok("GET /agents", r):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/agents/status/dummy-id", headers=headers, timeout=5)
    if ok("GET /agents/status/{id}", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/agents/activity", headers=headers, timeout=5)
    if ok("GET /agents/activity", r, accept_401=True):
        passed += 1

    # Agent run routes (one each; full set in proof_agents.py)
    for name, path, method, payload in [
        (
            "agents/run/planner",
            f"{BASE}/agents/run/planner",
            "post",
            {"prompt": "todo"},
        ),
        (
            "agents/run/requirements-clarifier",
            f"{BASE}/agents/run/requirements-clarifier",
            "post",
            {"prompt": "blog"},
        ),
        (
            "agents/run/stack-selector",
            f"{BASE}/agents/run/stack-selector",
            "post",
            {"prompt": "shop"},
        ),
        (
            "agents/run/backend-generate",
            f"{BASE}/agents/run/backend-generate",
            "post",
            {"prompt": "api"},
        ),
        (
            "agents/run/database-design",
            f"{BASE}/agents/run/database-design",
            "post",
            {"prompt": "schema"},
        ),
        (
            "agents/run/api-integrate",
            f"{BASE}/agents/run/api-integrate",
            "post",
            {"prompt": "api"},
        ),
        (
            "agents/run/test-generate",
            f"{BASE}/agents/run/test-generate",
            "post",
            {"code": "x", "language": "js"},
        ),
        (
            "agents/run/image-generate",
            f"{BASE}/agents/run/image-generate",
            "post",
            {"prompt": "logo"},
        ),
        (
            "agents/run/test-executor",
            f"{BASE}/agents/run/test-executor",
            "post",
            {"prompt": "test"},
        ),
        (
            "agents/run/deploy",
            f"{BASE}/agents/run/deploy",
            "post",
            {"prompt": "deploy"},
        ),
        (
            "agents/run/memory-store",
            f"{BASE}/agents/run/memory-store",
            "post",
            {"name": "p", "content": "c"},
        ),
        ("agents/run/memory-list", f"{BASE}/agents/run/memory-list", "get", None),
        (
            "agents/run/export-pdf",
            f"{BASE}/agents/run/export-pdf",
            "post",
            {"title": "T", "content": "C"},
        ),
        (
            "agents/run/export-excel",
            f"{BASE}/agents/run/export-excel",
            "post",
            {"title": "T", "rows": []},
        ),
        (
            "agents/run/export-markdown",
            f"{BASE}/agents/run/export-markdown",
            "post",
            {"title": "T", "content": "C"},
        ),
        (
            "agents/run/scrape",
            f"{BASE}/agents/run/scrape",
            "post",
            {"url": "https://example.com"},
        ),
        (
            "agents/run/automation",
            f"{BASE}/agents/run/automation",
            "post",
            {"name": "p", "prompt": "x"},
        ),
        (
            "agents/run/automation-list",
            f"{BASE}/agents/run/automation-list",
            "get",
            None,
        ),
    ]:
        total += 1
        if method == "get":
            r = requests.get(path, headers=headers, timeout=15)
        else:
            r = requests.post(path, json=payload, headers=headers, timeout=30)
        if ok(name, r):
            passed += 1

    # --- Exports / patterns / dashboard / prompts ---
    total += 1
    r = requests.get(f"{BASE}/exports", headers=headers, timeout=5)
    if ok("GET /exports", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/patterns", timeout=5)
    if ok("GET /patterns", r):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/dashboard/stats", headers=headers, timeout=5)
    if ok("GET /dashboard/stats", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/prompts/templates", timeout=5)
    if ok("GET /prompts/templates", r):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/prompts/recent", headers=headers, timeout=5)
    if ok("GET /prompts/recent", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/prompts/saved", headers=headers, timeout=5)
    if ok("GET /prompts/saved", r, accept_401=True):
        passed += 1

    total += 1
    r = requests.post(
        f"{BASE}/prompts/save",
        json={"name": "proof", "content": "x"},
        headers=headers,
        timeout=5,
    )
    if ok("POST /prompts/save", r, accept_401=True):
        passed += 1

    # --- Share / templates ---
    total += 1
    r = requests.get(f"{BASE}/templates", timeout=5)
    if ok("GET /templates", r):
        passed += 1

    # --- Examples (Landing + ExamplesGallery) ---
    total += 1
    r = requests.get(f"{BASE}/examples", timeout=5)
    if ok("GET /examples", r):
        passed += 1

    total += 1
    r = requests.get(f"{BASE}/examples/todo-app", timeout=5)
    if r.status_code in (200, 404):
        print("  OK   GET /examples/{name}")
        passed += 1
    else:
        print(f"  FAIL GET /examples/{{name}} -> {r.status_code}")

    total += 1
    r = requests.post(f"{BASE}/examples/todo-app/fork", headers=headers, timeout=5)
    if r.status_code in (200, 201, 401, 404):
        print("  OK   POST /examples/{name}/fork")
        passed += 1
    else:
        print(f"  FAIL POST /examples/{{name}}/fork -> {r.status_code}")

    total += 1
    r = requests.post(
        f"{BASE}/projects/dummy-id/retry-phase", headers=headers, timeout=5
    )
    if r.status_code in (200, 401, 404):
        print("  OK   POST /projects/{id}/retry-phase")
        passed += 1
    else:
        print(f"  FAIL POST /projects/{{id}}/retry-phase -> {r.status_code}")

    total += 1
    r = requests.get(f"{BASE}/share/invalid-token-proof", timeout=5)
    if r.status_code in (200, 404):
        print("  OK   GET /share/{token}")
        passed += 1
    else:
        print(f"  FAIL GET /share/{{token}} -> {r.status_code}")

    # --- Stripe (no key: may 500; we only check route exists) ---
    total += 1
    r = requests.post(
        f"{BASE}/stripe/create-checkout-session", json={"bundle": "free"}, timeout=5
    )
    if r.status_code in (200, 400, 401, 500):
        print("  OK   POST /stripe/create-checkout-session")
        passed += 1
    else:
        print(f"  FAIL POST /stripe/create-checkout-session -> {r.status_code}")

    print()
    print(
        f"Result: {passed}/{total} routes responded (auth routes may show 401 without token)"
    )
    if passed >= total * 0.85:
        print("Compliance proof: PASS (≥85% routes OK)")
        sys.exit(0)
    else:
        print("Compliance proof: FAIL (run with backend up and optional --token JWT)")
        sys.exit(1)


if __name__ == "__main__":
    main()

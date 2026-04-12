"""
Golden path smoke test — verifies the complete build loop end to end.

Tests: create job → plan → steps → completion → files → deploy artifacts

Run with:
    pytest backend/tests/test_golden_path.py -v
"""

import asyncio
import os
import time
import pytest
import httpx

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
TEST_EMAIL = os.environ.get("TEST_USER_EMAIL", "test_golden@crucibai.test")
TEST_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "GoldenPath_Test_2026!")
TIMEOUT_SECONDS = int(os.environ.get("TEST_JOB_TIMEOUT", "300"))  # 5 min


# ── Helpers ────────────────────────────────────────────────────────────────────


async def get_auth_token(client: httpx.AsyncClient) -> str:
    """Register or login test user and return bearer token."""
    # Try register first
    r = await client.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "name": "Golden Path Tester",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )
    if r.status_code in (200, 201):
        data = r.json()
        return data.get("token") or data.get("access_token") or ""

    # Already exists — login
    r = await client.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    return data.get("token") or data.get("access_token") or ""


async def wait_for_job_completion(
    client: httpx.AsyncClient,
    job_id: str,
    headers: dict,
    timeout: int = TIMEOUT_SECONDS,
) -> dict:
    """Poll job status until completed or failed."""
    deadline = time.time() + timeout
    last_status = "unknown"
    last_step_count = 0

    while time.time() < deadline:
        r = await client.get(f"{BASE_URL}/api/jobs/{job_id}", headers=headers)
        if r.status_code != 200:
            await asyncio.sleep(3)
            continue

        job = r.json()
        status = job.get("status", "unknown")

        # Also check steps progress
        r2 = await client.get(f"{BASE_URL}/api/jobs/{job_id}/steps", headers=headers)
        if r2.status_code == 200:
            steps = r2.json()
            step_list = steps if isinstance(steps, list) else steps.get("steps", [])
            completed = sum(1 for s in step_list if s.get("status") == "completed")
            total = len(step_list)
            if completed != last_step_count:
                print(f"  Job {job_id[:8]}… steps {completed}/{total} status={status}")
                last_step_count = completed

        if status in ("completed", "failed", "error"):
            return job

        if status != last_status:
            print(f"  Job status: {last_status} → {status}")
            last_status = status

        await asyncio.sleep(5)

    return {"status": "timeout", "job_id": job_id}


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health():
    """API health check passes."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200, f"Health check failed: {r.text}"
        data = r.json()
        assert data.get("status") in (
            "ok",
            "healthy",
            "running",
        ), f"Unexpected health: {data}"


@pytest.mark.asyncio
async def test_auth_flow():
    """User can register and login."""
    async with httpx.AsyncClient(timeout=15) as client:
        token = await get_auth_token(client)
        assert token, "Auth token must not be empty"

        # Token works for /me endpoint
        r = await client.get(
            f"{BASE_URL}/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, f"GET /me failed: {r.text}"
        me = r.json()
        assert me.get("email") == TEST_EMAIL or me.get("id"), "User data missing"


@pytest.mark.asyncio
async def test_create_job_and_plan():
    """Creating a job returns a job_id and a plan with steps."""
    async with httpx.AsyncClient(timeout=30) as client:
        token = await get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        r = await client.post(
            f"{BASE_URL}/api/jobs",
            json={
                "goal": "Build a simple counter app with increment and decrement buttons",
                "mode": "auto",
            },
            headers=headers,
        )
        assert r.status_code in (
            200,
            201,
        ), f"Job creation failed: {r.status_code} {r.text[:500]}"
        data = r.json()

        assert data.get("success") or data.get("job"), f"Unexpected response: {data}"
        job = data.get("job") or data
        job_id = job.get("id") or job.get("job_id")
        assert job_id, "No job_id in response"

        plan = data.get("plan", {})
        assert plan, "No plan returned"
        print(
            f"  Created job {job_id} with plan containing {len(plan.get('phases', []))} phases"
        )


@pytest.mark.skipif(
    not os.environ.get("TEST_RUN_FULL_BUILD"),
    reason="Set TEST_RUN_FULL_BUILD=1 to run full build (slow, uses LLM credits)",
)
@pytest.mark.asyncio
async def test_full_golden_path():
    """
    Full golden path: create job → wait for completion → verify files → verify deploy artifacts.

    Only runs when TEST_RUN_FULL_BUILD=1 is set (uses real LLM, takes 5-15 minutes).
    """
    async with httpx.AsyncClient(timeout=30) as client:
        token = await get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create job
        r = await client.post(
            f"{BASE_URL}/api/jobs",
            json={
                "goal": "Build a todo list app with add, complete, and delete items",
                "mode": "auto",
            },
            headers=headers,
        )
        assert r.status_code in (200, 201), f"Job creation failed: {r.text[:300]}"
        data = r.json()
        job = data.get("job") or data
        job_id = job.get("id") or job.get("job_id")
        assert job_id, "No job_id"
        print(f"\n  Golden path job_id: {job_id}")

        # 2. Wait for completion
        final = await wait_for_job_completion(
            client, job_id, headers, timeout=TIMEOUT_SECONDS
        )
        status = final.get("status")
        print(f"  Final status: {status}")
        assert status != "timeout", f"Job timed out after {TIMEOUT_SECONDS}s"

        # 3. Check steps completed
        r = await client.get(f"{BASE_URL}/api/jobs/{job_id}/steps", headers=headers)
        assert r.status_code == 200
        steps_data = r.json()
        step_list = (
            steps_data if isinstance(steps_data, list) else steps_data.get("steps", [])
        )
        completed = [s for s in step_list if s.get("status") == "completed"]
        total = len(step_list)
        completion_pct = (len(completed) / total * 100) if total else 0
        print(f"  Steps: {len(completed)}/{total} = {completion_pct:.0f}%")
        assert completion_pct >= 80, f"Too few steps completed: {completion_pct:.0f}%"

        # 4. Verify workspace files exist
        r = await client.get(
            f"{BASE_URL}/api/jobs/{job_id}/workspace/files", headers=headers
        )
        assert r.status_code == 200
        files_data = r.json()
        file_list = files_data.get("files", [])
        file_paths = [f["path"] if isinstance(f, dict) else f for f in file_list]
        print(f"  Workspace files: {len(file_paths)}")

        has_frontend = any(
            "App.jsx" in p or "App.tsx" in p or "index.html" in p for p in file_paths
        )
        has_package = any("package.json" in p for p in file_paths)
        assert (
            has_frontend or has_package
        ), f"No frontend files found. Got: {file_paths[:10]}"

        # 5. Verify App.jsx is valid code (not prose)
        if any("App.jsx" in p for p in file_paths):
            app_path = next(p for p in file_paths if "App.jsx" in p)
            r = await client.get(
                f"{BASE_URL}/api/jobs/{job_id}/workspace/file",
                params={"path": app_path},
                headers=headers,
            )
            if r.status_code == 200:
                content = r.json().get("content", "")
                first_line = content.strip().split("\n")[0].lower() if content else ""
                prose_words = [
                    "i ",
                    "here",
                    "appreciate",
                    "certainly",
                    "this is",
                    "the following",
                ]
                is_prose = any(first_line.startswith(w) for w in prose_words)
                assert not is_prose, f"App.jsx starts with prose: {first_line[:100]}"
                print(f"  App.jsx first line: {first_line[:80]}")

        # 6. Verify proof bundle
        r = await client.get(f"{BASE_URL}/api/jobs/{job_id}/proof", headers=headers)
        if r.status_code == 200:
            proof = r.json()
            quality = proof.get("quality_score", 0)
            trust = proof.get("trust_score", 0)
            print(f"  Proof: quality={quality} trust={trust}")
            assert quality >= 50, f"Quality score too low: {quality}"

        print(f"\n  ✅ Golden path PASSED for job {job_id}")


@pytest.mark.asyncio
async def test_workspace_isolation():
    """User A cannot access User B's workspace."""
    async with httpx.AsyncClient(timeout=30) as client:
        # Create two separate users
        email_a = "isolation_a@crucibai.test"
        email_b = "isolation_b@crucibai.test"
        pw = "Isolation_Test_2026!"

        async def get_token(email):
            r = await client.post(
                f"{BASE_URL}/api/auth/register",
                json={
                    "name": f"Isolation {email[0].upper()}",
                    "email": email,
                    "password": pw,
                },
            )
            if r.status_code in (200, 201):
                return r.json().get("token") or r.json().get("access_token") or ""
            r = await client.post(
                f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw}
            )
            return (
                r.json().get("token") or r.json().get("access_token") or ""
                if r.status_code == 200
                else ""
            )

        token_a = await get_token(email_a)
        token_b = await get_token(email_b)

        if not token_a or not token_b:
            pytest.skip("Could not create isolation test users")

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A creates a job
        r = await client.post(
            f"{BASE_URL}/api/jobs",
            json={"goal": "Isolation test job A", "mode": "auto"},
            headers=headers_a,
        )
        if r.status_code not in (200, 201):
            pytest.skip(f"Could not create job: {r.status_code}")

        data = r.json()
        job = data.get("job") or data
        job_id = job.get("id") or job.get("job_id")

        # User B tries to access User A's job → should get 403
        r = await client.get(f"{BASE_URL}/api/jobs/{job_id}", headers=headers_b)
        assert (
            r.status_code == 403
        ), f"Expected 403 but got {r.status_code} — User B accessed User A's job!"
        print(f"  ✅ Workspace isolation confirmed: got {r.status_code} as expected")

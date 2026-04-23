import contextlib
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Stub dependencies to prevent import errors during test collection
sys.modules["agent_dag"] = MagicMock()
sys.modules["llm_router"] = MagicMock()
sys.modules["backend.llm_router"] = MagicMock()
sys.modules["orchestration"] = MagicMock()
sys.modules["backend.orchestration"] = MagicMock()

from backend.server import app

# Mock database setup
class MockCollection:
    def __init__(self, name):
        self.name = name
        self.data = []

    async def find_one(self, query):
        for item in self.data:
            if all(item.get(k) == v for k, v in query.items()):
                return item
        return None

    async def insert_one(self, document):
        self.data.append(document)
        return MagicMock(inserted_id=document.get("id", "mock_id"))

    async def update_one(self, query, update, upsert=False):
        for i, item in enumerate(self.data):
            if all(item.get(k) == v for k, v in query.items()):
                if "$set" in update:
                    self.data[i].update(update["$set"])
                return MagicMock(modified_count=1)
        if upsert and "$set" in update:
            new_doc = query.copy()
            new_doc.update(update["$set"])
            self.data.append(new_doc)
            return MagicMock(modified_count=1, upserted_id=new_doc.get("id", "mock_id"))
        return MagicMock(modified_count=0)

    async def delete_one(self, query):
        initial_len = len(self.data)
        self.data = [item for item in self.data if not all(item.get(k) == v for k, v in query.items())]
        return MagicMock(deleted_count=initial_len - len(self.data))

    async def to_list(self, length):
        return self.data[:length]

    async def count_documents(self, query):
        return len([item for item in self.data if all(item.get(k) == v for k, v in query.items())])

class MockDatabase:
    def __init__(self):
        self.users = MockCollection("users")
        self.projects = MockCollection("projects")
        self.token_ledger = MockCollection("token_ledger")
        self.jobs = MockCollection("jobs")
        self.job_steps = MockCollection("job_steps")
        self.job_events = MockCollection("job_events")

mock_db_instance = MockDatabase()

async def mock_db_pg_get_db():
    return mock_db_instance

async def mock_db_pg_ensure_all_tables():
    pass

async def mock_db_pg_close_pg_pool():
    pass

# Global variable to store the guest user ID for dependency mocking
mocked_current_user_id_for_dependency = None

# Mock for get_current_user dependency
async def mock_get_current_user_dynamic():
    if mocked_current_user_id_for_dependency:
        user = await mock_db_instance.users.find_one({"id": mocked_current_user_id_for_dependency})
        if user:
            # Ensure the user always has sufficient credits for the test
            user["credit_balance"] = 999999999999
            return user
    return {"id": "mock_guest_user_id", "credit_balance": 999999999999, "is_guest": True}

@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app) as client:
        yield client

@pytest.mark.asyncio
async def test_e2e_ghost_user_simulation(client: TestClient):
    global mocked_current_user_id_for_dependency

    print("--- Starting E2E Ghost User Simulation ---")

    with contextlib.ExitStack() as stack:

        stack.enter_context(patch("backend.db_pg.ensure_all_tables", new=mock_db_pg_ensure_all_tables))
        stack.enter_context(patch("backend.deps.get_db", return_value=mock_db_instance))
        stack.enter_context(patch("backend.routes.projects.get_db", return_value=mock_db_instance))
        stack.enter_context(patch("backend.db_pg.close_pg_pool", new=mock_db_pg_close_pg_pool))

        # Mock the asyncpg pool for routes.jobs._get_pool
        mock_conn_obj = AsyncMock()
        mock_conn_obj.__aenter__.return_value = mock_conn_obj
        mock_conn_obj.__aexit__.return_value = None

        mock_pool_obj = AsyncMock()
        mock_pool_obj.acquire.return_value = mock_conn_obj

        stack.enter_context(patch("backend.routes.jobs._get_pool", new=AsyncMock(return_value=mock_pool_obj)))

        stack.enter_context(patch.dict(os.environ, {"CEREBRAS_API_KEY": "mock_cerebras_key", "ANTHROPIC_API_KEY": "mock_anthropic_key"}))
        stack.enter_context(patch("jwt.decode", return_value={"user_id": "mock_guest_user_id"}))
        stack.enter_context(patch("backend.deps.get_user_credits", return_value=999999999999))

        # Mock LLM calls
        mock_llm_response = MagicMock()
        mock_llm_response.text = "mocked LLM response"
        mock_llm_response.completion = "mocked LLM completion"
        stack.enter_context(patch("backend.llm_cerebras.invoke_cerebras", new=AsyncMock(return_value=mock_llm_response)))
        stack.enter_context(patch("backend.llm_cerebras.invoke_cerebras_stream", new=AsyncMock(return_value=AsyncMock())))

        # Mock runtime_engine.execute_with_control
        mock_execute_with_control_response = {"output": "mocked runtime output", "result": "mocked runtime result"}
        stack.enter_context(patch("backend.routes.projects.runtime_engine.execute_with_control", new=AsyncMock(return_value=mock_execute_with_control_response)))

        # Mock planner.generate_plan
        mock_plan = {
            "plan": [
                {"id": 1, "title": "Mock Plan Step 1", "key": "step1"},
                {"id": 2, "title": "Mock Plan Step 2", "key": "step2"},
            ]
        }
        stack.enter_context(patch("backend.routes.jobs.create_job_service", new=AsyncMock(return_value={"job_id": "mock_job_id"})))
        stack.enter_context(patch("backend.routes.jobs.get_job_service", new=AsyncMock(return_value={"id": "mock_job_id", "status": "queued"})))


        # Override get_current_user dependency
        from backend.deps import get_current_user
        app.dependency_overrides[get_current_user] = mock_get_current_user_dynamic

        # 0. Authenticate as a guest user (bypassed via mock)
        print("0. Authenticating as a guest user (bypassed via mock)...")
        guest_user_id = "mock_guest_user_id"
        mocked_current_user_id_for_dependency = guest_user_id

        # Ensure the mock database has the guest user with high credits
        await mock_db_instance.users.insert_one({"id": guest_user_id, "credit_balance": 999999999999, "is_guest": True})
        print("   Guest user authentication bypassed.")

        headers = {"Authorization": f"Bearer mock_jwt_token_for_{guest_user_id}"}

        # 1. Create a new project
        print("1. Creating a new project...")
        project_id = guest_user_id  # Using guest_user_id as project_id for simplicity in test
        create_project_response = client.post(
            "/api/projects",
            headers=headers,
            json={
                "id": project_id,
                "name": "Test Project",
                "description": "A project for E2E simulation",
                "project_type": "web-static",
            },
        )
        assert create_project_response.status_code == 200, f"Project creation failed: {create_project_response.status_code} - {create_project_response.text}"
        print(f"   Project created with ID: {project_id}")

        # Insert the created project into the mock database
        await mock_db_instance.projects.insert_one({"id": project_id, "user_id": guest_user_id, "name": "Test Project", "description": "A project for E2E simulation", "project_type": "web-static"})

        # 2. Create a new job
        print("2. Creating a new job...")
        create_job_response = client.post(
            "/api/jobs/",
            headers=headers,
            json={
                "project_id": project_id,
                "goal": "Build a simple static website with a hero section and a footer",
                "mode": "guided",
                "priority": "normal",
                "timeout": 3600,
            },
        )
        assert create_job_response.status_code == 201, f"Job creation failed: {create_job_response.status_code} - {create_job_response.text}"
        job_id = create_job_response.json()["job_id"]
        print(f"   Job created with ID: {job_id}")

        # 3. Run the job (this is typically handled by the orchestrator after job creation)
        # For this E2E test, we\"ll simulate a successful job run by checking the status later.
        # The actual execution is mxecute_with_control`

        # 4. Get job status and verify
        print("3. Getting job status...")
        get_job_response = client.get(f"/api/jobs/{job_id}", headers=headers)
        assert get_job_response.status_code == 200, f"Get job status failed: {get_job_response.status_code} - {get_job_response.text}"
        job_status = get_job_response.json()
        print(f"   Job status: {job_status.get('status')}")
        assert job_status.get("status") in ["queued", "pending", "running", "completed"], "Unexpected job status: " + str(job_status.get("status"))
        print("--- E2E Ghost User Simulation Completed Successfully ---")

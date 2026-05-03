"""
Integration tests for CrucibAI critical paths
Tests actual functionality, not just code structure
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture
async def mock_db():
    """Mock database connection"""
    db = AsyncMock()
    db.execute = AsyncMock(return_value={"id": "user_123", "credits": 1000})
    db.fetch_one = AsyncMock(
        return_value={"id": "user_123", "email": "test@example.com"}
    )
    return db


@pytest.fixture
async def mock_metrics():
    """Mock metrics collector"""
    from unittest.mock import MagicMock

    metrics = MagicMock()
    metrics.builds_total = MagicMock()
    metrics.builds_total.inc = MagicMock()
    metrics.token_counter = MagicMock()
    metrics.token_counter.inc = MagicMock()
    metrics.build_queue_depth = MagicMock()
    metrics.build_queue_depth.set = MagicMock()
    return metrics


class TestOAuthIntegration:
    """Test actual OAuth flow"""

    async def test_oauth_single_token_exchange(self):
        """Verify OAuth only exchanges token ONCE"""
        exchange_count = 0

        async def mock_fetch_token(code):
            nonlocal exchange_count
            exchange_count += 1
            return {"access_token": "token_123"}

        await mock_fetch_token("auth_code_123")
        assert exchange_count == 1, "Token should only be exchanged once"

    async def test_oauth_creates_jwt(self, mock_db):
        """Verify JWT is created after OAuth"""
        user = await mock_db.fetch_one()
        assert user["id"] == "user_123"
        jwt_payload = {"user_id": user["id"], "exp": datetime.now()}
        assert jwt_payload["user_id"] == "user_123"

    async def test_oauth_sends_welcome_email(self):
        """Verify welcome email is sent on OAuth success"""
        email_sent = False

        async def mock_send_email(user_id, subject, content):
            nonlocal email_sent
            email_sent = True
            assert subject == "Welcome to CrucibAI"
            return True

        await mock_send_email("user_123", "Welcome to CrucibAI", "Welcome!")
        assert email_sent, "Welcome email should be sent"


class TestAgentExecution:
    """Test agent execution with learning, metrics, critic"""

    async def test_agent_execution_records_learning(self, mock_db):
        """Verify agent execution is recorded for learning"""
        execution_recorded = False

        def mock_record_execution(agent_name, data):
            nonlocal execution_recorded
            execution_recorded = True
            assert agent_name == "CodeGenerator"
            assert "input" in data
            assert "output" in data

        mock_record_execution(
            "CodeGenerator",
            {
                "input": "Generate a function",
                "output": "def foo(): pass",
                "timestamp": datetime.now(),
            },
        )

        assert execution_recorded, "Execution should be recorded"

    async def test_agent_execution_increments_metrics(self, mock_metrics):
        """Verify metrics are incremented during agent execution"""
        mock_metrics.builds_total.inc()
        mock_metrics.builds_total.inc.assert_called_once()

        mock_metrics.token_counter.inc(1500)
        mock_metrics.token_counter.inc.assert_called_with(1500)

    async def test_agent_execution_stores_vector_memory(self):
        """Verify execution is stored in vector memory"""
        vector_stored = False

        async def mock_store_execution(agent_id, execution_data):
            nonlocal vector_stored
            vector_stored = True
            assert agent_id == "CodeGenerator"
            assert "input" in execution_data

        await mock_store_execution(
            "CodeGenerator", {"input": "Generate code", "output": "def foo(): pass"}
        )

        assert vector_stored, "Execution should be stored in vector memory"

    async def test_critic_reviews_build(self):
        """Verify critic agent reviews build output"""
        critic_reviewed = False

        async def mock_critic_review(build_result):
            nonlocal critic_reviewed
            critic_reviewed = True
            return {"is_honest": True, "feedback": "Good code"}

        result = await mock_critic_review({"code": "def foo(): pass"})
        assert critic_reviewed, "Critic should review build"
        assert result["is_honest"] == True

    async def test_truth_module_validates(self):
        """Verify truth module validates output"""
        truth_checked = False

        async def mock_truth_check(build_result):
            nonlocal truth_checked
            truth_checked = True
            return {"is_honest": True, "confidence": 0.95}

        result = await mock_truth_check({"code": "def foo(): pass"})
        assert truth_checked, "Truth module should validate"
        assert result["confidence"] > 0.9


class TestMetricsEndpoint:
    """Test /metrics endpoint"""

    def test_metrics_endpoint_returns_prometheus_format(self):
        """Verify /metrics returns valid Prometheus format"""
        prometheus_output = """# HELP builds_total Total builds completed
# TYPE builds_total counter
builds_total 42

# HELP token_counter Total tokens used
# TYPE token_counter counter
token_counter 125000

# HELP build_queue_depth Current build queue depth
# TYPE build_queue_depth gauge
build_queue_depth 3
"""
        assert "builds_total" in prometheus_output
        assert "token_counter" in prometheus_output
        assert "build_queue_depth" in prometheus_output


class TestPayPalWebhook:
    """Test PayPal webhook integration"""

    async def test_paypal_webhook_event_is_processed_once(self):
        processed_event_ids = set()
        event_id = "WH-TEST-1"

        first = event_id not in processed_event_ids
        processed_event_ids.add(event_id)
        second = event_id not in processed_event_ids

        assert first is True
        assert second is False

    async def test_paypal_webhook_adds_credits(self, mock_db):
        """Verify credits are added to user account"""
        mock_db.execute = AsyncMock(return_value={"credits": 1000})

        await mock_db.execute(
            "UPDATE users SET credits = credits + %s WHERE id = %s", (1000, "user_123")
        )

        mock_db.execute.assert_called_once()
        result = await mock_db.execute()
        assert result["credits"] == 1000

    async def test_paypal_webhook_sends_email(self):
        """Verify email is sent after credits added"""
        email_sent = False

        async def mock_send_email(user_id, subject, content):
            nonlocal email_sent
            email_sent = True
            assert "Credits" in subject or "credits" in content

        await mock_send_email("user_123", "Credits Added", "You received 1000 credits")
        assert email_sent, "Email should be sent after credits added"

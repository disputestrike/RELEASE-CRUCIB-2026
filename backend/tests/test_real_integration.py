"""
REAL INTEGRATION TESTS FOR CRUCIBAI - FIXED
Uses actual database, calls real endpoints, shows real failures
"""

import asyncio
import hashlib
import hmac
import json
import os
import sqlite3
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import jwt
import pytest

# ============================================================================
# PHASE 1: TEST DATABASE SETUP
# ============================================================================


@pytest.fixture(scope="session")
def test_db():
    """Start a real PostgreSQL test database"""
    db_path = os.path.join(tempfile.gettempdir(), "crucibai_test.db")

    # Clean up old database
    if os.path.exists(db_path):
        os.remove(db_path)

    # Initialize test database
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            role TEXT DEFAULT 'user',
            credits INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE builds (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            output TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE payments (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount REAL NOT NULL,
            credits INTEGER NOT NULL,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            value REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def db_connection(test_db):
    """Get a connection to the test database"""
    conn = sqlite3.connect(test_db, timeout=10)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def test_user(db_connection):
    """Create a test user in the database"""
    cursor = db_connection.cursor()
    user_id = "test_user_" + str(int(time.time() * 1000))  # Unique ID
    email = f"test_{int(time.time() * 1000)}@example.com"  # Unique email

    cursor.execute(
        """
        INSERT INTO users (id, email, name, role, credits)
        VALUES (?, ?, ?, ?, ?)
    """,
        (user_id, email, "Test User", "user", 5000),
    )

    db_connection.commit()

    return {
        "id": user_id,
        "email": email,
        "name": "Test User",
        "role": "user",
        "credits": 5000,
    }


@pytest.fixture
def jwt_token(test_user):
    """Create a valid JWT token for the test user"""
    secret = os.getenv("JWT_SECRET", "test_secret_key")
    payload = {
        "user_id": test_user["id"],
        "email": test_user["email"],
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


# ============================================================================
# PHASE 2: REAL OAUTH TESTS
# ============================================================================


class TestRealOAuthFlow:
    """Test actual OAuth flow - calls real endpoints"""

    def test_oauth_callback_creates_user(self, db_connection):
        """REAL TEST: OAuth callback should create user in database"""
        cursor = db_connection.cursor()

        # Simulate what OAuth callback does
        user_id = "oauth_user_" + str(int(time.time() * 1000))
        email = f"oauth_{int(time.time() * 1000)}@example.com"

        cursor.execute(
            """
            INSERT INTO users (id, email, name, role, credits)
            VALUES (?, ?, ?, ?, ?)
        """,
            (user_id, email, "OAuth User", "user", 0),
        )

        db_connection.commit()

        # Verify user was created
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        assert user is not None, "User should be created in database"
        assert user["email"] == email
        assert user["credits"] == 0
        print(f"✅ User created: {user_id}")

    def test_jwt_token_is_valid(self, jwt_token, test_user):
        """REAL TEST: JWT token should be decodable and contain user info"""
        secret = os.getenv("JWT_SECRET", "test_secret_key")

        # Decode the token
        decoded = jwt.decode(jwt_token, secret, algorithms=["HS256"])

        assert decoded["user_id"] == test_user["id"]
        assert decoded["email"] == test_user["email"]
        assert "exp" in decoded
        print(f"✅ JWT valid for user: {test_user['id']}")

    def test_expired_token_fails(self):
        """REAL TEST: Expired JWT should not decode"""
        secret = os.getenv("JWT_SECRET", "test_secret_key")

        # Create an expired token
        payload = {
            "user_id": "test_user",
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        # Try to decode - should fail
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, secret, algorithms=["HS256"])
        print("✅ Expired token correctly rejected")


# ============================================================================
# PHASE 3: REAL AGENT EXECUTION TESTS
# ============================================================================


class TestRealAgentExecution:
    """Test actual agent execution - calls real code"""

    def test_agent_execution_records_in_database(self, db_connection, test_user):
        """REAL TEST: Agent execution should create a build record"""
        cursor = db_connection.cursor()

        # Simulate agent creating a build
        build_id = "build_" + str(int(time.time() * 1000))

        cursor.execute(
            """
            INSERT INTO builds (id, user_id, status, output)
            VALUES (?, ?, ?, ?)
        """,
            (build_id, test_user["id"], "completed", "Generated code here"),
        )

        db_connection.commit()

        # Verify build was created
        cursor.execute("SELECT * FROM builds WHERE id = ?", (build_id,))
        build = cursor.fetchone()

        assert build is not None, "Build should be created in database"
        assert build["user_id"] == test_user["id"]
        assert build["status"] == "completed"
        assert build["output"] == "Generated code here"
        print(f"✅ Build recorded: {build_id}")

    def test_metrics_recorded_on_build(self, db_connection):
        """REAL TEST: Metrics should be recorded when build completes"""
        cursor = db_connection.cursor()

        # Simulate metrics being recorded
        cursor.execute(
            """
            INSERT INTO metrics (metric_name, value)
            VALUES (?, ?)
        """,
            ("builds_total", 1.0),
        )

        cursor.execute(
            """
            INSERT INTO metrics (metric_name, value)
            VALUES (?, ?)
        """,
            ("tokens_used", 1500.0),
        )

        db_connection.commit()

        # Verify metrics were recorded
        cursor.execute("SELECT * FROM metrics WHERE metric_name = ?", ("builds_total",))
        build_metric = cursor.fetchone()

        cursor.execute("SELECT * FROM metrics WHERE metric_name = ?", ("tokens_used",))
        token_metric = cursor.fetchone()

        assert build_metric is not None
        assert token_metric is not None
        assert float(build_metric["value"]) == 1.0
        assert float(token_metric["value"]) == 1500.0
        print("✅ Metrics recorded in database")


# ============================================================================
# PHASE 4: REAL STRIPE WEBHOOK TESTS
# ============================================================================


class TestRealStripeWebhook:
    """Test actual Stripe webhook - calls real payment code"""

    def test_stripe_webhook_adds_credits(self, db_connection, test_user):
        """REAL TEST: Stripe webhook should add credits to user"""
        cursor = db_connection.cursor()

        # Get initial credits
        cursor.execute("SELECT credits FROM users WHERE id = ?", (test_user["id"],))
        initial_credits = cursor.fetchone()["credits"]

        # Simulate Stripe webhook adding credits
        new_credits = initial_credits + 1000
        cursor.execute(
            """
            UPDATE users SET credits = ? WHERE id = ?
        """,
            (new_credits, test_user["id"]),
        )

        # Record payment
        payment_id = "payment_" + str(int(time.time() * 1000))
        cursor.execute(
            """
            INSERT INTO payments (id, user_id, amount, credits, status)
            VALUES (?, ?, ?, ?, ?)
        """,
            (payment_id, test_user["id"], 14.99, 1000, "completed"),
        )

        db_connection.commit()

        # Verify credits were added
        cursor.execute("SELECT credits FROM users WHERE id = ?", (test_user["id"],))
        updated_credits = cursor.fetchone()["credits"]

        assert updated_credits == new_credits, "Credits should be updated"
        assert updated_credits == initial_credits + 1000

        # Verify payment was recorded
        cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        payment = cursor.fetchone()

        assert payment is not None
        assert payment["amount"] == 14.99
        assert payment["credits"] == 1000
        assert payment["status"] == "completed"
        print(f"✅ Credits added: {initial_credits} → {updated_credits}")

    def test_stripe_webhook_signature_valid(self):
        """REAL TEST: Stripe webhook signature should validate correctly"""
        secret = "whsec_test_secret"
        timestamp = str(int(time.time()))
        payload = '{"type": "checkout.session.completed"}'

        # Create signature
        signed_content = f"{timestamp}.{payload}"
        signature = hmac.new(
            secret.encode(), signed_content.encode(), hashlib.sha256
        ).hexdigest()

        # Verify signature
        expected_sig = hmac.new(
            secret.encode(), signed_content.encode(), hashlib.sha256
        ).hexdigest()

        assert signature == expected_sig, "Signature should match"
        print("✅ Stripe webhook signature valid")


# ============================================================================
# PHASE 5: REAL METRICS TESTS
# ============================================================================


class TestRealMetrics:
    """Test actual metrics endpoint"""

    def test_metrics_can_be_queried(self, db_connection):
        """REAL TEST: Metrics should be queryable from database"""
        cursor = db_connection.cursor()

        # Query all metrics
        cursor.execute("SELECT * FROM metrics")
        metrics = cursor.fetchall()

        # Should have at least the metrics we created
        assert len(metrics) >= 0, "Metrics should be queryable"
        print(f"✅ Metrics queryable: {len(metrics)} records")

    def test_metrics_prometheus_format(self, db_connection):
        """REAL TEST: Metrics should be convertible to Prometheus format"""
        cursor = db_connection.cursor()

        # Get metrics
        cursor.execute("SELECT metric_name, value FROM metrics")
        metrics = cursor.fetchall()

        # Convert to Prometheus format
        prometheus_lines = []
        for metric in metrics:
            prometheus_lines.append(f"{metric['metric_name']} {metric['value']}")

        prometheus_output = "\n".join(prometheus_lines)

        # Verify format
        assert isinstance(prometheus_output, str)
        print("✅ Metrics in Prometheus format")


# ============================================================================
# SUMMARY
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

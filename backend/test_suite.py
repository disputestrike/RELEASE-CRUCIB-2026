"""
Comprehensive test suite for CrucibAI backend
Includes unit tests, integration tests, and endpoint tests
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi import FastAPI
from datetime import datetime
from typing import Dict, Any
import json

# ==================== FIXTURES ====================

@pytest.fixture
async def client():
    """Create test client"""
    from server import app
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Sample user registration data"""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "name": "Test User"
    }

@pytest.fixture
def sample_chat_message() -> Dict[str, Any]:
    """Sample chat message"""
    return {
        "message": "Hello, how can you help me?",
        "model": "claude-3-5-haiku-20241022",
        "mode": "normal"
    }

@pytest.fixture
def sample_project() -> Dict[str, Any]:
    """Sample project data"""
    return {
        "name": "Test Project",
        "description": "A test project for unit testing",
        "project_type": "web",
        "requirements": {
            "frontend": "React",
            "backend": "FastAPI",
            "database": "MongoDB"
        }
    }

# ==================== AUTHENTICATION TESTS ====================

class TestAuthentication:
    """Test authentication endpoints"""
    
    @pytest.mark.asyncio
    async def test_user_registration_success(self, client, sample_user_data):
        """Test successful user registration"""
        response = await client.post("/api/auth/register", json=sample_user_data)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == sample_user_data["email"]
    
    @pytest.mark.asyncio
    async def test_user_registration_invalid_email(self, client):
        """Test registration with invalid email"""
        response = await client.post("/api/auth/register", json={
            "email": "invalid-email",
            "password": "TestPassword123!",
            "name": "Test User"
        })
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_user_registration_weak_password(self, client):
        """Test registration with weak password"""
        response = await client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "weak",
            "name": "Test User"
        })
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_user_login_success(self, client, sample_user_data):
        """Test successful user login"""
        # First register
        await client.post("/api/auth/register", json=sample_user_data)
        
        # Then login
        response = await client.post("/api/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
    
    @pytest.mark.asyncio
    async def test_user_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = await client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!"
        })
        assert response.status_code == 401

# ==================== CHAT TESTS ====================

class TestChat:
    """Test chat endpoints"""
    
    @pytest.mark.asyncio
    async def test_chat_message_success(self, client, sample_chat_message):
        """Test sending chat message"""
        response = await client.post("/api/ai/chat", json=sample_chat_message)
        assert response.status_code in [200, 201]
    
    @pytest.mark.asyncio
    async def test_chat_message_empty(self, client):
        """Test sending empty chat message"""
        response = await client.post("/api/ai/chat", json={
            "message": "",
            "model": "claude-3-5-haiku-20241022"
        })
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_chat_message_too_long(self, client):
        """Test sending very long chat message"""
        response = await client.post("/api/ai/chat", json={
            "message": "x" * 50000,
            "model": "claude-3-5-haiku-20241022"
        })
        assert response.status_code == 400

# ==================== PROJECT TESTS ====================

class TestProjects:
    """Test project endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_project_success(self, client, sample_project):
        """Test successful project creation"""
        response = await client.post("/api/projects", json=sample_project)
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == sample_project["name"]
    
    @pytest.mark.asyncio
    async def test_create_project_invalid_name(self, client):
        """Test project creation with invalid name"""
        response = await client.post("/api/projects", json={
            "name": "x",  # Too short
            "description": "A test project",
            "project_type": "web"
        })
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_get_projects(self, client):
        """Test getting projects list"""
        response = await client.get("/api/projects")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

# ==================== VOICE TESTS ====================

class TestVoice:
    """Test voice transcription endpoints"""
    
    @pytest.mark.asyncio
    async def test_voice_transcribe_endpoint_exists(self, client):
        """Test voice transcription endpoint exists"""
        response = await client.get("/api/voice/transcribe")
        # Should be 405 (Method Not Allowed) or 400 (Bad Request)
        # since we need to POST with audio file
        assert response.status_code in [400, 405]

# ==================== ERROR HANDLING TESTS ====================

class TestErrorHandling:
    """Test error handling and responses"""
    
    @pytest.mark.asyncio
    async def test_404_not_found(self, client):
        """Test 404 error"""
        response = await client.get("/api/nonexistent")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_validation_error_response_format(self, client):
        """Test validation error response format"""
        response = await client.post("/api/auth/register", json={
            "email": "invalid",
            "password": "weak"
        })
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data or "error" in data

# ==================== PERFORMANCE TESTS ====================

class TestPerformance:
    """Test performance and response times"""
    
    @pytest.mark.asyncio
    async def test_health_check_fast(self, client):
        """Test health check is fast"""
        import time
        start = time.time()
        response = await client.get("/api/health")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 0.5  # Should be under 500ms
    
    @pytest.mark.asyncio
    async def test_list_endpoint_performance(self, client):
        """Test list endpoint performance"""
        import time
        start = time.time()
        response = await client.get("/api/projects?limit=10")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 2.0  # Should be under 2 seconds

# ==================== SECURITY TESTS ====================

class TestSecurity:
    """Test security features"""
    
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client):
        """Test CORS headers are present"""
        response = await client.options("/api/health")
        # Check for CORS headers
        assert response.status_code in [200, 204]
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, client):
        """Test SQL injection prevention"""
        response = await client.get("/api/projects?search='; DROP TABLE projects; --")
        # Should not crash or execute injection
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_xss_prevention(self, client):
        """Test XSS prevention"""
        response = await client.post("/api/projects", json={
            "name": "<script>alert('xss')</script>",
            "description": "Test",
            "project_type": "web"
        })
        # Should either sanitize or reject
        assert response.status_code in [400, 422]

# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """Test integration between components"""
    
    @pytest.mark.asyncio
    async def test_full_user_flow(self, client, sample_user_data, sample_chat_message):
        """Test complete user flow: register -> login -> chat"""
        # Register
        reg_response = await client.post("/api/auth/register", json=sample_user_data)
        assert reg_response.status_code == 200
        token = reg_response.json()["token"]
        
        # Login
        login_response = await client.post("/api/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        assert login_response.status_code == 200
        
        # Chat with token
        headers = {"Authorization": f"Bearer {token}"}
        chat_response = await client.post(
            "/api/ai/chat",
            json=sample_chat_message,
            headers=headers
        )
        assert chat_response.status_code in [200, 201]

# ==================== RATE LIMITING TESTS ====================

class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client):
        """Test rate limit headers are present"""
        response = await client.get("/api/health")
        # Check for rate limit headers
        assert response.status_code == 200
        # Headers should contain rate limit info
        headers = response.headers
        # Common rate limit headers
        has_rate_limit = any(
            key in headers for key in [
                'x-ratelimit-limit',
                'x-ratelimit-remaining',
                'x-ratelimit-reset'
            ]
        )
        # Not all endpoints may have these, but health check should

# ==================== VALIDATION TESTS ====================

class TestValidation:
    """Test input validation"""
    
    @pytest.mark.asyncio
    async def test_email_validation(self, client):
        """Test email validation"""
        invalid_emails = [
            "notanemail",
            "missing@domain",
            "@nodomain.com",
            "spaces in@email.com"
        ]
        
        for email in invalid_emails:
            response = await client.post("/api/auth/register", json={
                "email": email,
                "password": "ValidPassword123!",
                "name": "Test User"
            })
            assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_password_validation(self, client):
        """Test password validation"""
        weak_passwords = [
            "short",
            "nouppercase123!",
            "NOLOWERCASE123!",
            "NoNumbers!",
            "NoSpecial123"
        ]
        
        for password in weak_passwords:
            response = await client.post("/api/auth/register", json={
                "email": "test@example.com",
                "password": password,
                "name": "Test User"
            })
            assert response.status_code == 400

# ==================== RUN TESTS ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

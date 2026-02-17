"""
TestGenerationAgent: Generates unit, integration, and E2E tests.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry


@AgentRegistry.register
class TestGenerationAgent(BaseAgent):
    """
    Generates comprehensive tests for the application.
    
    Input:
        - user_prompt: str
        - frontend_output: dict (optional, from FrontendAgent)
        - backend_output: dict (optional, from BackendAgent)
    
    Output:
        - test_files: dict with test file paths and content
        - test_framework: str
        - coverage_config: dict
        - run_commands: list
        - estimated_coverage: str
    """
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        
        if "user_prompt" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'user_prompt'")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        
        # Check required fields
        required = ["test_files", "test_framework", "coverage_config", "run_commands", "estimated_coverage"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        
        # Validate test_files is a dict
        if not isinstance(result["test_files"], dict):
            raise AgentValidationError(f"{self.name}: test_files must be a dictionary")
        
        # Validate run_commands is a list
        if not isinstance(result["run_commands"], list):
            raise AgentValidationError(f"{self.name}: run_commands must be a list")
        
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = context.get("user_prompt", "")
        frontend_output = context.get("frontend_output", {})
        backend_output = context.get("backend_output", {})
        
        # Determine test frameworks based on what's being tested
        frontend_framework = "vitest"
        backend_framework = "pytest"
        
        context_info = ""
        if frontend_output:
            context_info += "\n\nFrontend Testing Context:\n"
            structure = frontend_output.get("structure", {})
            components = structure.get("main_components", [])
            context_info += f"Components to test: {', '.join(components)}\n"
            context_info += f"Framework: {frontend_framework}"
        
        if backend_output:
            context_info += "\n\nBackend Testing Context:\n"
            api_spec = backend_output.get("api_spec", {})
            endpoints = api_spec.get("endpoints", [])
            context_info += f"Endpoints to test: {len(endpoints)} API endpoints\n"
            context_info += f"Framework: {backend_framework}"
        
        system_prompt = f"""You are an expert Test Generation agent. Your job is to generate comprehensive unit, integration, and E2E tests.

Project Requirements:
{user_prompt}{context_info}

Your task:
1. Generate unit tests for individual components/functions
2. Create integration tests for API endpoints
3. Write E2E tests for critical user flows
4. Configure test coverage reporting
5. Add test utilities and fixtures
6. Provide commands to run tests

Output ONLY valid JSON in this exact format:
{{
  "test_files": {{
    "tests/unit/test_user_model.py": "import pytest\\nfrom models import User\\n\\ndef test_user_creation():\\n    user = User(email='test@example.com')\\n    assert user.email == 'test@example.com'\\n\\ndef test_user_validation():\\n    with pytest.raises(ValueError):\\n        User(email='invalid')",
    "tests/integration/test_api.py": "import pytest\\nfrom httpx import AsyncClient\\nfrom main import app\\n\\n@pytest.mark.asyncio\\nasync def test_create_user():\\n    async with AsyncClient(app=app, base_url='http://test') as client:\\n        response = await client.post('/api/users', json={{'email': 'test@example.com'}})\\n        assert response.status_code == 200\\n        data = response.json()\\n        assert 'id' in data",
    "tests/e2e/test_user_flow.spec.ts": "import {{ test, expect }} from '@playwright/test'\\n\\ntest('user can sign up and log in', async ({{ page }}) => {{\\n  await page.goto('http://localhost:5173')\\n  await page.click('text=Sign Up')\\n  await page.fill('input[name=email]', 'test@example.com')\\n  await page.fill('input[name=password]', 'password123')\\n  await page.click('button[type=submit]')\\n  await expect(page).toHaveURL(/\\\\/dashboard/)\\n}})",
    "tests/conftest.py": "import pytest\\nimport asyncio\\n\\n@pytest.fixture(scope='session')\\ndef event_loop():\\n    loop = asyncio.new_event_loop()\\n    yield loop\\n    loop.close()",
    "tests/frontend/components/Header.test.tsx": "import {{ render, screen }} from '@testing-library/react'\\nimport {{ describe, it, expect }} from 'vitest'\\nimport Header from '../../src/components/Header'\\n\\ndescribe('Header', () => {{\\n  it('renders app title', () => {{\\n    render(<Header />)\\n    expect(screen.getByText('My App')).toBeInTheDocument()\\n  }})\\n}})"
  }},
  "test_framework": "pytest (backend), vitest (frontend), playwright (E2E)",
  "coverage_config": {{
    "file": ".coveragerc",
    "content": "[run]\\nsource = .\\nomit = */tests/*, */venv/*, */__pycache__/*\\n\\n[report]\\nexclude_lines = pragma: no cover, def __repr__, raise AssertionError, raise NotImplementedError"
  }},
  "run_commands": [
    "# Backend tests",
    "pip install pytest pytest-asyncio pytest-cov httpx",
    "pytest tests/ --cov --cov-report=html",
    "",
    "# Frontend tests", 
    "npm install -D vitest @testing-library/react @testing-library/jest-dom",
    "npm test",
    "",
    "# E2E tests",
    "npm install -D @playwright/test",
    "npx playwright test"
  ],
  "estimated_coverage": "85%"
}}

Quality expectations:
- Tests should cover happy paths and edge cases
- Include proper setup and teardown in fixtures
- Use mocks for external dependencies
- Test error handling and validation
- Follow AAA pattern (Arrange, Act, Assert)
- Add descriptive test names and docstrings
- Include both positive and negative test cases
- Test authentication and authorization where applicable"""

        # Call LLM
        response, tokens = await self.call_llm(
            user_prompt=user_prompt + context_info,
            system_prompt=system_prompt,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=3000
        )
        
        # Parse JSON response
        data = self.parse_json_response(response)
        
        # Add metadata
        data["_tokens_used"] = tokens
        data["_model_used"] = "gpt-4o"
        data["_agent"] = self.name
        
        return data

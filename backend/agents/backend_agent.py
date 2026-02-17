"""
BackendAgent: Generates complete backend API code with proper structure.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry


@AgentRegistry.register
class BackendAgent(BaseAgent):
    """
    Generates backend API code with proper structure.
    
    Input:
        - user_prompt: str
        - stack_output: dict (optional, from StackSelectorAgent)
        - database_output: dict (optional, from DatabaseAgent)
    
    Output:
        - files: dict with file paths and content
        - api_spec: dict with endpoints and models
        - setup_instructions: list of setup commands
    """
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        
        if "user_prompt" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'user_prompt'")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        
        # Check required fields
        required = ["files", "api_spec", "setup_instructions"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        
        # Validate files is a dict
        if not isinstance(result["files"], dict):
            raise AgentValidationError(f"{self.name}: files must be a dictionary")
        
        # Validate api_spec has endpoints
        if "endpoints" not in result["api_spec"]:
            raise AgentValidationError(f"{self.name}: api_spec must have 'endpoints' field")
        
        if not isinstance(result["api_spec"]["endpoints"], list):
            raise AgentValidationError(f"{self.name}: api_spec endpoints must be a list")
        
        # Validate setup_instructions is a list
        if not isinstance(result["setup_instructions"], list):
            raise AgentValidationError(f"{self.name}: setup_instructions must be a list")
        
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = context.get("user_prompt", "")
        stack_output = context.get("stack_output", {})
        database_output = context.get("database_output", {})
        
        # Build context from previous agents
        backend_framework = "FastAPI"
        backend_language = "Python"
        database_type = "PostgreSQL"
        
        if stack_output:
            backend = stack_output.get("backend", {})
            backend_framework = backend.get("framework", "FastAPI")
            backend_language = backend.get("language", "Python")
            database = stack_output.get("database", {})
            database_type = database.get("primary", "PostgreSQL")
        
        # Include database schema if available
        schema_info = ""
        if database_output:
            tables = database_output.get("schema", {}).get("tables", [])
            if tables:
                schema_info = "\n\nDatabase Schema:\n"
                for table in tables:
                    schema_info += f"- {table.get('name', 'unknown')}: "
                    schema_info += ", ".join([col.get("name", "") for col in table.get("columns", [])])
                    schema_info += "\n"
        
        context_info = f"\n\nTechnology Context:\nFramework: {backend_framework}\nLanguage: {backend_language}\nDatabase: {database_type}{schema_info}"
        
        system_prompt = f"""You are an expert Backend Development agent. Your job is to generate complete, production-ready backend API code.

Project Requirements:
{user_prompt}{context_info}

Your task:
1. Generate main application file with server setup
2. Create requirements/dependencies file
3. Define data models (matching database schema if provided)
4. Implement API routes/endpoints with proper HTTP methods
5. Add error handling and validation
6. Include environment configuration (.env.example)
7. Add Dockerfile for containerization
8. Provide setup instructions

Output ONLY valid JSON in this exact format:
{{
  "files": {{
    "main.py": "from fastapi import FastAPI, HTTPException\\nfrom fastapi.middleware.cors import CORSMiddleware\\nimport os\\n\\napp = FastAPI(title='API', version='1.0.0')\\n\\napp.add_middleware(\\n    CORSMiddleware,\\n    allow_origins=['*'],\\n    allow_credentials=True,\\n    allow_methods=['*'],\\n    allow_headers=['*']\\n)\\n\\n@app.get('/')\\nasync def root():\\n    return {{'message': 'API Running'}}",
    "requirements.txt": "fastapi==0.110.1\\nuvicorn[standard]==0.25.0\\npydantic==2.6.0\\npython-dotenv==1.0.0\\nsqlalchemy==2.0.25\\npsycopg2-binary==2.9.9\\nalembic==1.13.1",
    "models.py": "from sqlalchemy import Column, Integer, String, DateTime\\nfrom sqlalchemy.ext.declarative import declarative_base\\nfrom datetime import datetime\\n\\nBase = declarative_base()\\n\\nclass User(Base):\\n    __tablename__ = 'users'\\n    id = Column(Integer, primary_key=True)\\n    email = Column(String, unique=True, nullable=False)\\n    created_at = Column(DateTime, default=datetime.utcnow)",
    "routes/users.py": "from fastapi import APIRouter, HTTPException\\nfrom pydantic import BaseModel\\n\\nrouter = APIRouter(prefix='/api/users', tags=['users'])\\n\\nclass UserCreate(BaseModel):\\n    email: str\\n\\n@router.get('/')\\nasync def list_users():\\n    return {{'users': []}}\\n\\n@router.post('/')\\nasync def create_user(user: UserCreate):\\n    return {{'id': 1, 'email': user.email}}",
    ".env.example": "DATABASE_URL=postgresql://user:password@localhost:5432/dbname\\nJWT_SECRET=your-secret-key-here\\nCORS_ORIGINS=http://localhost:3000,http://localhost:5173\\nENVIRONMENT=development",
    "Dockerfile": "FROM python:3.11-slim\\nWORKDIR /app\\nCOPY requirements.txt .\\nRUN pip install --no-cache-dir -r requirements.txt\\nCOPY . .\\nEXPOSE 8000\\nCMD [\\"uvicorn\\", \\"main:app\\", \\"--host\\", \\"0.0.0.0\\", \\"--port\\", \\"8000\\"]"
  }},
  "api_spec": {{
    "endpoints": [
      {{
        "path": "/api/users",
        "method": "GET",
        "description": "Get all users",
        "auth_required": false,
        "request_body": null,
        "response": {{"type": "array", "items": "User"}}
      }},
      {{
        "path": "/api/users",
        "method": "POST",
        "description": "Create a new user",
        "auth_required": false,
        "request_body": {{"email": "string"}},
        "response": {{"type": "object", "properties": {{"id": "integer", "email": "string"}}}}
      }}
    ],
    "models": [
      {{
        "name": "User",
        "fields": [
          {{"name": "id", "type": "int", "description": "Unique identifier"}},
          {{"name": "email", "type": "string", "description": "User email address"}},
          {{"name": "created_at", "type": "datetime", "description": "Creation timestamp"}}
        ]
      }}
    ]
  }},
  "setup_instructions": [
    "pip install -r requirements.txt",
    "cp .env.example .env",
    "Edit .env with your database credentials",
    "uvicorn main:app --reload"
  ]
}}

Quality expectations:
- Follow framework best practices and conventions
- Include proper error handling (try-catch, HTTP exceptions)
- Add input validation using Pydantic (FastAPI) or similar
- Use environment variables for configuration
- Include CORS configuration
- Add health check endpoint
- Follow RESTful API design principles
- Include proper HTTP status codes
- Add request/response models with type hints"""

        # Call LLM
        response, tokens = await self.call_llm(
            user_prompt=user_prompt + context_info,
            system_prompt=system_prompt,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=4000
        )
        
        # Parse JSON response
        data = self.parse_json_response(response)
        
        # Add metadata
        data["_tokens_used"] = tokens
        data["_model_used"] = "gpt-4o"
        data["_agent"] = self.name
        
        return data

"""
DocumentationAgent: Generates comprehensive documentation for the project.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry


@AgentRegistry.register
class DocumentationAgent(BaseAgent):
    """
    Generates comprehensive documentation.
    
    Input:
        - user_prompt: str
        - All other agent outputs (optional)
    
    Output:
        - files: dict with documentation files
        - api_documentation: dict with API docs specification
        - architecture_diagram: str (Mermaid diagram)
        - setup_guide: str
    """
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        
        if "user_prompt" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'user_prompt'")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        
        # Check required fields
        required = ["files", "api_documentation", "architecture_diagram", "setup_guide"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        
        # Validate files is a dict
        if not isinstance(result["files"], dict):
            raise AgentValidationError(f"{self.name}: files must be a dictionary")
        
        # Must include README.md
        if "README.md" not in result["files"]:
            raise AgentValidationError(f"{self.name}: Must include README.md")
        
        # Validate api_documentation is a dict
        if not isinstance(result["api_documentation"], dict):
            raise AgentValidationError(f"{self.name}: api_documentation must be a dictionary")
        
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = context.get("user_prompt", "")
        
        # Gather information from all previous agents
        stack_output = context.get("stack_output", {})
        backend_output = context.get("backend_output", {})
        frontend_output = context.get("frontend_output", {})
        database_output = context.get("database_output", {})
        deployment_output = context.get("deployment_output", {})
        
        # Build comprehensive context
        context_info = "\n\nProject Context:"
        
        if stack_output:
            context_info += f"\n\nTechnology Stack:"
            frontend = stack_output.get("frontend", {})
            backend = stack_output.get("backend", {})
            database = stack_output.get("database", {})
            context_info += f"\n- Frontend: {frontend.get('framework', 'N/A')}"
            context_info += f"\n- Backend: {backend.get('framework', 'N/A')}"
            context_info += f"\n- Database: {database.get('primary', 'N/A')}"
        
        if backend_output:
            api_spec = backend_output.get("api_spec", {})
            endpoints = api_spec.get("endpoints", [])
            context_info += f"\n\nAPI: {len(endpoints)} endpoints"
        
        if database_output:
            schema = database_output.get("schema", {})
            tables = schema.get("tables", [])
            context_info += f"\n\nDatabase: {len(tables)} tables"
        
        system_prompt = f"""You are an expert Documentation agent. Your job is to create comprehensive, well-structured documentation for the entire project.

Project Requirements:
{user_prompt}{context_info}

Your task:
1. Create a detailed README.md with project overview, features, setup, and usage
2. Generate API documentation (OpenAPI/Swagger spec)
3. Document architecture with Mermaid diagrams
4. Write contribution guidelines
5. Create setup and deployment guides
6. Document code structure and conventions

Output ONLY valid JSON in this exact format:
{{
  "files": {{
    "README.md": "# Project Name\\n\\n## Overview\\nBrief description of the project and its purpose.\\n\\n## Features\\n- Feature 1\\n- Feature 2\\n\\n## Tech Stack\\n- **Frontend**: React + TypeScript\\n- **Backend**: FastAPI + Python\\n- **Database**: PostgreSQL\\n\\n## Getting Started\\n\\n### Prerequisites\\n- Node.js 18+\\n- Python 3.11+\\n- PostgreSQL 15+\\n\\n### Installation\\n```bash\\n# Clone the repository\\ngit clone https://github.com/username/project.git\\n\\n# Install backend dependencies\\ncd backend\\npip install -r requirements.txt\\n\\n# Install frontend dependencies\\ncd ../frontend\\nnpm install\\n```\\n\\n### Running the Application\\n```bash\\n# Start backend\\ncd backend\\nuvicorn main:app --reload\\n\\n# Start frontend\\ncd frontend\\nnpm run dev\\n```\\n\\n## Usage\\nDetailed usage instructions...\\n\\n## API Documentation\\nSee [API.md](docs/API.md) for complete API documentation.\\n\\n## Contributing\\nSee [CONTRIBUTING.md](docs/CONTRIBUTING.md) for contribution guidelines.\\n\\n## License\\nMIT License",
    "docs/API.md": "# API Documentation\\n\\n## Base URL\\n`http://localhost:8000/api`\\n\\n## Authentication\\nUse Bearer token in Authorization header:\\n```\\nAuthorization: Bearer <token>\\n```\\n\\n## Endpoints\\n\\n### Users\\n\\n#### GET /api/users\\nGet all users.\\n\\n**Response**\\n```json\\n{{\\n  \\"users\\": [\\n    {{\\"id\\": 1, \\"email\\": \\"user@example.com\\"}}\\n  ]\\n}}\\n```\\n\\n#### POST /api/users\\nCreate a new user.\\n\\n**Request Body**\\n```json\\n{{\\n  \\"email\\": \\"user@example.com\\",\\n  \\"password\\": \\"secure-password\\"\\n}}\\n```\\n\\n**Response**\\n```json\\n{{\\n  \\"id\\": 1,\\n  \\"email\\": \\"user@example.com\\",\\n  \\"created_at\\": \\"2024-01-01T00:00:00Z\\"\\n}}\\n```",
    "docs/ARCHITECTURE.md": "# Architecture\\n\\n## Overview\\nThis project follows a modern three-tier architecture with separate frontend, backend, and database layers.\\n\\n## System Architecture\\n\\n```mermaid\\ngraph TD\\n    A[Client Browser] -->|HTTPS| B[Frontend - React]\\n    B -->|REST API| C[Backend - FastAPI]\\n    C -->|SQL| D[Database - PostgreSQL]\\n    C -->|Cache| E[Redis]\\n```\\n\\n## Frontend Architecture\\n- **Framework**: React 18 with TypeScript\\n- **State Management**: Context API\\n- **Styling**: TailwindCSS\\n- **Build Tool**: Vite\\n\\n## Backend Architecture\\n- **Framework**: FastAPI\\n- **ORM**: SQLAlchemy\\n- **Authentication**: JWT\\n- **API Style**: RESTful\\n\\n## Database Schema\\nSee [DATABASE.md](DATABASE.md) for detailed schema documentation.\\n\\n## Deployment\\n- **Frontend**: Vercel\\n- **Backend**: Railway\\n- **Database**: Railway PostgreSQL",
    "docs/CONTRIBUTING.md": "# Contributing Guidelines\\n\\n## Getting Started\\n1. Fork the repository\\n2. Create a feature branch: `git checkout -b feature/amazing-feature`\\n3. Make your changes\\n4. Run tests: `pytest` and `npm test`\\n5. Commit your changes: `git commit -m 'Add amazing feature'`\\n6. Push to the branch: `git push origin feature/amazing-feature`\\n7. Open a Pull Request\\n\\n## Code Style\\n- **Python**: Follow PEP 8, use Black for formatting\\n- **TypeScript**: Follow Airbnb style guide, use Prettier\\n- **Commits**: Use conventional commits (feat:, fix:, docs:, etc.)\\n\\n## Testing\\n- Write tests for all new features\\n- Maintain at least 80% code coverage\\n- Run full test suite before submitting PR\\n\\n## Pull Request Process\\n1. Update README.md with details of changes if applicable\\n2. Update API documentation if endpoints change\\n3. Ensure all tests pass\\n4. Request review from maintainers"
  }},
  "api_documentation": {{
    "format": "OpenAPI 3.0",
    "content": "openapi: 3.0.0\\ninfo:\\n  title: Project API\\n  version: 1.0.0\\n  description: RESTful API for the application\\npaths:\\n  /api/users:\\n    get:\\n      summary: List all users\\n      responses:\\n        '200':\\n          description: Successful response\\n          content:\\n            application/json:\\n              schema:\\n                type: array\\n                items:\\n                  $ref: '#/components/schemas/User'\\n    post:\\n      summary: Create a new user\\n      requestBody:\\n        required: true\\n        content:\\n          application/json:\\n            schema:\\n              $ref: '#/components/schemas/UserCreate'\\n      responses:\\n        '201':\\n          description: User created\\ncomponents:\\n  schemas:\\n    User:\\n      type: object\\n      properties:\\n        id:\\n          type: integer\\n        email:\\n          type: string\\n    UserCreate:\\n      type: object\\n      required:\\n        - email\\n        - password\\n      properties:\\n        email:\\n          type: string\\n        password:\\n          type: string"
  }},
  "architecture_diagram": "graph TD\\n    A[Client] -->|HTTPS| B[Frontend]\\n    B -->|REST API| C[Backend]\\n    C -->|ORM| D[Database]\\n    C -->|Cache| E[Redis]\\n    F[CI/CD] -->|Deploy| B\\n    F -->|Deploy| C",
  "setup_guide": "# Setup Guide\\n\\n## Prerequisites\\n- Node.js 18+\\n- Python 3.11+\\n- PostgreSQL 15+\\n- Git\\n\\n## Step 1: Clone Repository\\n```bash\\ngit clone https://github.com/username/project.git\\ncd project\\n```\\n\\n## Step 2: Database Setup\\n```bash\\n# Create database\\ncreatedb myapp\\n\\n# Run migrations\\ncd backend\\nalembic upgrade head\\n```\\n\\n## Step 3: Backend Setup\\n```bash\\ncd backend\\npython -m venv venv\\nsource venv/bin/activate\\npip install -r requirements.txt\\ncp .env.example .env\\n# Edit .env with your configuration\\nuvicorn main:app --reload\\n```\\n\\n## Step 4: Frontend Setup\\n```bash\\ncd frontend\\nnpm install\\nnpm run dev\\n```\\n\\n## Step 5: Verify Installation\\n- Backend: http://localhost:8000\\n- Frontend: http://localhost:5173\\n- API Docs: http://localhost:8000/docs"
}}

Quality expectations:
- Clear, concise documentation
- Include code examples and usage samples
- Use proper Markdown formatting
- Add Mermaid diagrams for visual representation
- Document all environment variables and configuration
- Include troubleshooting section
- Add links between related documentation files
- Keep documentation up-to-date with code"""

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

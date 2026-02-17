"""
DeploymentAgent: Creates deployment configurations for Docker, CI/CD, and cloud platforms.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry


@AgentRegistry.register
class DeploymentAgent(BaseAgent):
    """
    Creates deployment configurations and instructions.
    
    Input:
        - user_prompt: str
        - stack_output: dict (optional, from StackSelectorAgent)
    
    Output:
        - files: dict with deployment configuration files
        - deployment_targets: list of deployment target specifications
        - environment_variables: list of required environment variables
    """
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        
        if "user_prompt" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'user_prompt'")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        
        # Check required fields
        required = ["files", "deployment_targets", "environment_variables"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        
        # Validate files is a dict
        if not isinstance(result["files"], dict):
            raise AgentValidationError(f"{self.name}: files must be a dictionary")
        
        # Validate deployment_targets is a list
        if not isinstance(result["deployment_targets"], list):
            raise AgentValidationError(f"{self.name}: deployment_targets must be a list")
        
        # Validate environment_variables is a list
        if not isinstance(result["environment_variables"], list):
            raise AgentValidationError(f"{self.name}: environment_variables must be a list")
        
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = context.get("user_prompt", "")
        stack_output = context.get("stack_output", {})
        
        # Determine deployment platforms from stack
        frontend_platform = "Vercel"
        backend_platform = "Railway"
        
        if stack_output:
            deployment = stack_output.get("deployment", {})
            frontend_platform = deployment.get("frontend", "Vercel")
            backend_platform = deployment.get("backend", "Railway")
        
        context_info = f"\n\nDeployment Context:\nFrontend Platform: {frontend_platform}\nBackend Platform: {backend_platform}"
        
        system_prompt = f"""You are an expert Deployment Configuration agent. Your job is to create complete deployment configurations for modern cloud platforms.

Project Requirements:
{user_prompt}{context_info}

Your task:
1. Generate Dockerfile for containerization
2. Create docker-compose.yml for local development
3. Configure CI/CD pipeline (GitHub Actions)
4. Add platform-specific configs (Railway, Vercel, etc.)
5. Define environment variables and secrets
6. Provide deployment instructions

Output ONLY valid JSON in this exact format:
{{
  "files": {{
    "Dockerfile": "FROM python:3.11-slim\\nWORKDIR /app\\nCOPY requirements.txt .\\nRUN pip install --no-cache-dir -r requirements.txt\\nCOPY . .\\nEXPOSE 8000\\nCMD [\\"uvicorn\\", \\"main:app\\", \\"--host\\", \\"0.0.0.0\\", \\"--port\\", \\"8000\\"]",
    "docker-compose.yml": "version: '3.8'\\nservices:\\n  backend:\\n    build: .\\n    ports:\\n      - \\"8000:8000\\"\\n    environment:\\n      - DATABASE_URL=postgresql://user:password@db:5432/myapp\\n    depends_on:\\n      - db\\n  db:\\n    image: postgres:15-alpine\\n    environment:\\n      - POSTGRES_USER=user\\n      - POSTGRES_PASSWORD=password\\n      - POSTGRES_DB=myapp\\n    volumes:\\n      - postgres_data:/var/lib/postgresql/data\\nvolumes:\\n  postgres_data:",
    ".github/workflows/deploy.yml": "name: Deploy\\n\\non:\\n  push:\\n    branches: [main]\\n\\njobs:\\n  deploy:\\n    runs-on: ubuntu-latest\\n    steps:\\n      - uses: actions/checkout@v3\\n      - name: Deploy to Railway\\n        env:\\n          RAILWAY_TOKEN: \\${{{{ secrets.RAILWAY_TOKEN }}}}\\n        run: |\\n          npm install -g railway\\n          railway up",
    "railway.json": "{{\\n  \\"build\\": {{\\n    \\"builder\\": \\"DOCKERFILE\\",\\n    \\"dockerfilePath\\": \\"Dockerfile\\"\\n  }},\\n  \\"deploy\\": {{\\n    \\"restartPolicyType\\": \\"ON_FAILURE\\",\\n    \\"restartPolicyMaxRetries\\": 10\\n  }}\\n}}",
    "vercel.json": "{{\\n  \\"builds\\": [\\n    {{\\n      \\"src\\": \\"package.json\\",\\n      \\"use\\": \\"@vercel/static-build\\",\\n      \\"config\\": {{ \\"distDir\\": \\"dist\\" }}\\n    }}\\n  ],\\n  \\"routes\\": [\\n    {{ \\"src\\": \\"/api/(.*)\\", \\"dest\\": \\"https://api.yourdomain.com/api/$1\\" }},\\n    {{ \\"src\\": \\"/(.*)\\", \\"dest\\": \\"/index.html\\" }}\\n  ]\\n}}",
    ".dockerignore": "node_modules\\n__pycache__\\n*.pyc\\n.env\\n.git\\n.gitignore\\nREADME.md\\ntests\\n*.log",
    "render.yaml": "services:\\n  - type: web\\n    name: backend\\n    env: python\\n    buildCommand: pip install -r requirements.txt\\n    startCommand: uvicorn main:app --host 0.0.0.0 --port \\$PORT\\n    envVars:\\n      - key: DATABASE_URL\\n        sync: false\\n      - key: JWT_SECRET\\n        generateValue: true"
  }},
  "deployment_targets": [
    {{
      "name": "Production",
      "platform": "Railway",
      "type": "backend",
      "instructions": [
        "Install Railway CLI: npm install -g railway",
        "Login: railway login",
        "Link project: railway link",
        "Deploy: railway up",
        "Set environment variables in Railway dashboard"
      ]
    }},
    {{
      "name": "Production",
      "platform": "Vercel",
      "type": "frontend",
      "instructions": [
        "Install Vercel CLI: npm install -g vercel",
        "Login: vercel login",
        "Deploy: vercel --prod",
        "Configure environment variables in Vercel dashboard"
      ]
    }},
    {{
      "name": "Staging",
      "platform": "Docker",
      "type": "full-stack",
      "instructions": [
        "Build: docker-compose build",
        "Run: docker-compose up -d",
        "View logs: docker-compose logs -f",
        "Stop: docker-compose down"
      ]
    }}
  ],
  "environment_variables": [
    {{
      "name": "DATABASE_URL",
      "required": true,
      "description": "PostgreSQL connection string",
      "example": "postgresql://user:password@host:5432/dbname"
    }},
    {{
      "name": "JWT_SECRET",
      "required": true,
      "description": "Secret key for JWT token signing",
      "example": "your-secret-key-min-32-chars"
    }},
    {{
      "name": "OPENAI_API_KEY",
      "required": false,
      "description": "OpenAI API key for AI features",
      "example": "sk-..."
    }},
    {{
      "name": "CORS_ORIGINS",
      "required": true,
      "description": "Allowed CORS origins (comma-separated)",
      "example": "https://yourdomain.com,https://www.yourdomain.com"
    }},
    {{
      "name": "ENVIRONMENT",
      "required": true,
      "description": "Environment name",
      "example": "production|staging|development"
    }}
  ]
}}

Quality expectations:
- Multi-stage Docker builds for optimized images
- Proper .dockerignore to exclude unnecessary files
- GitHub Actions with proper secrets management
- Platform-specific optimizations (Railway, Vercel, Render)
- Health checks and restart policies
- Secure environment variable handling
- Clear deployment instructions for each platform"""

        # Call LLM
        response, tokens = await self.call_llm(
            user_prompt=user_prompt + context_info,
            system_prompt=system_prompt,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=1500
        )
        
        # Parse JSON response
        data = self.parse_json_response(response)
        
        # Add metadata
        data["_tokens_used"] = tokens
        data["_model_used"] = "gpt-4o"
        data["_agent"] = self.name
        
        return data

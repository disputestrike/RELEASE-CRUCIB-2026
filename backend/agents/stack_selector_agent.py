"""
StackSelectorAgent: Selects optimal technology stack based on requirements.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry


@AgentRegistry.register
class StackSelectorAgent(BaseAgent):
    """
    Selects optimal technology stack based on requirements.
    
    Input:
        - user_prompt: str
        - planner_output: dict (optional, from PlannerAgent)
    
    Output:
        - frontend: dict with framework, language, styling, state_management, reasoning
        - backend: dict with framework, language, reasoning
        - database: dict with primary, caching, reasoning
        - deployment: dict with frontend, backend, reasoning
        - additional_tools: list
        - overall_reasoning: str
    """
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        
        if "user_prompt" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'user_prompt'")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        
        # Check required top-level fields
        required = ["frontend", "backend", "database", "deployment", "additional_tools", "overall_reasoning"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        
        # Validate frontend
        frontend_fields = ["framework", "language", "styling", "state_management", "reasoning"]
        for field in frontend_fields:
            if field not in result["frontend"]:
                raise AgentValidationError(f"{self.name}: Missing frontend field '{field}'")
        
        # Validate backend
        backend_fields = ["framework", "language", "reasoning"]
        for field in backend_fields:
            if field not in result["backend"]:
                raise AgentValidationError(f"{self.name}: Missing backend field '{field}'")
        
        # Validate database
        database_fields = ["primary", "caching", "reasoning"]
        for field in database_fields:
            if field not in result["database"]:
                raise AgentValidationError(f"{self.name}: Missing database field '{field}'")
        
        # Validate deployment
        deployment_fields = ["frontend", "backend", "reasoning"]
        for field in deployment_fields:
            if field not in result["deployment"]:
                raise AgentValidationError(f"{self.name}: Missing deployment field '{field}'")
        
        # Validate additional_tools is a list
        if not isinstance(result["additional_tools"], list):
            raise AgentValidationError(f"{self.name}: additional_tools must be a list")
        
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = context.get("user_prompt", "")
        planner_output = context.get("planner_output", {})
        
        # Include planner context if available
        context_info = ""
        if planner_output:
            summary = planner_output.get("project_summary", "")
            complexity = planner_output.get("complexity", "")
            context_info = f"\n\nProject Context:\nSummary: {summary}\nComplexity: {complexity}"
        
        system_prompt = f"""You are an expert Technology Stack Selector agent. Your job is to recommend the optimal technology stack based on project requirements.

Project Requirements:
{user_prompt}{context_info}

Consider:
1. Project type and scale
2. Team expertise (assume modern web development skills)
3. Performance requirements
4. Development speed vs. scalability
5. Cost and hosting considerations
6. Ecosystem maturity and community support

Output ONLY valid JSON in this exact format:
{{
  "frontend": {{
    "framework": "React|Vue|Angular|Next.js|Svelte",
    "language": "TypeScript|JavaScript",
    "styling": "TailwindCSS|styled-components|MUI|CSS Modules",
    "state_management": "Redux|Zustand|Context|Recoil|none",
    "reasoning": "2-3 sentences explaining why this frontend stack"
  }},
  "backend": {{
    "framework": "FastAPI|Express|NestJS|Django|Flask",
    "language": "Python|Node.js|Go|TypeScript",
    "reasoning": "2-3 sentences explaining why this backend stack"
  }},
  "database": {{
    "primary": "PostgreSQL|MySQL|MongoDB|SQLite",
    "caching": "Redis|Memcached|none",
    "reasoning": "2-3 sentences explaining why this database choice"
  }},
  "deployment": {{
    "frontend": "Vercel|Netlify|Cloudflare Pages|AWS S3",
    "backend": "Railway|Render|Fly.io|AWS|Heroku",
    "reasoning": "2-3 sentences explaining deployment choices"
  }},
  "additional_tools": ["Prisma", "tRPC", "Docker", "GitHub Actions"],
  "overall_reasoning": "High-level 3-4 sentence justification for the complete stack"
}}

Quality expectations:
- Choose modern, production-ready technologies
- Balance between developer experience and performance
- Consider deployment and maintenance costs
- Ensure all parts of the stack work well together"""

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

"""
PlannerAgent: Analyzes requirements and creates structured execution plan with task dependencies.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry


@AgentRegistry.register
class PlannerAgent(BaseAgent):
    """
    Analyzes requirements and creates structured execution plan.
    
    Input:
        - user_prompt: str (>10 characters)
    
    Output:
        - project_summary: str
        - estimated_duration: str
        - complexity: str (low|medium|high)
        - tasks: List[dict] with id, title, description, agent, dependencies, estimated_complexity
    """
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        
        if "user_prompt" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'user_prompt'")
        
        prompt = context["user_prompt"]
        if not isinstance(prompt, str) or len(prompt) <= 10:
            raise AgentValidationError(
                f"{self.name}: user_prompt must be a string with >10 characters"
            )
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        
        # Check required fields
        required = ["project_summary", "estimated_duration", "complexity", "tasks"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        
        # Validate complexity
        if result["complexity"] not in ["low", "medium", "high"]:
            raise AgentValidationError(
                f"{self.name}: complexity must be 'low', 'medium', or 'high'"
            )
        
        # Validate tasks
        tasks = result["tasks"]
        if not isinstance(tasks, list):
            raise AgentValidationError(f"{self.name}: tasks must be a list")
        
        if len(tasks) < 5 or len(tasks) > 15:
            raise AgentValidationError(
                f"{self.name}: Must generate 5-15 tasks, got {len(tasks)}"
            )
        
        # Validate each task
        for i, task in enumerate(tasks):
            required_task_fields = ["id", "title", "description", "agent", "dependencies", "estimated_complexity"]
            for field in required_task_fields:
                if field not in task:
                    raise AgentValidationError(
                        f"{self.name}: Task {i} missing required field '{field}'"
                    )
            
            if task["estimated_complexity"] not in ["low", "medium", "high"]:
                raise AgentValidationError(
                    f"{self.name}: Task {i} complexity must be 'low', 'medium', or 'high'"
                )
        
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = context.get("user_prompt", "")
        
        system_prompt = """You are an expert Project Planner agent. Your job is to analyze user requirements and create a structured, detailed execution plan.

Requirements:
1. Break down the project into 5-15 clear, executable tasks
2. Each task should be assigned to a specific agent (e.g., FrontendAgent, BackendAgent, DatabaseAgent, etc.)
3. Define dependencies between tasks (task IDs that must complete first)
4. Estimate complexity for each task and the overall project
5. Provide realistic time estimates

Available agents for task assignment:
- PlannerAgent (planning and coordination)
- StackSelectorAgent (technology stack selection)
- DesignAgent (UI/UX design)
- DatabaseAgent (database schema and migrations)
- BackendAgent (backend API development)
- FrontendAgent (frontend development)
- TestGenerationAgent (test generation)
- SecurityAgent (security audit)
- DeploymentAgent (deployment configuration)
- DocumentationAgent (documentation)

Output ONLY valid JSON in this exact format:
{
  "project_summary": "Brief 2-3 sentence description of the project",
  "estimated_duration": "X-Y hours/days/weeks",
  "complexity": "low|medium|high",
  "tasks": [
    {
      "id": 1,
      "title": "Clear task name",
      "description": "Detailed description of what needs to be done",
      "agent": "AgentClassName",
      "dependencies": [0],
      "estimated_complexity": "low|medium|high"
    }
  ]
}

Quality expectations:
- Tasks should be ordered logically (dependencies first)
- Each task should be specific and actionable
- Use realistic complexity estimates
- Include all necessary phases: planning, design, development, testing, deployment, documentation"""

        # Call LLM
        response, tokens = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=2000
        )
        
        # Parse JSON response
        data = self.parse_json_response(response)
        
        # Add metadata
        data["_tokens_used"] = tokens
        data["_model_used"] = "gpt-4o"
        data["_agent"] = self.name
        
        return data

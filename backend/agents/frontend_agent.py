"""
FrontendAgent: Generates complete, validated frontend code.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry


@AgentRegistry.register
class FrontendAgent(BaseAgent):
    """
    Generates complete frontend code with proper structure.
    
    Input:
        - user_prompt: str
        - stack_output: dict (optional, from StackSelectorAgent)
        - design_output: dict (optional, from DesignAgent)
    
    Output:
        - files: dict with file paths and content
        - structure: dict with architecture overview
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
        required = ["files", "structure", "setup_instructions"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        
        # Validate files is a dict
        if not isinstance(result["files"], dict):
            raise AgentValidationError(f"{self.name}: files must be a dictionary")
        
        # Must include package.json
        if "package.json" not in result["files"]:
            raise AgentValidationError(f"{self.name}: Must include package.json")
        
        # Validate package.json is valid JSON
        try:
            import json
            json.loads(result["files"]["package.json"])
        except json.JSONDecodeError as e:
            raise AgentValidationError(f"{self.name}: package.json must be valid JSON: {e}")
        
        # Validate structure has required fields
        structure_fields = ["description", "entry_point", "main_components"]
        for field in structure_fields:
            if field not in result["structure"]:
                raise AgentValidationError(f"{self.name}: structure missing field '{field}'")
        
        # Validate setup_instructions is a list
        if not isinstance(result["setup_instructions"], list):
            raise AgentValidationError(f"{self.name}: setup_instructions must be a list")
        
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = context.get("user_prompt", "")
        stack_output = context.get("stack_output", {})
        design_output = context.get("design_output", {})
        
        # Build context from previous agents
        framework = "React"
        language = "TypeScript"
        styling = "TailwindCSS"
        state_mgmt = "Context"
        
        if stack_output:
            frontend = stack_output.get("frontend", {})
            framework = frontend.get("framework", "React")
            language = frontend.get("language", "TypeScript")
            styling = frontend.get("styling", "TailwindCSS")
            state_mgmt = frontend.get("state_management", "Context")
        
        # Include design system if available
        design_info = ""
        if design_output:
            design_system = design_output.get("design_system", {})
            colors = design_system.get("colors", {})
            if colors:
                design_info = "\n\nDesign System:\n"
                design_info += f"Primary Color: {colors.get('primary', '#1A1A1A')}\n"
                design_info += f"Secondary Color: {colors.get('secondary', '#808080')}\n"
                design_info += f"Styling: {styling}"
        
        context_info = f"\n\nTechnology Context:\nFramework: {framework}\nLanguage: {language}\nStyling: {styling}\nState Management: {state_mgmt}{design_info}"
        
        system_prompt = f"""You are an expert Frontend Development agent. Generate a complete, runnable Vite React frontend for the request.

Project Requirements:
{user_prompt}{context_info}

Return ONLY valid JSON with this shape:
{{
  "files": {{
    "package.json": "valid JSON string with scripts dev/build/preview and needed dependencies",
    "index.html": "complete Vite HTML entry",
    "src/main.jsx": "ReactDOM.createRoot entry that imports App and CSS",
    "src/App.jsx": "root app component",
    "src/index.css": "global CSS or Tailwind directives"
  }},
  "structure": {{
    "description": "short architecture summary",
    "entry_point": "src/main.jsx",
    "main_components": ["App"]
  }},
  "setup_instructions": ["npm install", "npm run dev"]
}}

Hard requirements:
- Use React 18 with Vite and include a valid package.json.
- Include every imported file in the files object; no dangling imports.
- Include App.jsx or App.js and src/main.jsx.
- Use react-router-dom when the request needs routes or multiple screens.
- Use state management only when the app actually needs shared state.
- Include accessible, responsive UI with loading and error states.
- Keep code self-contained and runnable in a browser preview.
- Do not include markdown fences, prose, comments outside JSON, or placeholder TODO-only files."""

        # Call LLM
        response, tokens = await self.call_llm(
            user_prompt=user_prompt + context_info,
            system_prompt=system_prompt,
            model="claude-haiku-4-5-20251001",
            temperature=0.7,
            max_tokens=6000
        )
        
        # DEBUG: Log raw response before parsing
        logger.info(f"RAW LLM RESPONSE ({len(response)} chars): {response[:300]}...")
        
        # Parse JSON response
        data = self.parse_json_response(response)
        
        # DEBUG: Log parsed result
        logger.info(f"PARSED RESULT: files={len(data.get('files', {}))}, structure={bool(data.get('structure'))}")
        
        # EXPLICIT VALIDATION
        if not data:
            raise AgentValidationError(f"{self.name}: parse_json_response returned empty result")
        
        if not data.get("files"):
            raise AgentValidationError(f"{self.name}: No files in parsed JSON: {list(data.keys())}")
        
        if not isinstance(data["files"], dict) or len(data["files"]) == 0:
            raise AgentValidationError(f"{self.name}: files is not a non-empty dict")
        
        # Add metadata
        data["_tokens_used"] = tokens
        data["_model_used"] = "claude-haiku-4-5-20251001"
        data["_agent"] = self.name
        
        return data


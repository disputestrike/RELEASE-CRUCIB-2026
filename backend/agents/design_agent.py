"""
DesignAgent: Creates UI/UX specifications and design system.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry


@AgentRegistry.register
class DesignAgent(BaseAgent):
    """
    Creates UI/UX specifications and design system.
    
    Input:
        - user_prompt: str
        - stack_output: dict (optional, from StackSelectorAgent)
    
    Output:
        - design_system: dict with colors, typography, spacing, border_radius
        - layouts: list of layout specifications
        - components: list of component specifications
        - mockup_description: str
    """
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        
        if "user_prompt" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'user_prompt'")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        
        # Check required fields
        required = ["design_system", "layouts", "components", "mockup_description"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        
        # Validate design_system
        design_fields = ["colors", "typography", "spacing", "border_radius"]
        for field in design_fields:
            if field not in result["design_system"]:
                raise AgentValidationError(f"{self.name}: Missing design_system field '{field}'")
        
        # Validate colors has required keys
        color_keys = ["primary", "secondary", "accent"]
        for key in color_keys:
            if key not in result["design_system"]["colors"]:
                raise AgentValidationError(f"{self.name}: Missing color '{key}'")
        
        # Validate typography has required keys
        typography_keys = ["heading", "body"]
        for key in typography_keys:
            if key not in result["design_system"]["typography"]:
                raise AgentValidationError(f"{self.name}: Missing typography '{key}'")
        
        # Validate layouts is a list
        if not isinstance(result["layouts"], list):
            raise AgentValidationError(f"{self.name}: layouts must be a list")
        
        # Validate components is a list
        if not isinstance(result["components"], list):
            raise AgentValidationError(f"{self.name}: components must be a list")
        
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = context.get("user_prompt", "")
        stack_output = context.get("stack_output", {})
        
        # Include stack context if available
        context_info = ""
        if stack_output:
            frontend = stack_output.get("frontend", {})
            styling = frontend.get("styling", "")
            if styling:
                context_info = f"\n\nTechnology Context:\nStyling Framework: {styling}"
        
        system_prompt = f"""You are an expert UI/UX Design agent. Your job is to create a comprehensive design system and UI specifications.

Project Requirements:
{user_prompt}{context_info}

Your task:
1. Define a cohesive color palette (primary, secondary, accent, neutral shades)
2. Choose appropriate typography (fonts, sizes, weights)
3. Define spacing system (base unit, scale)
4. Specify border radius and other design tokens
5. Design key layouts (hero, content sections, etc.)
6. Define reusable components (buttons, forms, cards, etc.)
7. Provide overall design direction and mockup description

Output ONLY valid JSON in this exact format:
{{
  "design_system": {{
    "colors": {{
      "primary": "#1A1A1A",
      "secondary": "#808080",
      "accent": "#999999",
      "neutral": {{"50": "#F9FAFB", "100": "#F3F4F6", "900": "#1A1A1A"}},
      "success": "#808080",
      "error": "#1A1A1A",
      "warning": "#999999"
    }},
    "typography": {{
      "heading": "Inter, system-ui, sans-serif",
      "body": "Inter, system-ui, sans-serif",
      "mono": "Fira Code, monospace",
      "sizes": {{"xs": "0.75rem", "sm": "0.875rem", "base": "1rem", "lg": "1.125rem", "xl": "1.25rem", "2xl": "1.5rem", "3xl": "1.875rem", "4xl": "2.25rem"}}
    }},
    "spacing": "8px base unit with 4, 8, 12, 16, 24, 32, 48, 64px scale",
    "border_radius": "8px default, 4px small, 16px large, full for pills"
  }},
  "layouts": [
    {{
      "name": "Hero Section",
      "description": "Full-width hero with gradient background and CTA",
      "components": ["Heading", "Subtitle", "CTA Button", "Feature Image"]
    }},
    {{
      "name": "Feature Grid",
      "description": "3-column grid showcasing key features",
      "components": ["Feature Card", "Icon", "Title", "Description"]
    }}
  ],
  "components": [
    {{
      "name": "Button",
      "variants": ["primary", "secondary", "outline", "ghost"],
      "states": ["default", "hover", "active", "disabled", "loading"],
      "description": "Consistent button styling across the app"
    }},
    {{
      "name": "Input",
      "variants": ["text", "email", "password", "search"],
      "states": ["default", "focus", "error", "disabled"],
      "description": "Form input fields with validation states"
    }}
  ],
  "mockup_description": "Modern, clean interface with bold typography and vibrant accent colors. Minimalist design with generous whitespace. Card-based layout for content organization. Smooth animations and micro-interactions for enhanced UX."
}}

Quality expectations:
- Choose accessible color combinations (WCAG AA compliant)
- Use modern, web-safe fonts or popular Google Fonts
- Create a scalable, consistent design system
- Design should match the project's tone and audience"""

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

"""
Base agent class and validation error for all specialized agents.
All agents inherit from BaseAgent and must implement validate_input, validate_output, and execute.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import os
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic


class AgentValidationError(Exception):
    """Raised when agent input/output validation fails."""
    pass


class BaseAgent(ABC):
    """
    Base class for all specialized agents.
    Each agent must implement:
    - validate_input(context): Validate required context fields
    - validate_output(result): Validate output structure
    - execute(context): Main agent logic
    """
    
    def __init__(self, llm_client: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the agent.
        
        Args:
            llm_client: Optional LLM client (OpenAI, Anthropic, etc.)
            config: Optional configuration dictionary
        """
        self.llm_client = llm_client
        self.config = config or {}
        self.name = self.__class__.__name__
        
    def validate_input(self, context: Dict[str, Any]) -> bool:
        """
        Validate input context. Override in subclasses to add specific validations.
        
        Args:
            context: Input context dictionary
            
        Returns:
            bool: True if valid
            
        Raises:
            AgentValidationError: If validation fails
        """
        if not isinstance(context, dict):
            raise AgentValidationError(f"{self.name}: context must be a dictionary")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """
        Validate output structure. Override in subclasses to add specific validations.
        
        Args:
            result: Output result dictionary
            
        Returns:
            bool: True if valid
            
        Raises:
            AgentValidationError: If validation fails
        """
        if not isinstance(result, dict):
            raise AgentValidationError(f"{self.name}: result must be a dictionary")
        return True
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's main logic.
        
        Args:
            context: Input context dictionary
            
        Returns:
            Dict[str, Any]: Result dictionary
        """
        pass
    
    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the agent: validate input, execute, validate output.
        
        Args:
            context: Input context dictionary
            
        Returns:
            Dict[str, Any]: Result dictionary
        """
        # Validate input
        self.validate_input(context)
        
        # Execute
        result = await self.execute(context)
        
        # Validate output
        self.validate_output(result)
        
        return result
    
    async def call_llm(
        self,
        user_prompt: str,
        system_prompt: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> tuple[str, int]:
        """
        Call LLM with given prompts.
        
        Args:
            user_prompt: User message
            system_prompt: System message
            model: Model name (gpt-4o, gpt-4o-mini, claude-3-5-sonnet-20241022, etc.)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Tuple of (response_text, tokens_used)
        """
        # Try OpenAI models first
        if model.startswith("gpt-"):
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                try:
                    client = AsyncOpenAI(api_key=openai_key)
                    response = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    content = response.choices[0].message.content
                    tokens = response.usage.total_tokens if response.usage else 0
                    return content, tokens
                except Exception as e:
                    raise AgentValidationError(f"{self.name}: OpenAI API call failed: {e}")
        
        # Try Anthropic models
        elif model.startswith("claude-"):
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if anthropic_key:
                try:
                    client = AsyncAnthropic(api_key=anthropic_key)
                    response = await client.messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    content = response.content[0].text
                    tokens = response.usage.input_tokens + response.usage.output_tokens
                    return content, tokens
                except Exception as e:
                    raise AgentValidationError(f"{self.name}: Anthropic API call failed: {e}")
        
        raise AgentValidationError(f"{self.name}: No API key found for model {model}")
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            AgentValidationError: If JSON parsing fails
        """
        try:
            # Extract from markdown code block if present
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            data = json.loads(response)
            return data
        except json.JSONDecodeError as e:
            raise AgentValidationError(
                f"{self.name}: Invalid JSON: {e}\nResponse: {response[:500]}"
            )

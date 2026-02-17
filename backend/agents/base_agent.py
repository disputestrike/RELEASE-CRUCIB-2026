"""
Base Agent class for all tool agents.
Provides common interface and functionality.
"""
from typing import Dict, Any
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, llm_client, config: Dict[str, Any]):
        """
        Initialize agent.
        
        Args:
            llm_client: LLM client for AI operations (can be None for tool agents)
            config: Configuration dictionary
        """
        self.llm_client = llm_client
        self.config = config
        self.name = "BaseAgent"
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent action.
        
        Args:
            context: Input context with action parameters
            
        Returns:
            Dictionary with results
        """
        pass
    
    async def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the agent with a request.
        Wraps execute with error handling.
        
        Args:
            request: Request dictionary
            
        Returns:
            Response dictionary
        """
        try:
            result = await self.execute(request)
            return result
        except Exception as e:
            return {
                "error": str(e),
                "success": False,
                "agent": self.name
            }

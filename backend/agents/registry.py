"""
Agent registry for managing and discovering specialized agents.
Agents register themselves using the @AgentRegistry.register decorator.
"""
from typing import Dict, Type, List
from agents.base_agent import BaseAgent


class AgentRegistry:
    """Registry for all specialized agents."""
    
    _agents: Dict[str, Type[BaseAgent]] = {}
    
    @classmethod
    def register(cls, agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
        """
        Decorator to register an agent class.
        
        Usage:
            @AgentRegistry.register
            class MyAgent(BaseAgent):
                ...
        
        Args:
            agent_class: Agent class to register
            
        Returns:
            The agent class (for decorator pattern)
        """
        agent_name = agent_class.__name__
        cls._agents[agent_name] = agent_class
        return agent_class
    
    @classmethod
    def get_agent(cls, name: str) -> Type[BaseAgent]:
        """
        Get agent class by name.
        
        Args:
            name: Agent class name
            
        Returns:
            Agent class
            
        Raises:
            KeyError: If agent not found
        """
        if name not in cls._agents:
            raise KeyError(f"Agent '{name}' not registered")
        return cls._agents[name]
    
    @classmethod
    def list_agents(cls) -> List[str]:
        """
        List all registered agent names.
        
        Returns:
            List of agent class names
        """
        return list(cls._agents.keys())
    
    @classmethod
    def get_all_agents(cls) -> Dict[str, Type[BaseAgent]]:
        """
        Get all registered agents.
        
        Returns:
            Dictionary of agent name -> agent class
        """
        return cls._agents.copy()

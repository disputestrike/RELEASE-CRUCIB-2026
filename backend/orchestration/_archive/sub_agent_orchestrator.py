"""
Sub-Agent Orchestrator: Enables recursive agent calling and hierarchical decomposition.
Allows agents to spawn specialized sub-agents for complex tasks (like I do).
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SubAgentRequest:
    """Request to spawn a sub-agent"""

    def __init__(self, agent_name: str, context: Dict[str, Any], parent_task_id: str = ""):
        self.agent_name = agent_name
        self.context = context
        self.parent_task_id = parent_task_id
        self.task_id = f"{parent_task_id}_sub_{agent_name}".replace(" ", "_")


class SubAgentResult:
    """Result from sub-agent execution"""

    def __init__(self, task_id: str, agent_name: str, success: bool, result: Dict[str, Any], error: str = ""):
        self.task_id = task_id
        self.agent_name = agent_name
        self.success = success
        self.result = result
        self.error = error
        self.execution_time = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
        }


class SubAgentOrchestrator:
    """
    Orchestrates recursive agent execution.
    Agents can request sub-agents to handle specific sub-tasks.
    """

    def __init__(self, agent_registry: Optional[Dict[str, Any]] = None, max_depth: int = 5):
        """
        Initialize sub-agent orchestrator.

        Args:
            agent_registry: Dict mapping agent names to agent instances
            max_depth: Maximum recursion depth for sub-agents
        """
        self.agent_registry = agent_registry or {}
        self.max_depth = max_depth
        self.execution_tree: Dict[str, Any] = {}
        self.sub_agent_results: List[SubAgentResult] = []

    async def spawn_sub_agent(
        self, request: SubAgentRequest, current_depth: int = 0
    ) -> SubAgentResult:
        """
        Spawn a sub-agent to handle a specific task.
        Like when I decompose a complex problem into specialized sub-tasks.
        """
        import time
        start_time = time.time()

        # Check depth limit
        if current_depth >= self.max_depth:
            return SubAgentResult(
                task_id=request.task_id,
                agent_name=request.agent_name,
                success=False,
                result={},
                error=f"Maximum recursion depth ({self.max_depth}) exceeded",
            )

        # Check if agent exists
        if request.agent_name not in self.agent_registry:
            return SubAgentResult(
                task_id=request.task_id,
                agent_name=request.agent_name,
                success=False,
                result={},
                error=f"Agent not found: {request.agent_name}",
            )

        try:
            agent = self.agent_registry[request.agent_name]

            # Execute sub-agent
            logger.info(f"Spawning sub-agent: {request.agent_name} (depth: {current_depth})")

            result = await agent.execute(request.context)

            execution_time = time.time() - start_time

            sub_result = SubAgentResult(
                task_id=request.task_id,
                agent_name=request.agent_name,
                success=True,
                result=result,
            )
            sub_result.execution_time = execution_time

            self.sub_agent_results.append(sub_result)
            self._record_in_tree(request, sub_result, current_depth)

            return sub_result

        except Exception as e:
            logger.error(f"Sub-agent execution error: {str(e)}")
            execution_time = time.time() - start_time

            sub_result = SubAgentResult(
                task_id=request.task_id,
                agent_name=request.agent_name,
                success=False,
                result={},
                error=str(e),
            )
            sub_result.execution_time = execution_time

            self.sub_agent_results.append(sub_result)
            self._record_in_tree(request, sub_result, current_depth)

            return sub_result

    async def execute_sub_agents_parallel(
        self, requests: List[SubAgentRequest], current_depth: int = 0
    ) -> List[SubAgentResult]:
        """
        Execute multiple sub-agents in parallel (like parallel tool execution).
        """
        tasks = []
        for request in requests:
            task = self.spawn_sub_agent(request, current_depth)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

    async def execute_sub_agents_sequential(
        self, requests: List[SubAgentRequest], current_depth: int = 0
    ) -> List[SubAgentResult]:
        """
        Execute sub-agents sequentially (one depends on output of previous).
        """
        results = []
        for request in requests:
            result = await self.spawn_sub_agent(request, current_depth)
            results.append(result)

            # Pass output as input to next request if needed
            if result.success and len(requests) > 1:
                idx = requests.index(request)
                if idx + 1 < len(requests):
                    requests[idx + 1].context["previous_result"] = result.result

        return results

    def _record_in_tree(self, request: SubAgentRequest, result: SubAgentResult, depth: int):
        """Record sub-agent execution in execution tree"""
        key = request.task_id
        self.execution_tree[key] = {
            "agent": request.agent_name,
            "depth": depth,
            "success": result.success,
            "execution_time": result.execution_time,
            "error": result.error,
        }

    def get_execution_tree(self) -> Dict[str, Any]:
        """Get full execution tree of all sub-agents"""
        return self.execution_tree

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of sub-agent executions"""
        successful = len([r for r in self.sub_agent_results if r.success])
        failed = len(self.sub_agent_results) - successful
        total_time = sum(r.execution_time for r in self.sub_agent_results)

        agent_stats = {}
        for result in self.sub_agent_results:
            if result.agent_name not in agent_stats:
                agent_stats[result.agent_name] = {
                    "runs": 0,
                    "successful": 0,
                    "total_time": 0.0,
                }
            agent_stats[result.agent_name]["runs"] += 1
            if result.success:
                agent_stats[result.agent_name]["successful"] += 1
            agent_stats[result.agent_name]["total_time"] += result.execution_time

        return {
            "total_sub_agents_spawned": len(self.sub_agent_results),
            "successful": successful,
            "failed": failed,
            "total_execution_time": total_time,
            "agent_stats": agent_stats,
            "execution_tree": self.execution_tree,
        }

    def clear_history(self):
        """Clear execution history"""
        self.execution_tree.clear()
        self.sub_agent_results.clear()

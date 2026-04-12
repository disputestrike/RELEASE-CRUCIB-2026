"""
Advanced Agent Orchestrator for CrucibAI
Coordinates multiple agents, handles dependencies, and optimizes execution.
Implements recursive learning-based optimization.
"""

from typing import Dict, Any, List, Optional, Callable
import asyncio
import logging
from datetime import datetime, timezone
from agent_recursive_learning import (
    AgentMemory,
    PerformanceTracker,
    AdaptiveStrategy,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)


class TaskDependency:
    """Represents a dependency between tasks"""

    def __init__(self, task_id: str, depends_on: List[str]):
        self.task_id = task_id
        self.depends_on = depends_on

    def is_ready(self, completed_tasks: set) -> bool:
        """Check if all dependencies are completed"""
        return all(dep in completed_tasks for dep in self.depends_on)


class AgentTask:
    """Represents a task to be executed by an agent"""

    def __init__(
        self,
        task_id: str,
        agent_name: str,
        context: Dict[str, Any],
        depends_on: Optional[List[str]] = None,
        retry_count: int = 0,
        max_retries: int = 3,
        timeout_seconds: int = 300,
    ):
        self.task_id = task_id
        self.agent_name = agent_name
        self.context = context
        self.depends_on = depends_on or []
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.result = None
        self.error = None
        self.status = "pending"
        self.start_time = None
        self.end_time = None


class AgentOrchestrator:
    """
    Orchestrates multi-agent workflows with learning-based optimization.
    """

    def __init__(self, db, agents: Dict[str, Any]):
        self.db = db
        self.agents = agents
        self.memory = AgentMemory(db)
        self.performance = PerformanceTracker(db)
        self.strategy = AdaptiveStrategy(db)
        self.executed_tasks = {}
        self.task_results = {}

    async def execute_workflow(
        self,
        tasks: List[AgentTask],
        parallel: bool = True,
        on_task_complete: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Execute a workflow of tasks with dependency management.

        Args:
            tasks: List of AgentTask objects
            parallel: Whether to execute tasks in parallel when possible
            on_task_complete: Optional callback when a task completes

        Returns:
            Dictionary with task results
        """

        logger.info(f"Starting workflow with {len(tasks)} tasks")

        completed_tasks = set()
        failed_tasks = set()
        pending_tasks = {t.task_id: t for t in tasks}

        while pending_tasks or (completed_tasks and len(completed_tasks) < len(tasks)):
            # Find ready tasks
            ready_tasks = []
            for task_id, task in pending_tasks.items():
                if all(dep in completed_tasks for dep in task.depends_on):
                    ready_tasks.append(task)

            if not ready_tasks:
                if pending_tasks:
                    logger.error("Deadlock: no ready tasks but workflow incomplete")
                break

            # Execute ready tasks
            if parallel:
                # Execute in parallel
                results = await asyncio.gather(
                    *[
                        self._execute_task(task, on_task_complete)
                        for task in ready_tasks
                    ],
                    return_exceptions=True,
                )

                for task, result in zip(ready_tasks, results):
                    if isinstance(result, Exception):
                        logger.error(f"Task {task.task_id} failed: {result}")
                        failed_tasks.add(task.task_id)
                    else:
                        completed_tasks.add(task.task_id)
                        self.task_results[task.task_id] = task.result

                    del pending_tasks[task.task_id]

            else:
                # Execute sequentially
                for task in ready_tasks:
                    try:
                        await self._execute_task(task, on_task_complete)
                        completed_tasks.add(task.task_id)
                        self.task_results[task.task_id] = task.result
                    except Exception as e:
                        logger.error(f"Task {task.task_id} failed: {e}")
                        failed_tasks.add(task.task_id)

                    del pending_tasks[task.task_id]

        # Prepare results
        workflow_result = {
            "total_tasks": len(tasks),
            "completed": len(completed_tasks),
            "failed": len(failed_tasks),
            "results": self.task_results,
            "status": "success" if not failed_tasks else "partial_failure",
        }

        logger.info(
            f"Workflow complete: {len(completed_tasks)}/{len(tasks)} tasks succeeded"
        )

        return workflow_result

    async def _execute_task(
        self,
        task: AgentTask,
        on_task_complete: Optional[Callable] = None,
    ) -> Any:
        """Execute a single task with retry logic"""

        logger.info(f"Executing task {task.task_id} with agent {task.agent_name}")

        task.status = "running"
        task.start_time = datetime.now(timezone.utc)

        agent = self.agents.get(task.agent_name)
        if not agent:
            raise ValueError(f"Agent {task.agent_name} not found")

        # Get recommended strategy
        strategy = await self.strategy.get_recommended_strategy(
            task.agent_name, task.context
        )
        logger.info(
            f"Task {task.task_id} strategy: {strategy.get('success_rate', 0):.1f}% success"
        )

        # Execute with retries
        last_error = None
        for attempt in range(task.max_retries + 1):
            try:
                task.context["retry_count"] = attempt

                # Execute with timeout
                result = await asyncio.wait_for(
                    agent.run(task.context), timeout=task.timeout_seconds
                )

                task.result = result
                task.status = "completed"
                task.end_time = datetime.now(timezone.utc)

                logger.info(f"Task {task.task_id} completed successfully")

                if on_task_complete:
                    await on_task_complete(task)

                return result

            except asyncio.TimeoutError:
                last_error = f"Task timeout after {task.timeout_seconds}s"
                logger.warning(f"Task {task.task_id} attempt {attempt + 1} timed out")

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Task {task.task_id} attempt {attempt + 1} failed: {e}")

                # Check if should retry
                should_retry = await self.memory.should_retry(
                    task.agent_name, str(e), attempt
                )
                if not should_retry:
                    break

            # Wait before retry
            if attempt < task.max_retries:
                await asyncio.sleep(2**attempt)  # Exponential backoff

        # All retries failed
        task.status = "failed"
        task.error = last_error
        task.end_time = datetime.now(timezone.utc)

        logger.error(
            f"Task {task.task_id} failed after {task.max_retries + 1} attempts: {last_error}"
        )

        raise Exception(f"Task {task.task_id} failed: {last_error}")

    async def optimize_workflow(self, tasks: List[AgentTask]) -> List[AgentTask]:
        """
        Optimize task order based on learned patterns.
        Reorder tasks to minimize total execution time.
        """

        logger.info("Optimizing workflow based on learned patterns")

        # Get performance metrics for each agent
        agent_metrics = {}
        for task in tasks:
            if task.agent_name not in agent_metrics:
                metrics = await self.performance.get_metrics_summary(
                    task.agent_name, metric_name="execution_time_ms", hours=24
                )
                agent_metrics[task.agent_name] = metrics

        # Sort tasks by expected duration (fastest first)
        def get_expected_duration(task: AgentTask) -> float:
            metrics = agent_metrics.get(task.agent_name, {})
            return metrics.get("avg", 5000)  # Default 5s

        # Topological sort with duration optimization
        optimized = []
        completed = set()
        remaining = set(t.task_id for t in tasks)

        while remaining:
            # Find ready tasks
            ready = [
                t
                for t in tasks
                if t.task_id in remaining and all(d in completed for d in t.depends_on)
            ]

            if not ready:
                break

            # Sort by expected duration (fastest first for parallelization)
            ready.sort(key=get_expected_duration)

            # Add fastest task
            task = ready[0]
            optimized.append(task)
            completed.add(task.task_id)
            remaining.remove(task.task_id)

        logger.info(f"Workflow optimized: {len(optimized)} tasks")

        return optimized

    async def analyze_workflow_performance(self) -> Dict[str, Any]:
        """
        Analyze performance of completed workflow.
        Extract learnings for future optimization.
        """

        analysis = {
            "total_tasks": len(self.executed_tasks),
            "successful_tasks": sum(
                1 for t in self.executed_tasks.values() if t.status == "completed"
            ),
            "failed_tasks": sum(
                1 for t in self.executed_tasks.values() if t.status == "failed"
            ),
            "agent_performance": {},
        }

        # Analyze per-agent performance
        agents = set(t.agent_name for t in self.executed_tasks.values())
        for agent_name in agents:
            agent_tasks = [
                t for t in self.executed_tasks.values() if t.agent_name == agent_name
            ]

            durations = []
            for task in agent_tasks:
                if task.start_time and task.end_time:
                    duration = (task.end_time - task.start_time).total_seconds() * 1000
                    durations.append(duration)

            if durations:
                analysis["agent_performance"][agent_name] = {
                    "avg_duration_ms": sum(durations) / len(durations),
                    "min_duration_ms": min(durations),
                    "max_duration_ms": max(durations),
                    "success_rate": sum(
                        1 for t in agent_tasks if t.status == "completed"
                    )
                    / len(agent_tasks)
                    * 100,
                }

        return analysis

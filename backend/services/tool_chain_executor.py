"""
Tool Chain Executor: Orchestrates execution of multiple tools in sequence or parallel.
Implements multi-step workflows like I do (file reads -> analysis -> edits).
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolStep:
    """Single step in a tool chain"""

    def __init__(
        self,
        name: str,
        tool: Callable,
        input_params: Dict[str, Any],
        output_key: str = "",
    ):
        self.name = name
        self.tool = tool
        self.input_params = input_params
        self.output_key = output_key  # Key to store result in context
        self.result = None
        self.error = None
        self.execution_time = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "input_params": self.input_params,
            "output_key": self.output_key,
            "execution_time": self.execution_time,
            "success": self.error is None,
            "error": self.error,
        }


class ToolChain:
    """Defines a sequence of tools to execute"""

    def __init__(self, name: str, steps: List[ToolStep] = None):
        self.name = name
        self.steps = steps or []
        self.execution_order = []  # Track execution order
        self.context = {}  # Shared context between steps

    def add_step(
        self,
        name: str,
        tool: Callable,
        input_params: Dict[str, Any],
        output_key: str = "",
    ) -> "ToolChain":
        """Add step to chain (fluent interface)"""
        step = ToolStep(name, tool, input_params, output_key)
        self.steps.append(step)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
            "context": self.context,
        }


class ToolChainExecutor:
    """Executes tool chains in sequence or parallel"""

    def __init__(self, max_parallel: int = 5, timeout_per_step: int = 30):
        self.max_parallel = max_parallel
        self.timeout_per_step = timeout_per_step
        self.execution_history: List[Dict[str, Any]] = []

    async def execute_sequential(self, chain: ToolChain) -> Dict[str, Any]:
        """
        Execute tool chain sequentially.
        Each step can use output of previous steps.
        """
        logger.info(f"Executing tool chain sequentially: {chain.name}")

        for i, step in enumerate(chain.steps):
            try:
                # Resolve input parameters using context
                resolved_params = self._resolve_parameters(step.input_params, chain.context)

                logger.info(f"Step {i + 1}/{len(chain.steps)}: {step.name}")

                # Execute tool
                import time
                start_time = time.time()

                if asyncio.iscoroutinefunction(step.tool):
                    result = await asyncio.wait_for(
                        step.tool(resolved_params),
                        timeout=self.timeout_per_step
                    )
                else:
                    result = step.tool(resolved_params)

                step.execution_time = time.time() - start_time
                step.result = result

                # Store in context if output_key is set
                if step.output_key:
                    chain.context[step.output_key] = result

                logger.info(f"Step {i + 1} completed in {step.execution_time:.2f}s")

            except asyncio.TimeoutError:
                step.error = f"Tool timed out after {self.timeout_per_step}s"
                logger.error(f"Step {i + 1} timeout: {step.error}")
                return self._create_result(chain, success=False)

            except Exception as e:
                step.error = str(e)
                logger.error(f"Step {i + 1} error: {step.error}")
                return self._create_result(chain, success=False)

            chain.execution_order.append(step.name)

        return self._create_result(chain, success=True)

    async def execute_parallel(self, chain: ToolChain, groups: Optional[List[List[int]]] = None) -> Dict[str, Any]:
        """
        Execute tool chain with parallel groups.
        Groups define which steps can run in parallel.
        If no groups provided, one-at-a-time execution.

        Example groups: [[0, 1, 2], [3], [4, 5]] means steps 0-2 parallel, then 3, then 4-5
        """
        logger.info(f"Executing tool chain in parallel: {chain.name}")

        if not groups:
            groups = [[i] for i in range(len(chain.steps))]

        for group_idx, group_step_indices in enumerate(groups):
            tasks = []

            for step_idx in group_step_indices:
                if step_idx < len(chain.steps):
                    step = chain.steps[step_idx]
                    task = self._execute_step(step, chain.context, step_idx + 1, len(chain.steps))
                    tasks.append(task)

            try:
                results = await asyncio.gather(*tasks, return_exceptions=False)

                # Update context with results
                for step_idx, result in zip(group_step_indices, results):
                    step = chain.steps[step_idx]
                    if step.output_key and result and result.get("result"):
                        chain.context[step.output_key] = result["result"]

                # Check for errors
                if any(r.get("error") for r in results if r):
                    errors = [r.get("error") for r in results if r and r.get("error")]
                    logger.error(f"Errors in parallel execution: {errors}")
                    return self._create_result(chain, success=False, error="; ".join(errors))

            except Exception as e:
                logger.error(f"Parallel group {group_idx} error: {str(e)}")
                return self._create_result(chain, success=False, error=str(e))

            chain.execution_order.extend([chain.steps[i].name for i in group_step_indices])

        return self._create_result(chain, success=True)

    async def _execute_step(
        self, step: ToolStep, context: Dict[str, Any], step_num: int, total_steps: int
    ) -> Dict[str, Any]:
        """Execute single step (used in parallel execution)"""
        try:
            resolved_params = self._resolve_parameters(step.input_params, context)

            logger.info(f"Step {step_num}/{total_steps}: {step.name}")

            import time
            start_time = time.time()

            if asyncio.iscoroutinefunction(step.tool):
                result = await asyncio.wait_for(
                    step.tool(resolved_params),
                    timeout=self.timeout_per_step
                )
            else:
                result = step.tool(resolved_params)

            step.execution_time = time.time() - start_time
            step.result = result

            logger.info(f"Step {step_num} completed in {step.execution_time:.2f}s")

            return {"result": result, "error": None}

        except asyncio.TimeoutError:
            error = f"Tool timed out after {self.timeout_per_step}s"
            step.error = error
            return {"result": None, "error": error}

        except Exception as e:
            error = str(e)
            step.error = error
            return {"result": None, "error": error}

    def _resolve_parameters(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve parameters using context variables"""
        resolved = {}

        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                # Reference to context variable
                context_key = value[1:]  # Remove $
                resolved[key] = context.get(context_key, value)
            elif isinstance(value, dict):
                # Recursive resolution for nested params
                resolved[key] = self._resolve_parameters(value, context)
            else:
                resolved[key] = value

        return resolved

    def _create_result(self, chain: ToolChain, success: bool, error: str = "") -> Dict[str, Any]:
        """Create execution result"""
        total_time = sum(s.execution_time for s in chain.steps)

        result = {
            "chain_name": chain.name,
            "success": success,
            "steps_executed": len(chain.execution_order),
            "total_steps": len(chain.steps),
            "total_execution_time": total_time,
            "execution_order": chain.execution_order,
            "final_context": chain.context,
            "step_details": [s.to_dict() for s in chain.steps],
            "error": error,
        }

        self.execution_history.append(result)

        # Keep last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

        return result

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history of all chains"""
        return self.execution_history

    def get_chain_stats(self) -> Dict[str, Any]:
        """Get statistics about tool chains"""
        if not self.execution_history:
            return {"total_chains": 0}

        total_chains = len(self.execution_history)
        successful = len([r for r in self.execution_history if r["success"]])
        failed = total_chains - successful
        total_time = sum(r["total_execution_time"] for r in self.execution_history)
        avg_time = total_time / total_chains if total_chains > 0 else 0

        return {
            "total_chains_executed": total_chains,
            "successful": successful,
            "failed": failed,
            "total_execution_time": total_time,
            "average_chain_time": avg_time,
        }

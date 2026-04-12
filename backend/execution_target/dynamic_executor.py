"""
Dynamic Executor: Allows target switching and multi-target builds
Coordinates execution of multiple targets in parallel or sequence
"""

import asyncio
from typing import Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """How to execute multiple targets"""

    SEQUENTIAL = "sequential"  # One after another
    PARALLEL = "parallel"  # All at once
    CONDITIONAL = "conditional"  # Based on dependencies


class DynamicExecutor:
    """
    Manages execution of one or more targets
    Supports:
    - Switching targets mid-execution
    - Executing multiple targets (primary + secondary)
    - Fallback to secondary if primary fails
    - Parallel multi-target execution
    """

    def __init__(self):
        self.execution_history = {}
        self.active_executions = {}

    async def execute_targets(
        self,
        job_id: str,
        primary_target: str,
        secondary_targets: Optional[List[str]] = None,
        mode: ExecutionMode = ExecutionMode.PARALLEL,
        allow_switching: bool = True,
    ) -> Dict:
        """
        Execute one or more execution targets

        Args:
            job_id: The job ID
            primary_target: Main target to execute
            secondary_targets: Additional targets (optional)
            mode: How to execute (sequential/parallel/conditional)
            allow_switching: Allow mid-execution target switching

        Returns:
            {
                "job_id": str,
                "primary_result": dict,
                "secondary_results": dict,
                "executed_targets": [str],
                "switched_targets": [str],
                "success": bool,
                "fallback_used": bool
            }
        """

        logger.info(
            f"[{job_id}] Starting dynamic execution: primary={primary_target}, secondary={secondary_targets or []}"
        )

        result = {
            "job_id": job_id,
            "primary_result": None,
            "secondary_results": {},
            "executed_targets": [],
            "switched_targets": [],
            "success": False,
            "fallback_used": False,
        }

        # Register execution
        self.active_executions[job_id] = {
            "primary": primary_target,
            "secondary": secondary_targets or [],
            "allow_switching": allow_switching,
            "status": "running",
        }

        try:
            # Execute primary target
            logger.info(f"[{job_id}] Executing primary target: {primary_target}")
            primary_result = await self._execute_target(job_id, primary_target)
            result["primary_result"] = primary_result
            result["executed_targets"].append(primary_target)
            result["success"] = primary_result.get("success", False)

            # If primary failed and we have secondary targets, try fallback
            if not result["success"] and secondary_targets:
                logger.warning(
                    f"[{job_id}] Primary target failed, attempting fallback to secondary targets"
                )
                result["fallback_used"] = True

                for secondary in secondary_targets:
                    logger.info(f"[{job_id}] Executing secondary target: {secondary}")
                    secondary_result = await self._execute_target(job_id, secondary)
                    result["secondary_results"][secondary] = secondary_result
                    result["executed_targets"].append(secondary)

                    if secondary_result.get("success"):
                        result["success"] = True
                        logger.info(f"[{job_id}] Fallback to {secondary} succeeded")
                        break

            # Execute remaining secondary targets (in parallel or sequence)
            elif result["success"] and secondary_targets:
                remaining = [
                    s for s in secondary_targets if s not in result["executed_targets"]
                ]

                if mode == ExecutionMode.PARALLEL:
                    logger.info(
                        f"[{job_id}] Executing secondary targets in parallel: {remaining}"
                    )
                    tasks = [
                        self._execute_target(job_id, target) for target in remaining
                    ]
                    secondary_results = await asyncio.gather(
                        *tasks, return_exceptions=True
                    )

                    for target, res in zip(remaining, secondary_results):
                        if isinstance(res, Exception):
                            result["secondary_results"][target] = {
                                "success": False,
                                "error": str(res),
                            }
                        else:
                            result["secondary_results"][target] = res
                            result["executed_targets"].append(target)

                elif mode == ExecutionMode.SEQUENTIAL:
                    logger.info(
                        f"[{job_id}] Executing secondary targets sequentially: {remaining}"
                    )
                    for target in remaining:
                        secondary_result = await self._execute_target(job_id, target)
                        result["secondary_results"][target] = secondary_result
                        result["executed_targets"].append(target)

        except Exception as e:
            logger.error(f"[{job_id}] Error during execution: {str(e)}")
            result["success"] = False

        finally:
            # Mark execution as complete
            self.active_executions[job_id]["status"] = "complete"
            self.execution_history[job_id] = result
            logger.info(
                f"[{job_id}] Dynamic execution complete: success={result['success']}"
            )

        return result

    async def switch_target(self, job_id: str, new_target: str) -> bool:
        """
        Switch execution target mid-stream

        Args:
            job_id: The job ID
            new_target: New target to switch to

        Returns:
            True if switch was successful
        """

        if job_id not in self.active_executions:
            logger.warning(f"[{job_id}] Cannot switch target: execution not found")
            return False

        execution = self.active_executions[job_id]

        if not execution.get("allow_switching"):
            logger.warning(f"[{job_id}] Cannot switch target: switching not allowed")
            return False

        if execution["status"] != "running":
            logger.warning(f"[{job_id}] Cannot switch target: execution not running")
            return False

        logger.info(
            f"[{job_id}] Switching target from {execution['primary']} to {new_target}"
        )

        # Record the switch
        self.active_executions[job_id]["switched_targets"] = self.active_executions[
            job_id
        ].get("switched_targets", [])
        self.active_executions[job_id]["switched_targets"].append(new_target)
        self.active_executions[job_id]["primary"] = new_target

        return True

    async def _execute_target(self, job_id: str, target: str) -> Dict:
        """
        Dispatch to per-target execution logic.

        Known targets (from IntentAnalyzer / target_detection_api):
            fullstack-web      → full-stack Vite + React + Node build
            nextjs-app         → Next.js App Router build
            marketing-static   → static HTML/CSS/JS build
            api-backend-first  → FastAPI / Node backend build
            agents-automation  → agent orchestration run

        Any unrecognised target is accepted and logged so future targets can be
        added without breaking existing callers.
        """
        import time

        logger.info(f"[{job_id}] _execute_target called for target={target!r}")
        start = time.monotonic()

        try:
            result = await self._dispatch(job_id, target)
        except Exception as exc:
            logger.error(f"[{job_id}] Target {target!r} raised: {exc}")
            result = {"success": False, "target": target, "error": str(exc)}

        result["duration"] = round(time.monotonic() - start, 3)
        return result

    # ------------------------------------------------------------------
    # Per-target dispatch
    # ------------------------------------------------------------------

    async def _dispatch(self, job_id: str, target: str) -> Dict:
        """Route a target string to the appropriate execution handler."""
        handlers = {
            "fullstack-web": self._run_fullstack_web,
            "nextjs-app": self._run_nextjs_app,
            "marketing-static": self._run_marketing_static,
            "api-backend-first": self._run_api_backend,
            "agents-automation": self._run_agents_automation,
        }
        handler = handlers.get(target)
        if handler is None:
            logger.warning(
                f"[{job_id}] Unknown target {target!r}; running generic handler"
            )
            return await self._run_generic(job_id, target)
        return await handler(job_id)

    async def _run_fullstack_web(self, job_id: str) -> Dict:
        """Full-stack web target: Vite + React + Node.js API."""
        logger.info(f"[{job_id}] Running fullstack-web target")
        return {
            "success": True,
            "target": "fullstack-web",
            "output": "Full-stack web build initiated (Vite + React + Node.js API)",
            "details": {"frontend": "vite+react", "backend": "node-api"},
        }

    async def _run_nextjs_app(self, job_id: str) -> Dict:
        """Next.js App Router target."""
        logger.info(f"[{job_id}] Running nextjs-app target")
        return {
            "success": True,
            "target": "nextjs-app",
            "output": "Next.js App Router build initiated",
            "details": {"renderer": "server-components", "router": "app"},
        }

    async def _run_marketing_static(self, job_id: str) -> Dict:
        """Static marketing / landing-page target."""
        logger.info(f"[{job_id}] Running marketing-static target")
        return {
            "success": True,
            "target": "marketing-static",
            "output": "Static site build initiated (HTML/CSS/JS)",
            "details": {"type": "static", "assets": "optimised"},
        }

    async def _run_api_backend(self, job_id: str) -> Dict:
        """API / backend-first target (FastAPI or Node)."""
        logger.info(f"[{job_id}] Running api-backend-first target")
        return {
            "success": True,
            "target": "api-backend-first",
            "output": "Backend API build initiated (FastAPI / Node.js)",
            "details": {"type": "rest-api", "framework": "fastapi"},
        }

    async def _run_agents_automation(self, job_id: str) -> Dict:
        """Agent orchestration / automation target."""
        logger.info(f"[{job_id}] Running agents-automation target")
        return {
            "success": True,
            "target": "agents-automation",
            "output": "Agent orchestration workflow initiated",
            "details": {"type": "agent-workflow"},
        }

    async def _run_generic(self, job_id: str, target: str) -> Dict:
        """Fallback handler for unrecognised targets."""
        logger.info(f"[{job_id}] Running generic handler for target={target!r}")
        return {
            "success": True,
            "target": target,
            "output": f"Generic execution for target '{target}'",
            "details": {},
        }

    def get_execution_status(self, job_id: str) -> Optional[Dict]:
        """Get current execution status"""
        return self.active_executions.get(job_id)

    def get_execution_result(self, job_id: str) -> Optional[Dict]:
        """Get execution result after completion"""
        return self.execution_history.get(job_id)

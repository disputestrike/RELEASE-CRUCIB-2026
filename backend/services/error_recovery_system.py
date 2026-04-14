"""
Enhanced Error Recovery & Learning System: Intelligent failure handling and adaptation.
When things fail, learn from it and try alternative strategies.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ErrorEvent:
    """Records an error for analysis and learning"""

    def __init__(self, agent_name: str, error_type: str, error_message: str, context: Dict[str, Any]):
        self.id = f"error_{int(datetime.now().timestamp() * 1000)}"
        self.timestamp = datetime.now()
        self.agent_name = agent_name
        self.error_type = error_type
        self.error_message = error_message
        self.context = context
        self.recovery_attempts = []
        self.resolved = False

    def add_recovery_attempt(self, strategy: str, success: bool, result: str):
        """Log a recovery attempt"""
        self.recovery_attempts.append({
            "strategy": strategy,
            "success": success,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        })
        self.resolved = success

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent": self.agent_name,
            "error_type": self.error_type,
            "message": self.error_message,
            "context": self.context,
            "recovery_attempts": self.recovery_attempts,
            "resolved": self.resolved,
            "timestamp": self.timestamp.isoformat(),
        }


class ErrorRecoveryStrategy:
    """Base class for recovery strategies"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.success_rate = 0.5
        self.usage_count = 0

    async def execute(self, error: ErrorEvent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute recovery strategy - override in subclasses"""
        raise NotImplementedError

    def record_result(self, success: bool):
        """Update success rate based on result"""
        self.usage_count += 1
        if success:
            self.success_rate = (self.success_rate * 0.9) + (1.0 * 0.1)
        else:
            self.success_rate = (self.success_rate * 0.9) + (0.0 * 0.1)


class RetryStrategy(ErrorRecoveryStrategy):
    """Simple retry with backoff"""

    def __init__(self):
        super().__init__("retry", "Retry the failing operation with exponential backoff")
        self.max_retries = 3

    async def execute(self, error: ErrorEvent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Retry the operation"""
        import asyncio
        
        retry_count = len(error.recovery_attempts)
        
        if retry_count >= self.max_retries:
            return {
                "success": False,
                "reason": f"Max retries ({self.max_retries}) exceeded",
            }

        # Exponential backoff
        wait_time = 2 ** retry_count
        await asyncio.sleep(min(wait_time, 10))  # Max 10 seconds

        return {
            "success": True,
            "action": "retry_queued",
            "retry_number": retry_count + 1,
            "backoff_seconds": wait_time,
        }


class FallbackAgentStrategy(ErrorRecoveryStrategy):
    """Use alternative agent to handle the task"""

    def __init__(self):
        super().__init__("fallback_agent", "Route to alternative agent for the same task")
        self.agent_fallbacks = {
            "CodeAnalysisAgent": ["SecurityAgent", "DocumentationAgent"],
            "TerminalAgent": ["FileAgent", "APIAgent"],
            "BackendAgent": ["PlannerAgent", "ArchitectureAgent"],
        }

    async def execute(self, error: ErrorEvent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Try alternative agent"""
        agent_name = error.agent_name
        fallbacks = self.agent_fallbacks.get(agent_name, [])

        if not fallbacks:
            return {
                "success": False,
                "reason": "No fallback agents available",
            }

        return {
            "success": True,
            "action": "use_fallback_agent",
            "fallback_agent": fallbacks[0],
            "reason": f"Primary agent {agent_name} failed, trying {fallbacks[0]}",
        }


class ContextAdjustmentStrategy(ErrorRecoveryStrategy):
    """Modify request context and retry"""

    def __init__(self):
        super().__init__(
            "context_adjustment",
            "Simplify or adjust request context",
        )

    async def execute(self, error: ErrorEvent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust context for retry"""
        adjusted_context = context.copy()

        # Simplification strategies
        if "timeout" in error.error_message.lower():
            adjusted_context["timeout"] = adjusted_context.get("timeout", 30) * 0.5
            return {
                "success": True,
                "action": "reduce_timeout",
                "new_timeout": adjusted_context["timeout"],
            }

        if "too large" in error.error_message.lower() or "memory" in error.error_message.lower():
            adjusted_context["batch_size"] = adjusted_context.get("batch_size", 100) // 2
            return {
                "success": True,
                "action": "reduce_load",
                "new_batch_size": adjusted_context["batch_size"],
            }

        if "insufficient" in error.error_message.lower():
            # Provide more explicit context
            adjusted_context["include_examples"] = True
            return {
                "success": True,
                "action": "add_context",
                "added_examples": True,
            }

        return {"success": False, "reason": "Cannot adjust context for this error"}


class ClarificationStrategy(ErrorRecoveryStrategy):
    """Ask for clarification before retry"""

    def __init__(self):
        super().__init__(
            "clarification",
            "Request clarification from user",
        )

    async def execute(self, error: ErrorEvent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate clarification request"""
        return {
            "success": True,
            "action": "request_clarification",
            "error_type": error.error_type,
            "questions": self._generate_questions(error),
        }

    def _generate_questions(self, error: ErrorEvent) -> List[str]:
        """Generate clarifying questions for the error"""
        questions = []

        if "ambiguous" in error.error_message.lower():
            questions.append("Can you provide more specific details about what you want?")

        if "missing" in error.error_message.lower():
            questions.append("What information is required for me to proceed?")

        if "invalid" in error.error_message.lower():
            questions.append("Can you verify the input format or values?")

        if "not found" in error.error_message.lower():
            questions.append("Can you check if the file/resource exists in your workspace?")

        return questions or ["Can you clarify the request?"]


class SkipAndContinueStrategy(ErrorRecoveryStrategy):
    """Skip this step and continue with next steps"""

    def __init__(self):
        super().__init__(
            "skip_continue",
            "Skip failing operation and continue workflow",
        )

    async def execute(self, error: ErrorEvent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Skip and continue"""
        return {
            "success": True,
            "action": "skip_step",
            "message": f"Skipped {error.agent_name} due to {error.error_type}. Continuing with other steps.",
        }


class EnhancedErrorRecoverySystem:
    """
    Intelligent error recovery system.
    Analyzes failures and applies best recovery strategy.
    """

    def __init__(self):
        self.strategies: List[ErrorRecoveryStrategy] = [
            RetryStrategy(),
            FallbackAgentStrategy(),
            ContextAdjustmentStrategy(),
            ClarificationStrategy(),
            SkipAndContinueStrategy(),
        ]
        self.error_history: List[ErrorEvent] = []
        self.recovery_success_rates: Dict[str, float] = {}

    async def handle_error(
        self, agent_name: str, error_type: str, error_message: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle error by selecting best recovery strategy.
        Returns recovery plan.
        """
        error = ErrorEvent(agent_name, error_type, error_message, context)
        self.error_history.append(error)

        # Select best strategy based on error type
        best_strategy = self._select_strategy(error)

        if not best_strategy:
            return {
                "success": False,
                "error_id": error.id,
                "message": "No recovery strategy available",
            }

        try:
            result = await best_strategy.execute(error, context)
            success = result.get("success", False)

            error.add_recovery_attempt(best_strategy.name, success, json.dumps(result))
            best_strategy.record_result(success)

            logger.info(
                f"Error recovery {best_strategy.name}: {result}"
            )

            return {
                "error_id": error.id,
                "strategy": best_strategy.name,
                "result": result,
                "success": success,
            }

        except Exception as e:
            logger.error(f"Error recovery strategy failed: {str(e)}")
            error.add_recovery_attempt(best_strategy.name, False, str(e))
            return {
                "error_id": error.id,
                "strategy": best_strategy.name,
                "success": False,
                "message": str(e),
            }

    def _select_strategy(self, error: ErrorEvent) -> Optional[ErrorRecoveryStrategy]:
        """Select best recovery strategy for error"""
        error_lower = error.error_message.lower() + error.error_type.lower()

        # Prioritize by error type
        if "timeout" in error_lower or "too slow" in error_lower:
            return next(s for s in self.strategies if isinstance(s, ContextAdjustmentStrategy))

        if "insufficient" in error_lower or "ambiguous" in error_lower:
            return next(s for s in self.strategies if isinstance(s, ClarificationStrategy))

        if "not found" in error_lower or "missing" in error_lower:
            return next(s for s in self.strategies if isinstance(s, RetryStrategy))

        # Sort strategies by success rate
        sorted_strategies = sorted(
            self.strategies,
            key=lambda s: s.success_rate,
            reverse=True,
        )

        return sorted_strategies[0] if sorted_strategies else None

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error recovery statistics"""
        unresolved_errors = [e for e in self.error_history if not e.resolved]
        resolved_errors = [e for e in self.error_history if e.resolved]

        return {
            "total_errors": len(self.error_history),
            "resolved": len(resolved_errors),
            "unresolved": len(unresolved_errors),
            "resolution_rate": len(resolved_errors) / len(self.error_history) if self.error_history else 0,
            "strategy_stats": {
                s.name: {
                    "usage": s.usage_count,
                    "success_rate": s.success_rate,
                }
                for s in self.strategies
            },
            "recent_errors": [e.to_dict() for e in self.error_history[-10:]],
        }

    def get_insights(self) -> List[str]:
        """Get insights about common failure patterns"""
        insights = []

        if not self.error_history:
            return insights

        # Most common error types
        error_types = {}
        for error in self.error_history:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1

        if error_types:
            most_common = max(error_types.items(), key=lambda x: x[1])
            insights.append(f"Most common error: {most_common[0]} ({most_common[1]} occurrences)")

        # Agents with most failures
        agent_failures = {}
        for error in self.error_history:
            agent_failures[error.agent_name] = agent_failures.get(error.agent_name, 0) + 1

        if agent_failures:
            problem_agent = max(agent_failures.items(), key=lambda x: x[1])
            insights.append(f"Most problematic agent: {problem_agent[0]} ({problem_agent[1]} errors)")

        # Best performing recovery strategy
        best_strategy = max(self.strategies, key=lambda s: s.success_rate)
        insights.append(f"Most effective recovery: {best_strategy.name} ({best_strategy.success_rate:.0%} success rate)")

        return insights

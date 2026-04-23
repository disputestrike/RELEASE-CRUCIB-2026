"""
Base agent class with recursive learning integration.
All agents inherit from BaseAgent and implement validate_input, validate_output, and execute.
Now includes learning system, performance tracking, and Cerebras integration.
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from backend.agent_recursive_learning import (
    AdaptiveStrategy,
    AgentMemory,
    ExecutionStatus,
    PerformanceTracker,
)
from anthropic import AsyncAnthropic
from backend.anthropic_models import ANTHROPIC_HAIKU_MODEL, normalize_anthropic_model
from backend.llm_cerebras import invoke_cerebras, invoke_cerebras_stream
from backend.services.runtime.execution_authority import require_runtime_authority

logger = logging.getLogger(__name__)

CEREBRAS_CONTEXT_TOKEN_LIMIT = int(
    os.environ.get("CEREBRAS_CONTEXT_TOKEN_LIMIT", "8192")
)
CEREBRAS_CONTEXT_SAFETY_MARGIN = int(
    os.environ.get("CEREBRAS_CONTEXT_SAFETY_MARGIN", "512")
)
ANTHROPIC_FALLBACK_MODEL = normalize_anthropic_model(
    os.environ.get("ANTHROPIC_FALLBACK_MODEL"),
    default=ANTHROPIC_HAIKU_MODEL,
)


class AgentValidationError(Exception):
    """Raised when agent input/output validation fails."""

    pass


class BaseAgent(ABC):
    """
    Base class for all specialized agents with recursive learning.
    Each agent must implement:
    - validate_input(context): Validate required context fields
    - validate_output(result): Validate output structure
    - execute(context): Main agent logic
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        db: Optional[Any] = None,
    ):
        """
        Initialize the agent with learning system support.

        Args:
            llm_client: Optional LLM client
            config: Optional configuration dictionary
            db: Optional database connection for learning system
        """
        self.llm_client = llm_client
        self.config = config or {}
        self.name = self.__class__.__name__
        self.db = db

        # Initialize learning systems if db is available
        if db:
            self.memory = AgentMemory(db)
            self.performance = PerformanceTracker(db)
            self.strategy = AdaptiveStrategy(db)
        else:
            self.memory = None
            self.performance = None
            self.strategy = None

    @staticmethod
    def _estimate_prompt_tokens(*parts: str) -> int:
        """Rough guardrail estimate used before provider calls."""
        return sum(len(part or "") for part in parts) // 4

    def _cerebras_context_too_large(
        self, user_prompt: str, system_prompt: str, max_tokens: int
    ) -> bool:
        requested = self._estimate_prompt_tokens(user_prompt, system_prompt) + int(
            max_tokens or 0
        )
        return requested + CEREBRAS_CONTEXT_SAFETY_MARGIN > CEREBRAS_CONTEXT_TOKEN_LIMIT

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
        Run the agent with learning: validate, execute, validate, and record.

        Args:
            context: Input context dictionary

        Returns:
            Dict[str, Any]: Result dictionary
        """
        start_time = time.time()
        execution_id = None
        error = None
        status = ExecutionStatus.SUCCESS
        result = {}

        require_runtime_authority("agent", detail="execution")

        try:
            # Validate input
            self.validate_input(context)

            # Get recommended strategy if available
            if self.strategy:
                strategy = await self.strategy.get_recommended_strategy(
                    self.name, context
                )
                logger.info(
                    f"{self.name} strategy: {strategy.get('success_rate', 0):.1f}% success"
                )

            # Execute
            result = await self.execute(context)

            # Validate output
            self.validate_output(result)

            status = ExecutionStatus.SUCCESS

        except Exception as e:
            error = str(e)
            status = ExecutionStatus.ERROR
            logger.error(f"{self.name} execution failed: {error}")
            raise

        finally:
            # Record execution for learning
            duration_ms = (time.time() - start_time) * 1000

            if self.memory:
                try:
                    execution_id = await self.memory.record_execution(
                        agent_name=self.name,
                        input_data=context,
                        output=result if status == ExecutionStatus.SUCCESS else {},
                        status=status,
                        duration_ms=duration_ms,
                        error=error,
                        metadata={"retry_count": context.get("retry_count", 0)},
                    )

                    # Record performance metrics
                    if self.performance:
                        await self.performance.record_metric(
                            agent_name=self.name,
                            metric_name="execution_time_ms",
                            value=duration_ms,
                        )

                        await self.performance.record_metric(
                            agent_name=self.name,
                            metric_name=(
                                "success"
                                if status == ExecutionStatus.SUCCESS
                                else "failure"
                            ),
                            value=1.0,
                        )
                except Exception as e:
                    logger.warning(f"Failed to record learning: {e}")

        return result

    async def call_llm(
        self,
        user_prompt: str,
        system_prompt: str,
        model: str = "cerebras",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        stream: bool = True,
    ) -> tuple[str, int]:
        """
        Call LLM with given prompts. Defaults to Cerebras (free tier) with streaming.

        Args:
            user_prompt: User message
            system_prompt: System message
            model: Model name ("cerebras" for free tier, "claude-*" for Anthropic)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            stream: Whether to use streaming (default True, more reliable)

        Returns:
            Tuple of (response_text, tokens_used)
        """
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

        # Use Cerebras by default (free tier, streaming is more reliable)
        if model == "cerebras" or not anthropic_key:
            if self._cerebras_context_too_large(user_prompt, system_prompt, max_tokens):
                if anthropic_key:
                    logger.info(
                        "%s prompt exceeds Cerebras context; routing to Anthropic fallback",
                        self.name,
                    )
                    return await self.call_llm(
                        user_prompt,
                        system_prompt,
                        ANTHROPIC_FALLBACK_MODEL,
                        temperature,
                        max_tokens,
                        stream=False,
                    )
                raise AgentValidationError(
                    f"{self.name}: prompt too large for Cerebras context window; configure ANTHROPIC_API_KEY for large build prompts"
                )
            try:
                if stream:
                    # Use streaming API (more reliable, no compression issues)
                    content = ""
                    async for chunk in invoke_cerebras_stream(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        max_tokens=max_tokens,
                        temperature=temperature,
                    ):
                        content += chunk

                    # Estimate tokens (rough: 1 token ≈ 4 chars)
                    tokens = len(content) // 4 + len(user_prompt) // 4

                    logger.info(
                        f"{self.name} used Cerebras (streaming): ~{tokens} tokens"
                    )
                    return content, tokens

                else:
                    # Non-streaming API (has compression issues, avoid)
                    response = await invoke_cerebras(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )

                    content = response["choices"][0]["message"]["content"]
                    tokens = response.get("usage", {}).get(
                        "prompt_tokens", 0
                    ) + response.get("usage", {}).get("completion_tokens", 0)

                    logger.info(f"{self.name} used Cerebras: {tokens} tokens")
                    return content, tokens

            except Exception as e:
                logger.error(f"{self.name}: Cerebras API call failed: {e}")
                raise AgentValidationError(
                    f"{self.name}: Cerebras API call failed: {e}"
                )

        # Try Anthropic (Haiku) if key is available
        if model.startswith("claude-"):
            try:
                model = normalize_anthropic_model(
                    model, default=ANTHROPIC_FALLBACK_MODEL
                )
                client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                response = await client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                content = response.content[0].text
                tokens = response.usage.input_tokens + response.usage.output_tokens

                logger.info(f"{self.name} used Anthropic: {tokens} tokens")
                return content, tokens

            except Exception as e:
                logger.error(f"{self.name}: Anthropic API call failed: {e}")
                # Fallback to Cerebras streaming
                if self._cerebras_context_too_large(
                    user_prompt, system_prompt, max_tokens
                ):
                    raise AgentValidationError(
                        f"{self.name}: Anthropic failed and Cerebras fallback was skipped because the prompt exceeds the Cerebras context window"
                    )
                logger.info(f"{self.name} falling back to Cerebras")
                return await self.call_llm(
                    user_prompt,
                    system_prompt,
                    "cerebras",
                    temperature,
                    max_tokens,
                    stream=True,
                )

        raise AgentValidationError(f"{self.name}: No valid LLM model specified")

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

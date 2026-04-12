"""
Parallel workers for CrucibAI — parallel execution for build/agent phases.
Enables shorter build times when phases run agents in parallel (orchestration already uses asyncio.gather).
This module provides a structured pool and batch runner for use by orchestration or other callers.
"""

import asyncio
from typing import List, Callable, Any, TypeVar, Coroutine
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_phase_parallel(
    agents: List[str],
    run_fn: Callable[[str], Coroutine[Any, Any, T]],
    timeout_per_agent: float = 300,
) -> List[tuple]:
    """
    Run a list of agents in parallel. run_fn(agent_name) is awaited for each agent.
    Returns list of (agent_name, result_or_exception).
    """

    async def run_one(name: str):
        try:
            return await asyncio.wait_for(run_fn(name), timeout=timeout_per_agent)
        except asyncio.TimeoutError as e:
            return e
        except Exception as e:
            return e

    tasks = [run_one(a) for a in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return list(zip(agents, results))


async def run_batch(
    items: List[Any],
    process_fn: Callable[[Any], Coroutine[Any, Any, T]],
    max_concurrency: int = 10,
) -> List[T | BaseException]:
    """
    Process items in batches with limited concurrency.
    process_fn(item) is awaited for each item. Returns list of results (or exceptions).
    """
    sem = asyncio.Semaphore(max_concurrency)

    async def limited(item):
        async with sem:
            try:
                return await process_fn(item)
            except Exception as e:
                return e

    tasks = [limited(x) for x in items]
    return list(await asyncio.gather(*tasks, return_exceptions=True))

"""
Agent Latency Optimization System
Reduces latency through caching, batching, and parallel execution.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional


class ResponseCache:
    """Cache agent responses to reduce latency"""

    def __init__(self, db, ttl_seconds: int = 3600):
        self.db = db
        self.ttl_seconds = ttl_seconds
        self.memory_cache = {}

    def _hash_key(self, agent_name: str, input_data: Dict[str, Any]) -> str:
        """Generate cache key from agent name and input"""
        key_str = f"{agent_name}:{json.dumps(input_data, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get(
        self, agent_name: str, input_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get cached response if available"""
        cache_key = self._hash_key(agent_name, input_data)

        # Check memory cache first
        if cache_key in self.memory_cache:
            cached = self.memory_cache[cache_key]
            if datetime.now(timezone.utc) < cached["expires"]:
                return cached["response"]
            else:
                del self.memory_cache[cache_key]

        # Check database cache
        try:
            cached_doc = await self.db["response_cache"].find_one(
                {
                    "cache_key": cache_key,
                    "expires": {"$gt": datetime.now(timezone.utc).isoformat()},
                }
            )

            if cached_doc:
                response = cached_doc.get("response")
                # Store in memory for faster access
                self.memory_cache[cache_key] = {
                    "response": response,
                    "expires": datetime.fromisoformat(cached_doc["expires"]),
                }
                return response
        except:
            pass

        return None

    async def set(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        response: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Cache a response"""
        cache_key = self._hash_key(agent_name, input_data)
        ttl = ttl_seconds or self.ttl_seconds
        expires = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        # Store in memory
        self.memory_cache[cache_key] = {"response": response, "expires": expires}

        # Store in database
        try:
            await self.db["response_cache"].insert_one(
                {
                    "cache_key": cache_key,
                    "agent_name": agent_name,
                    "input_hash": hashlib.md5(
                        json.dumps(input_data, sort_keys=True).encode()
                    ).hexdigest(),
                    "response": response,
                    "created": datetime.now(timezone.utc).isoformat(),
                    "expires": expires.isoformat(),
                    "ttl_seconds": ttl,
                }
            )
        except:
            pass

    async def clear_expired(self) -> int:
        """Remove expired cache entries"""
        try:
            result = await self.db["response_cache"].delete_many(
                {"expires": {"$lt": datetime.now(timezone.utc).isoformat()}}
            )
            return result.get("deleted_count", 0)
        except:
            return 0


class RequestBatcher:
    """Batch similar requests to reduce latency"""

    def __init__(self, db, batch_size: int = 10, wait_ms: int = 100):
        self.db = db
        self.batch_size = batch_size
        self.wait_ms = wait_ms
        self.pending_batches = {}
        self.batch_timers = {}

    async def add_to_batch(
        self,
        agent_name: str,
        request_id: str,
        input_data: Dict[str, Any],
        handler: Callable,
    ) -> Any:
        """Add request to batch"""

        if agent_name not in self.pending_batches:
            self.pending_batches[agent_name] = []

        # Create future for this request
        future = asyncio.Future()

        self.pending_batches[agent_name].append(
            {"request_id": request_id, "input": input_data, "future": future}
        )

        # Check if batch is ready
        if len(self.pending_batches[agent_name]) >= self.batch_size:
            await self._execute_batch(agent_name, handler)
        else:
            # Set timer to execute batch after wait time
            if agent_name not in self.batch_timers:
                self.batch_timers[agent_name] = asyncio.create_task(
                    self._wait_and_execute(agent_name, handler)
                )

        return await future

    async def _wait_and_execute(self, agent_name: str, handler: Callable) -> None:
        """Wait and execute batch"""
        await asyncio.sleep(self.wait_ms / 1000)
        await self._execute_batch(agent_name, handler)

    async def _execute_batch(self, agent_name: str, handler: Callable) -> None:
        """Execute batched requests"""
        if (
            agent_name not in self.pending_batches
            or not self.pending_batches[agent_name]
        ):
            return

        batch = self.pending_batches[agent_name]
        self.pending_batches[agent_name] = []

        if agent_name in self.batch_timers:
            del self.batch_timers[agent_name]

        # Execute all requests in batch
        inputs = [req["input"] for req in batch]

        try:
            results = await handler(inputs)

            # Distribute results
            for req, result in zip(batch, results):
                if not req["future"].done():
                    req["future"].set_result(result)
        except Exception as e:
            # Set error for all futures
            for req in batch:
                if not req["future"].done():
                    req["future"].set_exception(e)


class ParallelExecutor:
    """Execute independent tasks in parallel"""

    def __init__(self, db, max_concurrent: int = 10):
        self.db = db
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_parallel(
        self, tasks: List[Dict[str, Any]], handler: Callable
    ) -> List[Any]:
        """
        Execute tasks in parallel with concurrency limit.

        Args:
            tasks: List of task dictionaries
            handler: Async function to execute each task

        Returns:
            List of results
        """

        async def bounded_handler(task):
            async with self.semaphore:
                return await handler(task)

        # Execute all tasks in parallel
        results = await asyncio.gather(
            *[bounded_handler(task) for task in tasks], return_exceptions=True
        )

        return results

    async def execute_with_dependencies(
        self, task_graph: Dict[str, Dict[str, Any]], handler: Callable
    ) -> Dict[str, Any]:
        """
        Execute tasks respecting dependencies.

        Args:
            task_graph: Dict of task_id -> {depends_on: [...], data: {...}}
            handler: Async function to execute each task

        Returns:
            Dict of task_id -> result
        """

        results = {}
        completed = set()

        while len(completed) < len(task_graph):
            # Find ready tasks
            ready_tasks = []
            for task_id, task_def in task_graph.items():
                if task_id not in completed:
                    deps = task_def.get("depends_on", [])
                    if all(d in completed for d in deps):
                        ready_tasks.append((task_id, task_def))

            if not ready_tasks:
                break

            # Execute ready tasks in parallel
            async def execute_task(task_info):
                task_id, task_def = task_info
                return task_id, await handler(task_def)

            task_results = await asyncio.gather(
                *[execute_task(t) for t in ready_tasks], return_exceptions=True
            )

            for task_id, result in task_results:
                if isinstance(result, Exception):
                    results[task_id] = {"error": str(result)}
                else:
                    results[task_id] = result
                completed.add(task_id)

        return results


class LatencyMonitor:
    """Monitor and track latency metrics"""

    def __init__(self, db):
        self.db = db

    async def record_latency(
        self, agent_name: str, operation: str, latency_ms: float, cached: bool = False
    ) -> None:
        """Record latency metric"""

        await self.db["latency_metrics"].insert_one(
            {
                "agent_name": agent_name,
                "operation": operation,
                "latency_ms": latency_ms,
                "cached": cached,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def get_latency_summary(
        self, agent_name: Optional[str] = None, hours: int = 24
    ) -> Dict[str, Any]:
        """Get latency summary"""

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_iso = cutoff.isoformat()

        query = {"timestamp": {"$gte": cutoff_iso}}
        if agent_name:
            query["agent_name"] = agent_name

        records = await self.db["latency_metrics"].find(query).to_list(10000)

        if not records:
            return {"avg_latency_ms": 0, "records": 0}

        # Calculate statistics
        latencies = [r.get("latency_ms", 0) for r in records]
        cached_count = sum(1 for r in records if r.get("cached", False))

        return {
            "total_records": len(records),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)],
            "cached_requests": cached_count,
            "cache_hit_rate": f"{cached_count / len(records) * 100:.1f}%",
        }

    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get latency optimization recommendations"""

        summary = await self.get_latency_summary()
        recommendations = []

        avg_latency = summary.get("avg_latency_ms", 0)
        p99_latency = summary.get("p99_latency_ms", 0)
        cache_hit_rate = float(summary.get("cache_hit_rate", "0%").rstrip("%"))

        if avg_latency > 2000:
            recommendations.append(
                {
                    "priority": "high",
                    "issue": "High average latency",
                    "current": f"{avg_latency:.0f}ms",
                    "target": "< 1000ms",
                    "action": "Optimize prompts, increase caching, use batching",
                }
            )

        if p99_latency > 5000:
            recommendations.append(
                {
                    "priority": "high",
                    "issue": "High P99 latency (tail latency)",
                    "current": f"{p99_latency:.0f}ms",
                    "target": "< 2000ms",
                    "action": "Implement request timeouts, use parallel execution",
                }
            )

        if cache_hit_rate < 30:
            recommendations.append(
                {
                    "priority": "medium",
                    "issue": "Low cache hit rate",
                    "current": f"{cache_hit_rate:.1f}%",
                    "target": "> 50%",
                    "action": "Increase cache TTL, cache more common patterns",
                }
            )

        return recommendations

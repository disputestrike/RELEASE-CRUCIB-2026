"""
Database Query Optimization Utilities for CrucibAI
Includes indexing strategies, query analysis, and caching
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

# ==================== QUERY CACHING ====================


class QueryCache:
    """
    In-memory cache for database queries
    Automatically expires entries based on TTL
    """

    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds

    def set(self, key: str, value: Any) -> None:
        """Cache a query result"""
        self.cache[key] = {"value": value, "timestamp": datetime.now(), "hits": 0}

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached result if not expired"""
        if key not in self.cache:
            return None

        entry = self.cache[key]
        age = (datetime.now() - entry["timestamp"]).total_seconds()

        if age > self.ttl:
            del self.cache[key]
            return None

        entry["hits"] += 1
        return entry["value"]

    def invalidate(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern"""
        keys_to_delete = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.cache[key]

    def clear(self) -> None:
        """Clear entire cache"""
        self.cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = sum(entry["hits"] for entry in self.cache.values())
        return {"entries": len(self.cache), "total_hits": total_hits, "ttl": self.ttl}


# Global query cache
query_cache = QueryCache()

# ==================== QUERY OPTIMIZATION DECORATOR ====================


def optimize_query(
    cache_key: Optional[str] = None, cache_ttl: int = 3600, timeout: int = 30
):
    """
    Decorator to optimize database queries
    Includes caching, timeout, and performance tracking
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            key = cache_key or f"{func.__name__}_{json.dumps(kwargs, default=str)}"

            # Check cache
            cached_result = query_cache.get(key)
            if cached_result is not None:
                return cached_result

            # Execute query with timeout
            start_time = time.time()
            try:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)

                # Cache result
                query_cache.set(key, result)

                # Log performance
                duration = time.time() - start_time
                if duration > 1.0:  # Log slow queries
                    print(f"Slow query: {func.__name__} took {duration:.2f}s")

                return result

            except asyncio.TimeoutError:
                raise TimeoutError(f"Query {func.__name__} exceeded {timeout}s timeout")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = cache_key or f"{func.__name__}_{json.dumps(kwargs, default=str)}"

            cached_result = query_cache.get(key)
            if cached_result is not None:
                return cached_result

            start_time = time.time()
            result = func(*args, **kwargs)

            query_cache.set(key, result)

            duration = time.time() - start_time
            if duration > 1.0:
                print(f"Slow query: {func.__name__} took {duration:.2f}s")

            return result

        # Return appropriate wrapper
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ==================== INDEXING STRATEGIES ====================


class IndexingStrategy:
    """
    Recommended indexing strategies for MongoDB collections
    """

    @staticmethod
    def get_recommended_indexes() -> Dict[str, List[Dict[str, Any]]]:
        """Get recommended indexes for all collections"""
        return {
            "users": [
                {"fields": [("email", 1)], "unique": True},
                {"fields": [("created_at", -1)], "unique": False},
                {"fields": [("plan", 1), ("created_at", -1)], "unique": False},
                {"fields": [("mfa_enabled", 1)], "unique": False},
            ],
            "projects": [
                {"fields": [("user_id", 1)], "unique": False},
                {"fields": [("user_id", 1), ("created_at", -1)], "unique": False},
                {"fields": [("status", 1), ("created_at", -1)], "unique": False},
                {"fields": [("name", "text")], "unique": False},
            ],
            "chat_sessions": [
                {"fields": [("user_id", 1)], "unique": False},
                {"fields": [("user_id", 1), ("created_at", -1)], "unique": False},
                {"fields": [("project_id", 1)], "unique": False},
                {"fields": [("created_at", -1)], "unique": False},
            ],
            "token_ledger": [
                {"fields": [("user_id", 1)], "unique": False},
                {"fields": [("user_id", 1), ("created_at", -1)], "unique": False},
                {"fields": [("type", 1)], "unique": False},
                {"fields": [("created_at", -1)], "unique": False},
            ],
            "api_logs": [
                {"fields": [("user_id", 1)], "unique": False},
                {"fields": [("endpoint", 1)], "unique": False},
                {"fields": [("status_code", 1)], "unique": False},
                {"fields": [("created_at", -1)], "unique": False},
            ],
        }


# ==================== QUERY ANALYSIS ====================


class QueryAnalyzer:
    """
    Analyze and optimize database queries
    """

    @staticmethod
    def analyze_query_plan(query_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze MongoDB query plan"""
        return {
            "stage": query_plan.get("stage"),
            "documents_examined": query_plan.get("executionStats", {}).get(
                "totalDocsExamined"
            ),
            "documents_returned": query_plan.get("executionStats", {}).get("nReturned"),
            "execution_time_ms": query_plan.get("executionStats", {})
            .get("executionStages", {})
            .get("executionTimeMillis"),
            "index_used": "COLLSCAN"
            not in str(query_plan.get("executionStats", {}).get("executionStages", {})),
            "efficiency": QueryAnalyzer._calculate_efficiency(query_plan),
        }

    @staticmethod
    def _calculate_efficiency(query_plan: Dict[str, Any]) -> float:
        """Calculate query efficiency (0-1)"""
        stats = query_plan.get("executionStats", {})
        docs_examined = stats.get("totalDocsExamined", 1)
        docs_returned = stats.get("nReturned", 1)

        if docs_examined == 0:
            return 1.0

        efficiency = docs_returned / docs_examined
        return min(efficiency, 1.0)

    @staticmethod
    def get_optimization_suggestions(query_plan: Dict[str, Any]) -> List[str]:
        """Get optimization suggestions based on query plan"""
        suggestions = []
        stats = query_plan.get("executionStats", {})

        docs_examined = stats.get("totalDocsExamined", 0)
        docs_returned = stats.get("nReturned", 0)

        # Check if full collection scan
        if "COLLSCAN" in str(
            query_plan.get("executionStats", {}).get("executionStages", {})
        ):
            suggestions.append(
                "Query is doing a full collection scan. Consider adding an index."
            )

        # Check efficiency
        if docs_examined > 0:
            efficiency = docs_returned / docs_examined
            if efficiency < 0.5:
                suggestions.append(
                    f"Query efficiency is low ({efficiency:.1%}). Consider refining the query or adding an index."
                )

        # Check execution time
        exec_time = stats.get("executionStages", {}).get("executionTimeMillis", 0)
        if exec_time > 1000:
            suggestions.append(
                f"Query execution time is high ({exec_time}ms). Consider optimizing the query or adding an index."
            )

        return suggestions


# ==================== BATCH OPERATIONS ====================


async def batch_insert(
    collection, documents: List[Dict[str, Any]], batch_size: int = 1000
):
    """
    Insert documents in batches to prevent memory issues
    """
    inserted = 0

    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        result = await collection.insert_many(batch)
        inserted += len(result.inserted_ids)

    return inserted


async def batch_update(
    collection, updates: List[Dict[str, Any]], batch_size: int = 1000
):
    """
    Update documents in batches
    """
    updated = 0

    for i in range(0, len(updates), batch_size):
        batch = updates[i : i + batch_size]
        operations = [
            {
                "update_one": {
                    "filter": update.get("filter"),
                    "update": update.get("update"),
                }
            }
            for update in batch
        ]
        result = await collection.bulk_write(operations)
        updated += result.modified_count

    return updated


async def batch_delete(
    collection, filters: List[Dict[str, Any]], batch_size: int = 1000
):
    """
    Delete documents in batches
    """
    deleted = 0

    for i in range(0, len(filters), batch_size):
        batch = filters[i : i + batch_size]
        operations = [{"delete_one": {"filter": filter_}} for filter_ in batch]
        result = await collection.bulk_write(operations)
        deleted += result.deleted_count

    return deleted


# ==================== AGGREGATION OPTIMIZATION ====================


class AggregationOptimizer:
    """
    Optimize MongoDB aggregation pipelines
    """

    @staticmethod
    def optimize_pipeline(pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize aggregation pipeline
        Moves $match early, removes unnecessary stages, etc.
        """
        optimized = []
        match_stages = []

        # Extract all $match stages
        for stage in pipeline:
            if "$match" in stage:
                match_stages.append(stage)
            else:
                optimized.append(stage)

        # Put all $match stages at the beginning
        return match_stages + optimized

    @staticmethod
    def get_pipeline_stats(pipeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about aggregation pipeline"""
        return {
            "stages": len(pipeline),
            "stage_types": [list(stage.keys())[0] for stage in pipeline],
            "has_early_match": any("$match" in stage for stage in pipeline[:1]),
            "has_lookup": any("$lookup" in stage for stage in pipeline),
        }


# ==================== CONNECTION POOLING ====================


class ConnectionPool:
    """
    Manage database connection pool
    """

    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.active_connections = 0
        self.queue = asyncio.Queue()

    async def acquire(self):
        """Acquire a connection from the pool"""
        if self.active_connections < self.max_connections:
            self.active_connections += 1
            return True

        # Wait for a connection to be available
        await self.queue.get()
        return True

    async def release(self):
        """Release a connection back to the pool"""
        self.active_connections -= 1
        self.queue.put_nowait(True)

    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics"""
        return {
            "active": self.active_connections,
            "max": self.max_connections,
            "available": self.max_connections - self.active_connections,
        }


# ==================== QUERY MONITORING ====================


class QueryMonitor:
    """
    Monitor database query performance
    """

    def __init__(self):
        self.queries: List[Dict[str, Any]] = []
        self.slow_query_threshold = 1.0  # 1 second

    def log_query(self, query_name: str, duration: float, success: bool = True):
        """Log a query execution"""
        self.queries.append(
            {
                "name": query_name,
                "duration": duration,
                "success": success,
                "timestamp": datetime.now(),
                "is_slow": duration > self.slow_query_threshold,
            }
        )

    def get_slow_queries(self) -> List[Dict[str, Any]]:
        """Get all slow queries"""
        return [q for q in self.queries if q["is_slow"]]

    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics"""
        if not self.queries:
            return {}

        durations = [q["duration"] for q in self.queries]
        return {
            "total_queries": len(self.queries),
            "avg_duration": sum(durations) / len(durations),
            "max_duration": max(durations),
            "min_duration": min(durations),
            "slow_queries": len(self.get_slow_queries()),
            "success_rate": sum(1 for q in self.queries if q["success"])
            / len(self.queries),
        }


# Global query monitor
query_monitor = QueryMonitor()

# ==================== USAGE EXAMPLE ====================

"""
In server.py:

from query_optimizer import optimize_query, query_cache, QueryAnalyzer

# Use the decorator on query functions
@optimize_query(cache_key="get_user_projects", cache_ttl=3600)
async def get_user_projects(user_id: str):
    return await db.projects.find({'user_id': user_id}).to_list(1000)

# Clear cache when data changes
@api_router.post("/projects")
async def create_project(data: ProjectCreate, user_id: str = Depends(get_current_user)):
    # Create project
    result = await db.projects.insert_one({...})
    
    # Invalidate cache
    query_cache.invalidate(user_id)
    
    return result

# Analyze query performance
query_plan = await db.projects.find({...}).explain()
analysis = QueryAnalyzer.analyze_query_plan(query_plan)
suggestions = QueryAnalyzer.get_optimization_suggestions(query_plan)
"""

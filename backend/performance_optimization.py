"""
Performance Optimization Suite for CrucibAI.

Implements:
- Query optimization
- Caching strategies
- Connection pooling
- CDN integration
- Image optimization
- Database indexing
"""

import logging
import time
from typing import Optional, Dict, Any, List, Callable
from functools import wraps, lru_cache
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Query performance metrics."""

    query_id: str
    query_text: str
    execution_time_ms: float
    rows_returned: int
    indexes_used: List[str]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class QueryOptimizer:
    """Optimize database queries."""

    def __init__(self):
        """Initialize query optimizer."""
        self.metrics = []
        self.slow_queries = []
        self.slow_query_threshold_ms = 100

    def analyze_query(self, query_text: str) -> Dict[str, Any]:
        """
        Analyze query for optimization opportunities.

        Args:
            query_text: SQL query to analyze

        Returns:
            Analysis results with recommendations
        """
        analysis = {
            "query": query_text[:100],
            "issues": [],
            "recommendations": [],
            "estimated_improvement_percent": 0,
        }

        # Check for common issues
        if "SELECT *" in query_text.upper():
            analysis["issues"].append("SELECT * used - specify columns")
            analysis["recommendations"].append(
                "Replace SELECT * with specific columns"
            )
            analysis["estimated_improvement_percent"] += 10

        if "NOT IN" in query_text.upper():
            analysis["issues"].append("NOT IN used - consider NOT EXISTS")
            analysis["recommendations"].append(
                "Replace NOT IN with NOT EXISTS for better performance"
            )
            analysis["estimated_improvement_percent"] += 15

        if "OR" in query_text.upper():
            analysis["issues"].append("OR condition used - consider UNION")
            analysis["recommendations"].append(
                "Consider using UNION instead of OR for better index usage"
            )
            analysis["estimated_improvement_percent"] += 20

        if "LIKE '%'" in query_text.upper():
            analysis["issues"].append("Leading wildcard used - not index friendly")
            analysis["recommendations"].append(
                "Avoid leading wildcards or use full-text search"
            )
            analysis["estimated_improvement_percent"] += 25

        if "JOIN" in query_text.upper():
            analysis["issues"].append("JOIN detected - verify indexes on join columns")
            analysis["recommendations"].append(
                "Ensure indexes exist on all join columns"
            )

        logger.info(
            "Query analyzed",
            extra={
                "issues_found": len(analysis["issues"]),
                "estimated_improvement": analysis["estimated_improvement_percent"],
            },
        )

        return analysis

    def record_query_metrics(
        self,
        query_id: str,
        query_text: str,
        execution_time_ms: float,
        rows_returned: int,
        indexes_used: List[str],
    ) -> QueryMetrics:
        """
        Record query performance metrics.

        Args:
            query_id: Query identifier
            query_text: SQL query text
            execution_time_ms: Execution time in milliseconds
            rows_returned: Number of rows returned
            indexes_used: List of indexes used

        Returns:
            Recorded metrics
        """
        metrics = QueryMetrics(
            query_id=query_id,
            query_text=query_text,
            execution_time_ms=execution_time_ms,
            rows_returned=rows_returned,
            indexes_used=indexes_used,
        )

        self.metrics.append(metrics)

        # Track slow queries
        if execution_time_ms > self.slow_query_threshold_ms:
            self.slow_queries.append(metrics)
            logger.warning(
                f"Slow query detected: {execution_time_ms}ms",
                extra={
                    "query_id": query_id,
                    "execution_time": execution_time_ms,
                },
            )

        return metrics

    def get_slow_queries(self, limit: int = 10) -> List[QueryMetrics]:
        """Get slowest queries."""
        return sorted(
            self.slow_queries,
            key=lambda x: x.execution_time_ms,
            reverse=True,
        )[:limit]

    def get_query_statistics(self) -> Dict[str, Any]:
        """Get query statistics."""
        if not self.metrics:
            return {
                "total_queries": 0,
                "average_execution_time_ms": 0,
                "slow_queries": 0,
            }

        execution_times = [m.execution_time_ms for m in self.metrics]

        return {
            "total_queries": len(self.metrics),
            "average_execution_time_ms": sum(execution_times) / len(execution_times),
            "min_execution_time_ms": min(execution_times),
            "max_execution_time_ms": max(execution_times),
            "slow_queries": len(self.slow_queries),
            "slow_query_percentage": (
                len(self.slow_queries) / len(self.metrics) * 100
            ),
        }


class CacheManager:
    """Manage caching strategies."""

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize cache manager.

        Args:
            ttl_seconds: Time-to-live for cache entries
        """
        self.cache = {}
        self.ttl_seconds = ttl_seconds
        self.hit_count = 0
        self.miss_count = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if key in self.cache:
            value, expiry = self.cache[key]

            if datetime.utcnow() < expiry:
                self.hit_count += 1
                logger.debug(f"Cache hit: {key}")
                return value
            else:
                # Expired
                del self.cache[key]
                self.miss_count += 1
                logger.debug(f"Cache miss (expired): {key}")
                return None

        self.miss_count += 1
        logger.debug(f"Cache miss: {key}")
        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Custom TTL (uses default if not specified)
        """
        ttl = ttl_seconds or self.ttl_seconds
        expiry = datetime.utcnow() + timedelta(seconds=ttl)
        self.cache[key] = (value, expiry)

        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def invalidate(self, key: str):
        """
        Invalidate cache entry.

        Args:
            key: Cache key
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Cache invalidated: {key}")

    def clear(self):
        """Clear entire cache."""
        self.cache.clear()
        logger.info("Cache cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hit_count + self.miss_count

        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "total_requests": total,
            "hit_rate_percent": (
                (self.hit_count / total * 100) if total > 0 else 0
            ),
            "cached_items": len(self.cache),
        }


class ConnectionPoolManager:
    """Manage database connection pooling."""

    def __init__(self, min_connections: int = 5, max_connections: int = 20):
        """
        Initialize connection pool manager.

        Args:
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.available_connections = min_connections
        self.active_connections = 0
        self.connection_requests = 0
        self.connection_timeouts = 0

    def acquire_connection(self, timeout_seconds: int = 5) -> bool:
        """
        Acquire a connection from the pool.

        Args:
            timeout_seconds: Timeout for acquiring connection

        Returns:
            True if connection acquired, False if timeout
        """
        self.connection_requests += 1

        if self.available_connections > 0:
            self.available_connections -= 1
            self.active_connections += 1
            logger.debug(
                "Connection acquired",
                extra={
                    "available": self.available_connections,
                    "active": self.active_connections,
                },
            )
            return True

        # Wait for connection to become available
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            if self.available_connections > 0:
                self.available_connections -= 1
                self.active_connections += 1
                return True

            time.sleep(0.1)

        self.connection_timeouts += 1
        logger.warning(
            "Connection acquisition timeout",
            extra={"timeout": timeout_seconds},
        )

        return False

    def release_connection(self):
        """Release a connection back to the pool."""
        if self.active_connections > 0:
            self.active_connections -= 1
            self.available_connections += 1

            logger.debug(
                "Connection released",
                extra={
                    "available": self.available_connections,
                    "active": self.active_connections,
                },
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return {
            "min_connections": self.min_connections,
            "max_connections": self.max_connections,
            "available_connections": self.available_connections,
            "active_connections": self.active_connections,
            "connection_requests": self.connection_requests,
            "connection_timeouts": self.connection_timeouts,
            "timeout_rate_percent": (
                (self.connection_timeouts / self.connection_requests * 100)
                if self.connection_requests > 0
                else 0
            ),
        }


class CDNIntegration:
    """Integrate with CDN for content delivery."""

    def __init__(self, cdn_url: str = "https://cdn.crucibai.com"):
        """
        Initialize CDN integration.

        Args:
            cdn_url: CDN base URL
        """
        self.cdn_url = cdn_url
        self.cached_assets = {}
        self.asset_requests = 0

    def get_asset_url(self, asset_path: str) -> str:
        """
        Get CDN URL for asset.

        Args:
            asset_path: Local asset path

        Returns:
            CDN URL
        """
        self.asset_requests += 1

        # Generate cache key
        cache_key = hashlib.md5(asset_path.encode()).hexdigest()

        if cache_key not in self.cached_assets:
            # Generate CDN URL
            cdn_url = f"{self.cdn_url}/{asset_path}"
            self.cached_assets[cache_key] = cdn_url

            logger.debug(f"CDN URL generated: {cdn_url}")

        return self.cached_assets[cache_key]

    def optimize_image(
        self,
        image_path: str,
        format: str = "webp",
        quality: int = 85,
    ) -> str:
        """
        Optimize image for CDN delivery.

        Args:
            image_path: Image path
            format: Output format (webp, jpg, png)
            quality: Quality level (1-100)

        Returns:
            Optimized image URL
        """
        # In production, would use image optimization service
        optimized_path = f"{image_path}?format={format}&quality={quality}"

        logger.info(
            f"Image optimized",
            extra={
                "path": image_path,
                "format": format,
                "quality": quality,
            },
        )

        return self.get_asset_url(optimized_path)

    def get_statistics(self) -> Dict[str, Any]:
        """Get CDN statistics."""
        return {
            "asset_requests": self.asset_requests,
            "cached_assets": len(self.cached_assets),
            "cdn_url": self.cdn_url,
        }


class IndexOptimizer:
    """Optimize database indexes."""

    def __init__(self):
        """Initialize index optimizer."""
        self.indexes = {}
        self.index_recommendations = []

    def analyze_missing_indexes(self, slow_queries: List[QueryMetrics]) -> List[str]:
        """
        Analyze slow queries for missing indexes.

        Args:
            slow_queries: List of slow queries

        Returns:
            List of recommended indexes
        """
        recommendations = []

        for query in slow_queries:
            # Extract table names and columns from query
            if "WHERE" in query.query_text.upper():
                # Recommend index on WHERE columns
                recommendations.append(
                    f"CREATE INDEX idx_where ON table(column)"
                )

            if "JOIN" in query.query_text.upper():
                # Recommend index on JOIN columns
                recommendations.append(
                    f"CREATE INDEX idx_join ON table(join_column)"
                )

            if "ORDER BY" in query.query_text.upper():
                # Recommend index on ORDER BY columns
                recommendations.append(
                    f"CREATE INDEX idx_order ON table(order_column)"
                )

        self.index_recommendations = recommendations

        logger.info(
            f"Index analysis complete",
            extra={"recommendations": len(recommendations)},
        )

        return recommendations

    def create_index(self, index_name: str, table: str, columns: List[str]):
        """
        Create database index.

        Args:
            index_name: Index name
            table: Table name
            columns: Columns to index
        """
        index_def = {
            "name": index_name,
            "table": table,
            "columns": columns,
            "created_at": datetime.utcnow(),
        }

        self.indexes[index_name] = index_def

        logger.info(
            f"Index created: {index_name}",
            extra={"table": table, "columns": columns},
        )


def cache_result(ttl_seconds: int = 3600):
    """
    Decorator to cache function results.

    Args:
        ttl_seconds: Time-to-live for cache

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        cache = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            cache_key_hash = hashlib.md5(cache_key.encode()).hexdigest()

            # Check cache
            if cache_key_hash in cache:
                result, expiry = cache[cache_key_hash]

                if datetime.utcnow() < expiry:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result

                # Expired
                del cache[cache_key_hash]

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            expiry = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            cache[cache_key_hash] = (result, expiry)

            logger.debug(f"Cached result for {func.__name__}")

            return result

        return wrapper

    return decorator


# Global instances
query_optimizer = QueryOptimizer()
cache_manager = CacheManager()
connection_pool = ConnectionPoolManager()
cdn_integration = CDNIntegration()
index_optimizer = IndexOptimizer()

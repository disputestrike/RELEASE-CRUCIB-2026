"""
Recursive Learning System for CrucibAI Agents
Enables agents to learn from past executions and improve over time.
Tracks performance metrics, learns from failures, and adapts strategies.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import json
import logging
import hashlib
from enum import Enum

logger = logging.getLogger(__name__)

COLLECTION_AGENT_MEMORY = "agent_memory"
COLLECTION_AGENT_PERFORMANCE = "agent_performance"
COLLECTION_AGENT_LEARNINGS = "agent_learnings"


class ExecutionStatus(str, Enum):
    """Execution result status"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


class AgentMemory:
    """
    Persistent memory system for agents.
    Stores execution history, patterns, and learned strategies.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def record_execution(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        output: Dict[str, Any],
        status: ExecutionStatus,
        duration_ms: float,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record an agent execution for learning."""
        
        execution_record = {
            "_id": self._generate_id(),
            "agent_name": agent_name,
            "input_hash": self._hash_input(input_data),
            "input_summary": self._summarize_input(input_data),
            "output": output,
            "status": status.value,
            "duration_ms": duration_ms,
            "error": error,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "learned": False,
        }
        
        try:
            await self.db[COLLECTION_AGENT_MEMORY].insert_one(execution_record)
            logger.info(f"Recorded execution for {agent_name}: {status.value}")
            return execution_record["_id"]
        except Exception as e:
            logger.error(f"Failed to record execution: {e}")
            return None
    
    async def get_execution_history(
        self,
        agent_name: str,
        limit: int = 50,
        status_filter: Optional[ExecutionStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get recent execution history for an agent."""
        
        query = {"agent_name": agent_name}
        if status_filter:
            query["status"] = status_filter.value
        
        try:
            executions = await self.db[COLLECTION_AGENT_MEMORY].find(query) \
                .sort("timestamp", -1) \
                .limit(limit) \
                .to_list(limit)
            return executions
        except Exception as e:
            logger.error(f"Failed to get execution history: {e}")
            return []
    
    async def extract_patterns(self, agent_name: str) -> Dict[str, Any]:
        """Analyze execution history to extract patterns and learnings."""
        
        executions = await self.get_execution_history(agent_name, limit=100)
        if not executions:
            return {}
        
        # Calculate success rate
        total = len(executions)
        successes = sum(1 for e in executions if e["status"] == ExecutionStatus.SUCCESS.value)
        success_rate = (successes / total * 100) if total > 0 else 0
        
        # Calculate average duration
        durations = [e["duration_ms"] for e in executions if "duration_ms" in e]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Identify common errors
        errors = {}
        for e in executions:
            if e.get("error"):
                error_type = e["error"].split(":")[0]
                errors[error_type] = errors.get(error_type, 0) + 1
        
        # Find successful patterns
        successful_inputs = [e["input_summary"] for e in executions if e["status"] == ExecutionStatus.SUCCESS.value]
        
        patterns = {
            "agent_name": agent_name,
            "total_executions": total,
            "success_rate": success_rate,
            "average_duration_ms": avg_duration,
            "common_errors": errors,
            "successful_patterns": successful_inputs[:5],  # Top 5 patterns
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        return patterns
    
    async def store_learning(
        self,
        agent_name: str,
        learning_type: str,
        content: Dict[str, Any],
        confidence: float = 0.8
    ) -> None:
        """Store a learned insight for future use."""
        
        learning_record = {
            "_id": self._generate_id(),
            "agent_name": agent_name,
            "learning_type": learning_type,  # e.g., "error_recovery", "optimization", "pattern"
            "content": content,
            "confidence": confidence,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "applied_count": 0,
            "success_count": 0,
        }
        
        try:
            await self.db[COLLECTION_AGENT_LEARNINGS].insert_one(learning_record)
            logger.info(f"Stored learning for {agent_name}: {learning_type}")
        except Exception as e:
            logger.error(f"Failed to store learning: {e}")
    
    async def get_learnings(
        self,
        agent_name: str,
        learning_type: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Retrieve learned insights for an agent."""
        
        query = {
            "agent_name": agent_name,
            "confidence": {"$gte": min_confidence}
        }
        
        if learning_type:
            query["learning_type"] = learning_type
        
        try:
            learnings = await self.db[COLLECTION_AGENT_LEARNINGS].find(query) \
                .sort("confidence", -1) \
                .to_list(50)
            return learnings
        except Exception as e:
            logger.error(f"Failed to get learnings: {e}")
            return []
    
    async def apply_learning(self, learning_id: str) -> None:
        """Mark a learning as applied."""
        try:
            await self.db[COLLECTION_AGENT_LEARNINGS].update_one(
                {"_id": learning_id},
                {"$inc": {"applied_count": 1}}
            )
        except Exception as e:
            logger.error(f"Failed to apply learning: {e}")
    
    async def record_learning_success(self, learning_id: str) -> None:
        """Record that a learning led to a successful outcome."""
        try:
            await self.db[COLLECTION_AGENT_LEARNINGS].update_one(
                {"_id": learning_id},
                {"$inc": {"success_count": 1}}
            )
        except Exception as e:
            logger.error(f"Failed to record learning success: {e}")
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _hash_input(self, input_data: Dict[str, Any]) -> str:
        """Hash input for pattern matching."""
        try:
            input_str = json.dumps(input_data, sort_keys=True)
            return hashlib.sha256(input_str.encode()).hexdigest()[:16]
        except:
            return "unknown"
    
    def _summarize_input(self, input_data: Dict[str, Any]) -> str:
        """Create a human-readable summary of input."""
        if isinstance(input_data, dict):
            keys = list(input_data.keys())[:3]
            return f"Input with keys: {', '.join(keys)}"
        return str(input_data)[:100]


class PerformanceTracker:
    """
    Track agent performance metrics over time.
    Identifies bottlenecks and optimization opportunities.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def record_metric(
        self,
        agent_name: str,
        metric_name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a performance metric."""
        
        metric_record = {
            "_id": self._generate_id(),
            "agent_name": agent_name,
            "metric_name": metric_name,
            "value": value,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            await self.db[COLLECTION_AGENT_PERFORMANCE].insert_one(metric_record)
        except Exception as e:
            logger.error(f"Failed to record metric: {e}")
    
    async def get_metrics_summary(
        self,
        agent_name: str,
        metric_name: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get summary of metrics for an agent."""
        
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        query = {
            "agent_name": agent_name,
            "timestamp": {"$gte": cutoff_time}
        }
        
        if metric_name:
            query["metric_name"] = metric_name
        
        try:
            metrics = await self.db[COLLECTION_AGENT_PERFORMANCE].find(query).to_list(1000)
            
            # Calculate statistics
            if not metrics:
                return {}
            
            values = [m["value"] for m in metrics]
            return {
                "agent_name": agent_name,
                "metric_name": metric_name or "all",
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "period_hours": hours,
            }
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        import uuid
        return str(uuid.uuid4())


class AdaptiveStrategy:
    """
    Adaptive execution strategies based on learned patterns.
    Agents can adjust their approach based on historical performance.
    """
    
    def __init__(self, db):
        self.db = db
        self.memory = AgentMemory(db)
    
    async def get_recommended_strategy(
        self,
        agent_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get recommended execution strategy based on learnings.
        """
        
        # Get recent patterns
        patterns = await self.memory.extract_patterns(agent_name)
        
        # Get learnings
        learnings = await self.memory.get_learnings(agent_name, min_confidence=0.7)
        
        # Build strategy
        strategy = {
            "agent_name": agent_name,
            "success_rate": patterns.get("success_rate", 0),
            "estimated_duration_ms": patterns.get("average_duration_ms", 5000),
            "retry_on_errors": list(patterns.get("common_errors", {}).keys()),
            "learnings_to_apply": [l["_id"] for l in learnings[:3]],
            "confidence": min(0.95, patterns.get("success_rate", 50) / 100),
        }
        
        return strategy
    
    async def should_retry(
        self,
        agent_name: str,
        error: str,
        retry_count: int = 0
    ) -> bool:
        """Determine if an agent should retry based on learnings."""
        
        patterns = await self.memory.extract_patterns(agent_name)
        common_errors = patterns.get("common_errors", {})
        
        # Retry if error is common and we haven't exceeded max retries
        error_type = error.split(":")[0]
        is_common_error = error_type in common_errors
        max_retries = 3 if is_common_error else 1
        
        return retry_count < max_retries and is_common_error

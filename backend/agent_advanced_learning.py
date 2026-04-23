"""
Advanced Learning System for Agents
Better pattern recognition, strategy adaptation, and cost optimization.
"""

import json
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import statistics


class PatternRecognizer:
    """Recognizes patterns in agent execution history"""
    
    def __init__(self, db):
        self.db = db
    
    async def extract_patterns(
        self,
        agent_name: str,
        lookback_days: int = 7
    ) -> Dict[str, Any]:
        """Extract patterns from agent execution history"""
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        cutoff_iso = cutoff.isoformat()
        
        # Get execution history
        executions = await self.db["agent_memory"].find({
            "agent_name": agent_name,
            "timestamp": {"$gte": cutoff_iso}
        }).to_list(1000)
        
        if not executions:
            return {}
        
        patterns = {
            "agent_name": agent_name,
            "total_executions": len(executions),
            "success_rate": 0,
            "avg_duration_ms": 0,
            "common_inputs": [],
            "common_errors": [],
            "time_patterns": {},
            "performance_trends": [],
        }
        
        # Success rate
        successes = sum(1 for e in executions if e.get("status") == "success")
        patterns["success_rate"] = (successes / len(executions)) * 100
        
        # Duration stats
        durations = [e.get("duration_ms", 0) for e in executions if e.get("duration_ms")]
        if durations:
            patterns["avg_duration_ms"] = statistics.mean(durations)
            patterns["median_duration_ms"] = statistics.median(durations)
            patterns["std_dev_duration_ms"] = statistics.stdev(durations) if len(durations) > 1 else 0
        
        # Common inputs (by hash)
        input_hashes = defaultdict(int)
        for e in executions:
            input_data = e.get("input_data", {})
            input_hash = str(hash(json.dumps(input_data, sort_keys=True)))
            input_hashes[input_hash] += 1
        
        patterns["common_inputs"] = sorted(
            [{"hash": h, "frequency": c} for h, c in input_hashes.items()],
            key=lambda x: x["frequency"],
            reverse=True
        )[:5]
        
        # Common errors
        errors = defaultdict(int)
        for e in executions:
            if e.get("error"):
                error_type = e.get("error", "unknown").split(":")[0]
                errors[error_type] += 1
        
        patterns["common_errors"] = sorted(
            [{"error": e, "frequency": c} for e, c in errors.items()],
            key=lambda x: x["frequency"],
            reverse=True
        )[:5]
        
        # Time patterns (by hour)
        time_patterns = defaultdict(lambda: {"count": 0, "success": 0})
        for e in executions:
            ts = e.get("timestamp", "")
            if ts:
                hour = datetime.fromisoformat(ts).hour
                time_patterns[hour]["count"] += 1
                if e.get("status") == "success":
                    time_patterns[hour]["success"] += 1
        
        patterns["time_patterns"] = {
            str(h): {
                "count": v["count"],
                "success_rate": (v["success"] / v["count"] * 100) if v["count"] > 0 else 0
            }
            for h, v in sorted(time_patterns.items())
        }
        
        # Performance trends (over time windows)
        window_size = max(1, len(executions) // 5)
        for i in range(0, len(executions), window_size):
            window = executions[i:i+window_size]
            window_success = sum(1 for e in window if e.get("status") == "success")
            window_avg_duration = statistics.mean([e.get("duration_ms", 0) for e in window])
            
            patterns["performance_trends"].append({
                "window": i // window_size,
                "success_rate": (window_success / len(window) * 100) if window else 0,
                "avg_duration_ms": window_avg_duration
            })
        
        return patterns
    
    async def detect_anomalies(
        self,
        agent_name: str,
        lookback_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in agent behavior"""
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        cutoff_iso = cutoff.isoformat()
        
        executions = await self.db["agent_memory"].find({
            "agent_name": agent_name,
            "timestamp": {"$gte": cutoff_iso}
        }).to_list(1000)
        
        if len(executions) < 10:
            return []
        
        anomalies = []
        
        # Duration anomalies
        durations = [e.get("duration_ms", 0) for e in executions]
        mean_duration = statistics.mean(durations)
        std_dev = statistics.stdev(durations) if len(durations) > 1 else 0
        
        for e in executions:
            duration = e.get("duration_ms", 0)
            if std_dev > 0 and abs(duration - mean_duration) > 3 * std_dev:
                anomalies.append({
                    "type": "duration_anomaly",
                    "execution_id": e.get("_id"),
                    "expected_ms": mean_duration,
                    "actual_ms": duration,
                    "deviation_std": (duration - mean_duration) / std_dev
                })
        
        # Error rate anomalies
        recent_errors = sum(1 for e in executions[-20:] if e.get("error"))
        if recent_errors > 10:
            anomalies.append({
                "type": "error_rate_spike",
                "recent_error_count": recent_errors,
                "recent_total": min(20, len(executions)),
                "error_rate": (recent_errors / min(20, len(executions))) * 100
            })
        
        return anomalies


class StrategyAdapterAdvanced:
    """Advanced strategy adaptation based on learnings"""
    
    def __init__(self, db):
        self.db = db
        self.recognizer = PatternRecognizer(db)
    
    async def adapt_strategy(
        self,
        agent_name: str,
        current_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt strategy based on learnings"""
        
        # Get patterns
        patterns = await self.recognizer.extract_patterns(agent_name)
        
        # Get anomalies
        anomalies = await self.recognizer.detect_anomalies(agent_name)
        
        strategy = {
            "agent_name": agent_name,
            "base_confidence": patterns.get("success_rate", 50) / 100,
            "recommendations": [],
            "parameters": {}
        }
        
        # Recommendation 1: Timeout adjustment
        if patterns.get("avg_duration_ms", 0) > 0:
            recommended_timeout = int(patterns["avg_duration_ms"] * 2)
            strategy["parameters"]["timeout_ms"] = recommended_timeout
            strategy["recommendations"].append({
                "type": "timeout",
                "value": recommended_timeout,
                "reason": f"Based on average duration of {patterns['avg_duration_ms']:.0f}ms"
            })
        
        # Recommendation 2: Retry strategy
        if patterns.get("success_rate", 100) < 90:
            strategy["parameters"]["max_retries"] = 3
            strategy["recommendations"].append({
                "type": "retry",
                "value": 3,
                "reason": f"Success rate is {patterns['success_rate']:.1f}%, retries may help"
            })
        else:
            strategy["parameters"]["max_retries"] = 1
        
        # Recommendation 3: Batch size
        if len(patterns.get("common_inputs", [])) > 3:
            strategy["parameters"]["batch_size"] = 5
            strategy["recommendations"].append({
                "type": "batching",
                "value": 5,
                "reason": "Multiple similar inputs detected, batching recommended"
            })
        
        # Recommendation 4: Caching
        if patterns.get("success_rate", 0) > 95:
            strategy["parameters"]["cache_ttl_seconds"] = 3600
            strategy["recommendations"].append({
                "type": "caching",
                "value": 3600,
                "reason": "High success rate, caching safe"
            })
        
        # Recommendation 5: Parallel execution
        if patterns.get("avg_duration_ms", 0) > 1000 and len(patterns.get("common_inputs", [])) > 2:
            strategy["parameters"]["parallel_execution"] = True
            strategy["recommendations"].append({
                "type": "parallelization",
                "value": True,
                "reason": "High latency with multiple input patterns, parallelization recommended"
            })
        
        # Handle anomalies
        if anomalies:
            strategy["anomalies"] = anomalies
            if any(a.get("type") == "error_rate_spike" for a in anomalies):
                strategy["parameters"]["circuit_breaker"] = True
        
        return strategy


class CostOptimizer:
    """Optimize costs based on learnings"""
    
    def __init__(self, db):
        self.db = db
    
    async def analyze_token_costs(
        self,
        agent_name: str,
        lookback_days: int = 7
    ) -> Dict[str, Any]:
        """Analyze token costs for an agent"""
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        cutoff_iso = cutoff.isoformat()
        
        # Get efficiency records
        records = await self.db["prompt_efficiency"].find({
            "agent_name": agent_name,
            "timestamp": {"$gte": cutoff_iso}
        }).to_list(1000)
        
        if not records:
            return {}
        
        # Calculate costs (Cerebras: $0.075 per 1M tokens, Haiku: $0.80 per 1M tokens)
        cerebras_cost_per_token = 0.075 / 1_000_000
        haiku_cost_per_token = 0.80 / 1_000_000
        
        total_tokens = sum(r.get("actual_tokens", 0) for r in records)
        avg_tokens = total_tokens / len(records)
        
        analysis = {
            "agent_name": agent_name,
            "period_days": lookback_days,
            "total_executions": len(records),
            "total_tokens": total_tokens,
            "avg_tokens_per_execution": avg_tokens,
            "costs": {
                "cerebras_total": total_tokens * cerebras_cost_per_token,
                "haiku_total": total_tokens * haiku_cost_per_token,
                "cerebras_per_execution": avg_tokens * cerebras_cost_per_token,
                "haiku_per_execution": avg_tokens * haiku_cost_per_token,
            },
            "optimization_opportunities": []
        }
        
        # Identify optimization opportunities
        if avg_tokens > 500:
            analysis["optimization_opportunities"].append({
                "type": "token_reduction",
                "potential_savings": f"${(avg_tokens * 0.2 * haiku_cost_per_token):.4f} per execution",
                "action": "Reduce prompt verbosity"
            })
        
        # High variance = inconsistent execution
        token_list = [r.get("actual_tokens", 0) for r in records]
        if len(token_list) > 1:
            variance = statistics.variance(token_list)
            if variance > avg_tokens ** 2:
                analysis["optimization_opportunities"].append({
                    "type": "consistency",
                    "issue": "High variance in token usage",
                    "action": "Standardize inputs/outputs"
                })
        
        return analysis
    
    async def get_cost_recommendations(self) -> List[Dict[str, Any]]:
        """Get cost optimization recommendations across all agents"""
        
        # Get all agents with efficiency data
        agents = await self.db["prompt_efficiency"].find({}).to_list(1)
        agent_names = set()
        
        # Get unique agent names
        all_records = await self.db["prompt_efficiency"].find({}).to_list(10000)
        for record in all_records:
            agent_names.add(record.get("agent_name"))
        
        recommendations = []
        
        for agent_name in sorted(agent_names)[:20]:  # Top 20 agents
            analysis = await self.analyze_token_costs(agent_name)
            
            if analysis.get("optimization_opportunities"):
                recommendations.append({
                    "agent": agent_name,
                    "total_cost_haiku": analysis["costs"]["haiku_total"],
                    "opportunities": analysis["optimization_opportunities"]
                })
        
        # Sort by cost
        recommendations.sort(
            key=lambda x: x.get("total_cost_haiku", 0),
            reverse=True
        )
        
        return recommendations[:10]

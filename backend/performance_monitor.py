"""
Performance Monitor: Real-time metrics and monitoring for CrucibAI.
"""

import time
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitors and tracks performance metrics."""

    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_time = datetime.now()
        self.agent_stats = {}
        self.error_log = []

    def record_agent_execution(
        self,
        agent_name: str,
        execution_time: float,
        success: bool,
        tokens_used: int = 0,
        output_size: int = 0,
    ):
        """Record agent execution metrics."""
        metric = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "execution_time": execution_time,
            "success": success,
            "tokens_used": tokens_used,
            "output_size": output_size,
        }

        self.metrics[agent_name].append(metric)

        # Update agent stats
        if agent_name not in self.agent_stats:
            self.agent_stats[agent_name] = {
                "executions": 0,
                "successes": 0,
                "failures": 0,
                "total_time": 0,
                "avg_time": 0,
                "total_tokens": 0,
                "total_output": 0,
            }

        stats = self.agent_stats[agent_name]
        stats["executions"] += 1
        stats["total_time"] += execution_time
        stats["avg_time"] = stats["total_time"] / stats["executions"]
        stats["total_tokens"] += tokens_used
        stats["total_output"] += output_size

        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1

        # Log
        status = "✅" if success else "❌"
        logger.info(
            f"{status} {agent_name}: {execution_time:.2f}s, "
            f"tokens: {tokens_used}, output: {output_size} bytes"
        )

    def record_error(
        self,
        agent_name: str,
        error_type: str,
        error_message: str,
        severity: str = "warning",
    ):
        """Record error event."""
        error = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "type": error_type,
            "message": error_message,
            "severity": severity,
        }

        self.error_log.append(error)
        logger.error(
            f"[{severity.upper()}] {agent_name}: {error_type} - {error_message}"
        )

    def get_agent_stats(self, agent_name: str = None) -> Dict[str, Any]:
        """Get statistics for an agent or all agents."""
        if agent_name:
            if agent_name in self.agent_stats:
                return self.agent_stats[agent_name]
            return {}

        return self.agent_stats

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        total_executions = sum(
            stats["executions"] for stats in self.agent_stats.values()
        )
        total_successes = sum(stats["successes"] for stats in self.agent_stats.values())
        total_failures = sum(stats["failures"] for stats in self.agent_stats.values())
        total_time = sum(stats["total_time"] for stats in self.agent_stats.values())
        total_tokens = sum(stats["total_tokens"] for stats in self.agent_stats.values())
        total_output = sum(stats["total_output"] for stats in self.agent_stats.values())

        success_rate = (
            (total_successes / total_executions * 100) if total_executions > 0 else 0
        )
        avg_time = total_time / total_executions if total_executions > 0 else 0

        return {
            "total_executions": total_executions,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "success_rate": f"{success_rate:.1f}%",
            "total_time": f"{total_time:.2f}s",
            "avg_time_per_execution": f"{avg_time:.2f}s",
            "total_tokens_used": total_tokens,
            "total_output_size": f"{total_output / 1024 / 1024:.2f} MB",
            "uptime": str(datetime.now() - self.start_time),
            "total_errors": len(self.error_log),
        }

    def get_slowest_agents(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get slowest agents by average execution time."""
        agents = []
        for agent_name, stats in self.agent_stats.items():
            agents.append(
                {
                    "agent": agent_name,
                    "avg_time": stats["avg_time"],
                    "executions": stats["executions"],
                }
            )

        # Sort by average time
        agents.sort(key=lambda x: x["avg_time"], reverse=True)
        return agents[:top_n]

    def get_most_used_agents(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get most used agents by execution count."""
        agents = []
        for agent_name, stats in self.agent_stats.items():
            agents.append(
                {
                    "agent": agent_name,
                    "executions": stats["executions"],
                    "success_rate": (
                        (stats["successes"] / stats["executions"] * 100)
                        if stats["executions"] > 0
                        else 0
                    ),
                }
            )

        # Sort by execution count
        agents.sort(key=lambda x: x["executions"], reverse=True)
        return agents[:top_n]

    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        errors_by_type = defaultdict(int)
        errors_by_agent = defaultdict(int)
        errors_by_severity = defaultdict(int)

        for error in self.error_log:
            errors_by_type[error["type"]] += 1
            errors_by_agent[error["agent"]] += 1
            errors_by_severity[error["severity"]] += 1

        return {
            "total_errors": len(self.error_log),
            "errors_by_type": dict(errors_by_type),
            "errors_by_agent": dict(errors_by_agent),
            "errors_by_severity": dict(errors_by_severity),
            "recent_errors": self.error_log[-10:],  # Last 10 errors
        }

    def get_token_efficiency(self) -> Dict[str, Any]:
        """Get token efficiency metrics."""
        efficiency = {}

        for agent_name, stats in self.agent_stats.items():
            if stats["executions"] > 0 and stats["total_output"] > 0:
                tokens_per_output = stats["total_tokens"] / stats["total_output"]
                efficiency[agent_name] = {
                    "total_tokens": stats["total_tokens"],
                    "total_output": stats["total_output"],
                    "tokens_per_byte": f"{tokens_per_output:.4f}",
                    "efficiency_score": f"{(1 / tokens_per_output * 100):.1f}%",
                }

        return efficiency

    def print_report(self):
        """Print comprehensive performance report."""
        print("\n" + "=" * 80)
        print("CRUCIBAI PERFORMANCE REPORT")
        print("=" * 80)

        # Overall summary
        print("\n📊 OVERALL SUMMARY")
        print("-" * 80)
        summary = self.get_performance_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")

        # Slowest agents
        print("\n🐢 SLOWEST AGENTS")
        print("-" * 80)
        slowest = self.get_slowest_agents()
        for agent in slowest:
            print(
                f"  {agent['agent']}: {agent['avg_time']:.2f}s avg ({agent['executions']} executions)"
            )

        # Most used agents
        print("\n⭐ MOST USED AGENTS")
        print("-" * 80)
        most_used = self.get_most_used_agents()
        for agent in most_used:
            print(
                f"  {agent['agent']}: {agent['executions']} executions ({agent['success_rate']:.1f}% success)"
            )

        # Error summary
        print("\n❌ ERROR SUMMARY")
        print("-" * 80)
        error_summary = self.get_error_summary()
        print(f"  Total errors: {error_summary['total_errors']}")
        print(f"  Errors by type: {error_summary['errors_by_type']}")
        print(f"  Errors by agent: {error_summary['errors_by_agent']}")

        # Token efficiency
        print("\n💰 TOKEN EFFICIENCY")
        print("-" * 80)
        efficiency = self.get_token_efficiency()
        for agent, metrics in list(efficiency.items())[:5]:
            print(f"  {agent}: {metrics['efficiency_score']} efficiency")

        print("\n" + "=" * 80 + "\n")

"""
Cost tracking system for CrucibAI builds.

Tracks costs per build, per agent, and identifies optimization opportunities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from metrics_system import metrics


@dataclass
class CostBreakdown:
    """Breakdown of costs for a build."""

    build_id: str
    timestamp: datetime
    llm_cost: float
    compute_cost: float
    storage_cost: float
    api_cost: float
    total_cost: float

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "build_id": self.build_id,
            "timestamp": self.timestamp.isoformat(),
            "llm_cost": self.llm_cost,
            "compute_cost": self.compute_cost,
            "storage_cost": self.storage_cost,
            "api_cost": self.api_cost,
            "total_cost": self.total_cost,
        }


class CostCalculator:
    """Calculates costs for builds and operations."""

    # Pricing (adjust based on actual rates)
    LLM_COST_PER_1K_TOKENS = 0.001  # $0.001 per 1K tokens
    COMPUTE_COST_PER_SECOND = 0.0001  # $0.0001 per second
    STORAGE_COST_PER_GB_MONTH = 0.023  # $0.023 per GB per month
    API_CALL_COST = 0.0001  # $0.0001 per API call

    def calculate_llm_cost(self, tokens_used: int) -> float:
        """Calculate LLM cost based on tokens."""
        return (tokens_used / 1000) * self.LLM_COST_PER_1K_TOKENS

    def calculate_compute_cost(self, duration_seconds: float) -> float:
        """Calculate compute cost based on duration."""
        return duration_seconds * self.COMPUTE_COST_PER_SECOND

    def calculate_storage_cost(self, size_gb: float, days: int) -> float:
        """Calculate storage cost based on size and duration."""
        months = days / 30
        return size_gb * months * self.STORAGE_COST_PER_GB_MONTH

    def calculate_api_cost(self, api_calls: int) -> float:
        """Calculate API cost based on number of calls."""
        return api_calls * self.API_CALL_COST

    def calculate_build_cost(
        self,
        build_id: str,
        tokens_used: int,
        duration_seconds: float,
        api_calls: int = 0,
        storage_gb: float = 0.0,
    ) -> CostBreakdown:
        """Calculate total cost for a build."""
        llm_cost = self.calculate_llm_cost(tokens_used)
        compute_cost = self.calculate_compute_cost(duration_seconds)
        api_cost = self.calculate_api_cost(api_calls)
        storage_cost = self.calculate_storage_cost(storage_gb, 1)  # 1 day

        total_cost = llm_cost + compute_cost + api_cost + storage_cost

        # Record in metrics
        metrics.build_cost_dollars.observe(total_cost)

        return CostBreakdown(
            build_id=build_id,
            timestamp=datetime.utcnow(),
            llm_cost=llm_cost,
            compute_cost=compute_cost,
            storage_cost=storage_cost,
            api_cost=api_cost,
            total_cost=total_cost,
        )


class CostAnalyzer:
    """Analyzes costs and identifies optimization opportunities."""

    def __init__(self):
        """Initialize cost analyzer."""
        self.cost_history: List[CostBreakdown] = []

    def add_cost(self, cost_breakdown: CostBreakdown):
        """Add cost breakdown to history."""
        self.cost_history.append(cost_breakdown)

    def get_average_build_cost(self) -> float:
        """Get average cost per build."""
        if not self.cost_history:
            return 0.0
        total = sum(c.total_cost for c in self.cost_history)
        return total / len(self.cost_history)

    def get_total_cost(self) -> float:
        """Get total cost across all builds."""
        return sum(c.total_cost for c in self.cost_history)

    def get_cost_by_component(self) -> Dict[str, float]:
        """Get total cost breakdown by component."""
        if not self.cost_history:
            return {}

        return {
            "llm": sum(c.llm_cost for c in self.cost_history),
            "compute": sum(c.compute_cost for c in self.cost_history),
            "storage": sum(c.storage_cost for c in self.cost_history),
            "api": sum(c.api_cost for c in self.cost_history),
        }

    def get_cost_trends(self, window_size: int = 10) -> Dict[str, float]:
        """Get cost trends over recent builds."""
        if len(self.cost_history) < window_size:
            return {}

        recent = self.cost_history[-window_size:]
        older = self.cost_history[-window_size * 2 : -window_size]

        recent_avg = sum(c.total_cost for c in recent) / len(recent)
        older_avg = (
            sum(c.total_cost for c in older) / len(older) if older else recent_avg
        )

        percent_change = (
            ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        )

        return {
            "recent_average": recent_avg,
            "older_average": older_avg,
            "percent_change": percent_change,
            "trend": "increasing" if percent_change > 0 else "decreasing",
        }

    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations based on cost analysis."""
        recommendations = []

        if not self.cost_history:
            return recommendations

        cost_by_component = self.get_cost_by_component()
        total_cost = sum(cost_by_component.values())

        # LLM optimization
        if cost_by_component.get("llm", 0) / total_cost > 0.5:
            recommendations.append(
                "LLM costs are >50% of total. Consider: "
                "1) Caching responses 2) Using smaller models 3) Batch processing"
            )

        # Compute optimization
        if cost_by_component.get("compute", 0) / total_cost > 0.3:
            recommendations.append(
                "Compute costs are >30% of total. Consider: "
                "1) Optimizing agent execution 2) Parallel processing 3) Resource pooling"
            )

        # Storage optimization
        if cost_by_component.get("storage", 0) / total_cost > 0.2:
            recommendations.append(
                "Storage costs are >20% of total. Consider: "
                "1) Archiving old builds 2) Compression 3) Cleanup policies"
            )

        # Trend analysis
        trends = self.get_cost_trends()
        if trends.get("percent_change", 0) > 10:
            recommendations.append(
                f"Costs are increasing {trends['percent_change']:.1f}%. "
                "Review recent changes and optimize."
            )

        return recommendations

    def get_cost_report(self) -> Dict:
        """Generate comprehensive cost report."""
        return {
            "total_builds": len(self.cost_history),
            "total_cost": self.get_total_cost(),
            "average_cost_per_build": self.get_average_build_cost(),
            "cost_by_component": self.get_cost_by_component(),
            "trends": self.get_cost_trends(),
            "recommendations": self.get_optimization_recommendations(),
        }


# Global instances
cost_calculator = CostCalculator()
cost_analyzer = CostAnalyzer()

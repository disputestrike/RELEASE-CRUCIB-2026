"""
Agent Prompt Optimization System
Optimizes prompts for each agent to reduce tokens and improve quality.
"""

import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class PromptOptimizer:
    """Optimizes agent prompts for token efficiency and quality"""
    
    def __init__(self, db):
        self.db = db
        self.cache = {}
    
    # Optimized system prompts for each agent type
    AGENT_PROMPTS = {
        "Planner": """You are a project planner. Analyze requirements and create concise action plans.
Format: JSON with steps, dependencies, and timeline. Be direct.""",
        
        "Requirements Clarifier": """Clarify requirements. Ask 2-3 key questions if needed.
Output: JSON with clarified requirements and assumptions.""",
        
        "Stack Selector": """Select optimal tech stack. Consider: scalability, cost, team skills.
Output: JSON with stack choice and justification.""",
        
        "Backend Generation": """Generate backend code. Use best practices.
Output: Code with comments.""",
        
        "Frontend Generation": """Generate frontend code. Use React/Vue best practices.
Output: Code with comments.""",
        
        "Database Agent": """Design database schema. Normalize and optimize.
Output: SQL DDL statements.""",
        
        "Design Agent": """Create design specifications. Include colors, typography, spacing.
Output: JSON design system.""",
        
        "Deployment Agent": """Plan deployment strategy. Consider: CI/CD, monitoring, rollback.
Output: JSON deployment plan.""",
        
        "Security Checker": """Check security vulnerabilities. List risks and mitigations.
Output: JSON security report.""",
        
        "Performance Analyzer": """Analyze performance metrics. Identify bottlenecks.
Output: JSON performance report with recommendations.""",
        
        "Code Review": """Review code for quality, security, performance.
Output: JSON review with issues and suggestions.""",
        
        "Test Generation": """Generate unit tests. Cover happy path and edge cases.
Output: Test code.""",
        
        "Documentation Agent": """Generate clear documentation. Include examples.
Output: Markdown documentation.""",
        
        "API Integration": """Integrate external APIs. Handle auth, errors, rate limits.
Output: Code with error handling.""",
        
        "Browser Tool Agent": """Automate browser tasks. Use Selenium/Playwright patterns.
Output: Code with comments.""",
        
        "File Tool Agent": """Handle file operations. Support multiple formats.
Output: Code with error handling.""",
        
        "Database Operations": """Execute database operations safely. Use parameterized queries.
Output: SQL or ORM code.""",
        
        "Deployment Operations": """Execute deployment. Handle rollback on failure.
Output: Deployment script.""",
        
        "Vibe Analyzer": """Analyze project vibe/mood/aesthetic. Be concise.
Output: JSON with vibe assessment.""",
        
        "Voice Context": """Convert voice/speech to code context. Extract key points.
Output: JSON context.""",
    }
    
    async def get_optimized_prompt(
        self,
        agent_name: str,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get optimized prompt for agent.
        
        Args:
            agent_name: Name of the agent
            task_description: What the agent needs to do
            context: Optional additional context
        
        Returns:
            Optimized prompt string
        """
        
        # Get base prompt
        base_prompt = self.AGENT_PROMPTS.get(agent_name, f"You are a {agent_name}.")
        
        # Build optimized prompt
        prompt = base_prompt
        
        # Add task
        prompt += f"\n\nTask: {task_description}"
        
        # Add context if provided
        if context:
            context_str = json.dumps(context, indent=2)
            prompt += f"\n\nContext:\n{context_str}"
        
        # Add output format hint
        prompt += "\n\nBe concise. Output valid JSON when applicable."
        
        return prompt
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens in text (rough: 1 token ≈ 4 chars)"""
        return len(text) // 4
    
    async def analyze_prompt_efficiency(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        tokens_used: int
    ) -> Dict[str, Any]:
        """
        Analyze prompt efficiency.
        
        Args:
            agent_name: Agent name
            prompt: Prompt used
            response: Response from agent
            tokens_used: Actual tokens used
        
        Returns:
            Efficiency analysis
        """
        
        prompt_tokens = self.estimate_tokens(prompt)
        response_tokens = self.estimate_tokens(response)
        estimated_total = prompt_tokens + response_tokens
        
        efficiency = {
            "agent_name": agent_name,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "estimated_tokens": estimated_total,
            "actual_tokens": tokens_used,
            "efficiency_ratio": estimated_total / max(tokens_used, 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Store analysis
        await self.db["prompt_efficiency"].insert_one(efficiency)
        
        return efficiency
    
    async def get_optimization_suggestions(
        self,
        agent_name: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get optimization suggestions based on recent runs.
        
        Args:
            agent_name: Agent name
            hours: Look back this many hours
        
        Returns:
            List of suggestions
        """
        
        # Get recent efficiency data
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        
        records = await self.db["prompt_efficiency"].find({
            "agent_name": agent_name,
            "timestamp": {"$gte": cutoff}
        }).to_list(100)
        
        if not records:
            return []
        
        # Analyze patterns
        avg_efficiency = sum(r.get("efficiency_ratio", 1) for r in records) / len(records)
        avg_tokens = sum(r.get("actual_tokens", 0) for r in records) / len(records)
        
        suggestions = []
        
        # Suggestion 1: Token usage
        if avg_tokens > 1000:
            suggestions.append({
                "type": "token_reduction",
                "priority": "high",
                "suggestion": "Reduce prompt verbosity or use more specific instructions",
                "potential_savings": f"{int(avg_tokens * 0.2)} tokens per call"
            })
        
        # Suggestion 2: Efficiency
        if avg_efficiency < 0.8:
            suggestions.append({
                "type": "efficiency",
                "priority": "medium",
                "suggestion": "Consider using more structured output format",
                "potential_improvement": "10-20% token reduction"
            })
        
        # Suggestion 3: Caching
        if len(records) > 10:
            suggestions.append({
                "type": "caching",
                "priority": "medium",
                "suggestion": "Cache common prompts and responses",
                "potential_savings": "30-50% for repeated tasks"
            })
        
        return suggestions


class TokenOptimizer:
    """Optimizes token usage across all agents"""
    
    def __init__(self, db):
        self.db = db
    
    async def get_token_usage_summary(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get token usage summary for all agents"""
        
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        
        # Get all token usage records
        records = await self.db["prompt_efficiency"].find({
            "timestamp": {"$gte": cutoff}
        }).to_list(1000)
        
        if not records:
            return {"total_tokens": 0, "agents": {}}
        
        # Group by agent
        by_agent = {}
        total_tokens = 0
        
        for record in records:
            agent = record.get("agent_name", "unknown")
            tokens = record.get("actual_tokens", 0)
            
            if agent not in by_agent:
                by_agent[agent] = {
                    "calls": 0,
                    "total_tokens": 0,
                    "avg_tokens": 0,
                    "max_tokens": 0,
                    "min_tokens": float('inf')
                }
            
            by_agent[agent]["calls"] += 1
            by_agent[agent]["total_tokens"] += tokens
            by_agent[agent]["max_tokens"] = max(by_agent[agent]["max_tokens"], tokens)
            by_agent[agent]["min_tokens"] = min(by_agent[agent]["min_tokens"], tokens)
            total_tokens += tokens
        
        # Calculate averages
        for agent in by_agent:
            calls = by_agent[agent]["calls"]
            by_agent[agent]["avg_tokens"] = by_agent[agent]["total_tokens"] // calls
            if by_agent[agent]["min_tokens"] == float('inf'):
                by_agent[agent]["min_tokens"] = 0
        
        return {
            "total_tokens": total_tokens,
            "total_calls": len(records),
            "avg_tokens_per_call": total_tokens // len(records),
            "agents": by_agent,
            "period_hours": hours
        }
    
    async def get_optimization_targets(self) -> List[Dict[str, Any]]:
        """Identify agents with highest token usage for optimization"""
        
        summary = await self.get_token_usage_summary(hours=24)
        
        # Sort by total tokens
        agents = sorted(
            summary.get("agents", {}).items(),
            key=lambda x: x[1]["total_tokens"],
            reverse=True
        )
        
        targets = []
        for agent_name, stats in agents[:10]:  # Top 10
            targets.append({
                "agent": agent_name,
                "total_tokens": stats["total_tokens"],
                "calls": stats["calls"],
                "avg_tokens": stats["avg_tokens"],
                "optimization_potential": f"{int(stats['avg_tokens'] * 0.2)}-{int(stats['avg_tokens'] * 0.3)} tokens per call"
            })
        
        return targets

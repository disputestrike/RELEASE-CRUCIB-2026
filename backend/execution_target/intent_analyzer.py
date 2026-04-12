"""
Intent Analysis Module - Auto-detects optimal execution targets
Analyzes user requests to automatically determine which execution targets to use
"""

import re
from typing import Dict, List, Tuple
from enum import Enum


class ExecutionTarget(Enum):
    """Available execution targets for CrucibAI"""

    FULLSTACK_WEB = "fullstack-web"
    NEXTJS_APP = "nextjs-app"
    MARKETING_STATIC = "marketing-static"
    API_BACKEND_FIRST = "api-backend-first"
    AGENTS_AUTOMATION = "agents-automation"


class IntentAnalyzer:
    """Auto-detects execution targets from user requests"""

    TARGET_KEYWORDS = {
        ExecutionTarget.FULLSTACK_WEB: [
            "dashboard",
            "app",
            "interface",
            "ui",
            "real-time",
            "interactive",
            "web app",
            "webapp",
            "frontend",
            "react",
            "responsive",
        ],
        ExecutionTarget.NEXTJS_APP: [
            "next.js",
            "nextjs",
            "ssg",
            "ssr",
            "static generation",
            "page",
            "route",
        ],
        ExecutionTarget.MARKETING_STATIC: [
            "landing",
            "static",
            "marketing",
            "brochure",
            "blog",
            "content",
            "documentation",
        ],
        ExecutionTarget.API_BACKEND_FIRST: [
            "api",
            "backend",
            "database",
            "rest",
            "graphql",
            "endpoint",
            "service",
        ],
        ExecutionTarget.AGENTS_AUTOMATION: [
            "agent",
            "automation",
            "workflow",
            "task",
            "bot",
            "intelligent",
        ],
    }

    FEATURE_REQUIREMENTS = {
        "real-time": ExecutionTarget.FULLSTACK_WEB,
        "websocket": ExecutionTarget.FULLSTACK_WEB,
        "live": ExecutionTarget.FULLSTACK_WEB,
        "database": ExecutionTarget.API_BACKEND_FIRST,
        "persistence": ExecutionTarget.API_BACKEND_FIRST,
        "seo": ExecutionTarget.NEXTJS_APP,
        "automation": ExecutionTarget.AGENTS_AUTOMATION,
        "workflow": ExecutionTarget.AGENTS_AUTOMATION,
    }

    def analyze(self, user_request: str) -> Dict:
        """Analyze request and suggest execution targets"""
        request_lower = user_request.lower()

        # Score each target
        target_scores = self._score_targets(request_lower)
        ranked = sorted(
            target_scores.items(), key=lambda x: x[1]["score"], reverse=True
        )

        if not ranked:
            primary = ExecutionTarget.FULLSTACK_WEB
            confidence = 40
            reasoning = "Default to Full-stack Web"
        else:
            primary = ranked[0][0]
            confidence = min(95, ranked[0][1]["score"])
            reasoning = ranked[0][1]["reasoning"]

        secondary = [
            t[0] for t in ranked[1:3] if t[0] != primary and t[1]["score"] > 30
        ]

        return {
            "primary_target": primary.value,
            "secondary_targets": [t.value for t in secondary],
            "confidence": confidence,
            "reasoning": reasoning,
            "features_detected": self._detect_features(request_lower),
            "all_scores": {t.value: s["score"] for t, s in target_scores.items()},
        }

    def _score_targets(self, request: str) -> Dict:
        """Score each target based on keyword/feature matching"""
        scores = {}

        for target in ExecutionTarget:
            score = 0
            reasons = []

            # Keyword matching
            keywords = self.TARGET_KEYWORDS.get(target, [])
            found = [kw for kw in keywords if kw in request]
            score += len(found) * 10

            if found:
                reasons.append(f"Keywords: {', '.join(found[:2])}")

            # Feature matching
            for feature, ftarget in self.FEATURE_REQUIREMENTS.items():
                if feature in request and ftarget == target:
                    score += 25
                    reasons.append(f"Feature: {feature}")

            scores[target] = {
                "score": score,
                "reasoning": " | ".join(reasons) or "Generic match",
            }

        return scores

    def _detect_features(self, request: str) -> List[str]:
        """Detect specific features"""
        return [f for f in self.FEATURE_REQUIREMENTS.keys() if f in request]

"""
Build Target Inference Engine

Analyzes user goals to automatically detect and suggest the most appropriate build target.
Returns:
- A single recommended target (high confidence)
- Multiple candidates (user should choose)
- None (ask user to specify)
"""

import re
from typing import Optional, List, Tuple
from .build_targets import BUILD_TARGETS, normalize_build_target


# Keywords that strongly indicate specific build targets
TARGET_KEYWORDS = {
    "full_system_generator": [
        "full system",
        "fullsystem",
        "multi-stack",
        "everything",
        "all-in-one",
        "complete platform",
        "swarm",
        "complex",
        "large scale",
        "enterprise",
        "microservices",
    ],
    "next_app_router": [
        "next.js",
        "nextjs",
        "next",
        "app router",
        "server components",
        "rsc",
        "streaming",
        "edge functions",
        "vercel",
    ],
    "static_site": [
        "landing page",
        "marketing site",
        "static",
        "brochure",
        "portfolio",
        "documentation",
        "blog",
        "static site",
        "marketing",
        "public site",
        "corporate site",
        "showcase",
    ],
    "mobile_expo": [
        "mobile app",
        "native app",
        "expo",
        "react native",
        "react-native",
        "ios app",
        "android app",
        "app store",
        "google play",
        "testflight",
        "eas build",
    ],
    "api_backend": [
        "api",
        "backend",
        "server",
        "rest api",
        "rest",
        "fastapi",
        "flask",
        "express",
        "nodejs",
        "node.js",
        "python backend",
        "database",
        "microservice",
        "service",
        "webhook",
        "endpoint",
        "routes",
        "endpoints",
    ],
    "internal_admin_tool": [
        "internal admin",
        "admin tool",
        "admin panel",
        "internal tool",
        "back office",
        "backoffice",
        "operations tool",
        "data tables",
        "approval workflow",
        "approval workflows",
        "form workflow",
        "forms",
    ],
    "agent_workflow": [
        "agent",
        "automation",
        "workflow",
        "crew",
        "langgraph",
        "task automation",
        "background job",
        "scheduler",
        "cron",
        "batch",
        "automation script",
        "bot",
        "orchestration",
    ],
    "vite_react": [
        "app",
        "application",
        "web app",
        "webapp",
        "spa",
        "single page",
        "interactive",
        "dashboard",
        "ui",
        "user interface",
        "frontend",
        "react",
        "component",
        "website",
        "web",
        "client",
    ],
}

# Keywords that rule OUT certain targets
EXCLUSION_KEYWORDS = {
    "api_backend": ["ui", "interface", "component", "page", "layout", "react", "frontend"],
    "static_site": ["interactive", "app", "application", "dashboard", "api", "backend"],
    "internal_admin_tool": ["marketing", "landing page", "portfolio", "brochure"],
    "agent_workflow": ["ui", "interface", "frontend", "component", "visual"],
}

# Patterns that indicate specific build types
PATTERN_INDICATORS = [
    # Full system
    (r"build.*everything|everything.*build|full.*system|multi.*stack|both.*frontend.*backend", "full_system_generator"),
    # Next.js
    (r"next\.?js|nextjs|server\s+component|app\s+router|rsc|edge\s+function", "next_app_router"),
    # Static/Marketing
    (r"landing\s+page|marketing\s+site|static\s+site|brochure|portfolio|showcase", "static_site"),
    # Mobile / Expo
    (r"mobile\s+app|native\s+app|react\s+native|react-native|expo|ios\s+app|android\s+app|app\s+store|google\s+play|testflight|eas\s+build", "mobile_expo"),
    # Internal admin / back-office tools
    (r"internal\s+admin|admin\s+tool|admin\s+panel|internal\s+tool|back\s*office|data\s+tables|approval\s+workflows?", "internal_admin_tool"),
    # API/Backend
    (r"api\s+only|backend\s+only|rest\s+api|fastapi|express|python\s+server|database", "api_backend"),
    # Agents/Automation
    (r"automat|agent|crew|workflow|task\s+automation|background\s+job", "agent_workflow"),
]


def infer_build_target(goal: str) -> Tuple[Optional[str], Optional[List[str]], str]:
    """
    Analyze goal text to infer the appropriate build target.

    Returns:
        (recommended_target, candidate_targets, reasoning)
        - recommended_target: Single best target, or None if ambiguous
        - candidate_targets: List of equally likely targets, or None
        - reasoning: Human-readable explanation
    """
    if not goal or not isinstance(goal, str):
        return None, None, "Goal is empty. Please describe what you want to build."

    goal_lower = goal.lower().strip()

    # Step 1: Check pattern indicators (highest confidence)
    for pattern, target in PATTERN_INDICATORS:
        if re.search(pattern, goal_lower):
            reason = f"Detected '{target}' from goal keywords."
            return normalize_build_target(target), None, reason

    # Step 2: Keyword scoring
    scores = {}
    for target, keywords in TARGET_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in goal_lower)
        if score > 0:
            scores[target] = score

    # Step 3: Apply exclusion rules
    for target, exclude_kws in EXCLUSION_KEYWORDS.items():
        for kw in exclude_kws:
            if kw in goal_lower:
                # Reduce score if this target conflicts with explicit keywords
                scores[target] = max(0, scores.get(target, 0) - 0.5)

    if not scores:
        return None, None, "Could not determine build type from goal. Please specify: app/website, API, automation, or landing page?"

    # Step 4: Determine result
    max_score = max(scores.values())
    candidates = [t for t, s in scores.items() if s == max_score]

    if len(candidates) == 1:
        target = candidates[0]
        return normalize_build_target(target), None, f"Best match: {BUILD_TARGETS[target]['label']}"

    # Multiple equally likely candidates
    normalized_candidates = [normalize_build_target(t) for t in candidates]
    candidate_labels = [BUILD_TARGETS[normalize_build_target(t)]['label'] for t in candidates]
    reasoning = f"Multiple possibilities: {', '.join(candidate_labels)}. Which one?"

    return None, normalized_candidates, reasoning


def ask_for_build_target(goal: str) -> dict:
    """
    Prepare a structured question to ask the user to pick a build target.

    Returns:
        {
            "need_clarification": True,
            "inferred_target": str | None,
            "candidates": [str] | None,
            "reasoning": str,
            "question": "Which build type matches your goal?",
            "options": [
                {
                    "id": "full_system_generator",
                    "label": "Workspace build",
                    "description": "..."
                },
                ...
            ]
        }
    """
    inferred, candidates, reasoning = infer_build_target(goal)

    # If we have a strong inference, return it without asking
    if inferred:
        return {
            "need_clarification": False,
            "inferred_target": inferred,
            "candidates": None,
            "reasoning": reasoning,
            "question": None,
            "options": None,
        }

    # If multiple candidates, ask user to choose
    if candidates:
        options = []
        for target_id in candidates:
            target = BUILD_TARGETS[target_id]
            options.append({
                "id": target_id,
                "label": target["label"],
                "tagline": target["tagline"],
                "description": f"{target['label']}: {target['tagline']}",
            })

        return {
            "need_clarification": True,
            "inferred_target": None,
            "candidates": candidates,
            "reasoning": reasoning,
            "question": f"What type of build do you want? {reasoning}",
            "options": options,
        }

    # No inference possible, show all options
    return {
        "need_clarification": True,
        "inferred_target": None,
        "candidates": None,
        "reasoning": reasoning,
        "question": reasoning,
        "options": [
            {
                "id": target_id,
                "label": target["label"],
                "tagline": target["tagline"],
                "description": f"{target['label']}: {target['tagline']}",
            }
            for target_id in ["full_system_generator", "vite_react", "next_app_router", "static_site", "internal_admin_tool", "mobile_expo", "api_backend", "agent_workflow"]
        ],
    }


# Test cases
if __name__ == "__main__":
    test_goals = [
        "Build me a landing page for my startup",
        "I need a full-stack web app with React and Python backend",
        "Create a REST API with FastAPI",
        "Build a Next.js app with server components",
        "I want to automate my workflow",
        "Make me an app",
        "Build everything - frontend, backend, database, all in one",
    ]

    for goal in test_goals:
        target, candidates, reason = infer_build_target(goal)
        print(f"\nGoal: {goal}")
        print(f"  Target: {target}")
        print(f"  Candidates: {candidates}")
        print(f"  Reason: {reason}")

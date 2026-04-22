"""
intent_extractor.py — Extract and validate user intent from prompts
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class IntentExtractor:
    """Extract structured requirements from user prompts."""

    # Common framework/library keywords
    FRAMEWORKS = {
        "react": ["react", "jsx", "nextjs", "next.js", "next"],
        "vue": ["vue", "vuejs", "vue.js"],
        "angular": ["angular"],
        "svelte": ["svelte"],
        "solid": ["solidjs", "solid"],
        "fastapi": ["fastapi", "fast api"],
        "flask": ["flask"],
        "django": ["django"],
        "fastify": ["fastify"],
        "express": ["express", "expressjs", "express.js"],
        "nodejs": ["node", "nodejs", "node.js"],
        "python": ["python", "py"],
        "typescript": ["typescript", "ts"],
        "javascript": ["javascript", "js"],
        "html": ["html"],
        "css": ["css", "tailwind", "styled-components"],
    }

    # Color/style keywords
    COLORS = {
        "red": ["red", "crimson", "scarlet"],
        "blue": ["blue", "navy", "cyan"],
        "green": ["green", "emerald", "lime"],
        "yellow": ["yellow", "gold"],
        "purple": ["purple", "violet", "indigo"],
        "pink": ["pink", "magenta"],
        "white": ["white", "light", "bright"],
        "black": ["black", "dark", "dark mode"],
        "gray": ["gray", "grey"],
    }

    # Object/entity keywords
    OBJECTS = {
        "button": ["button", "btn"],
        "card": ["card", "box"],
        "form": ["form", "input"],
        "table": ["table", "data table"],
        "list": ["list", "menu"],
        "modal": ["modal", "dialog"],
        "navbar": ["navbar", "nav", "navigation"],
        "footer": ["footer"],
        "sidebar": ["sidebar"],
        "dropdown": ["dropdown", "select"],
        "carousel": ["carousel", "slider"],
        "app": ["app", "application", "website", "site"],
        "dashboard": ["dashboard", "panel"],
        "chart": ["chart", "graph"],
        "map": ["map"],
    }

    @staticmethod
    async def extract_constraints(prompt: str) -> Dict[str, Any]:
        """
        Extract structured constraints from a user prompt.

        Returns:
            Dict with extracted frameworks, colors, objects, and raw keywords
        """
        if not prompt:
            return {
                "frameworks": [],
                "colors": [],
                "objects": [],
                "keywords": [],
                "constraints_found": 0,
                "confidence": 0.0,
            }

        prompt_lower = prompt.lower()
        constraints = []
        found_frameworks = []
        found_colors = []
        found_objects = []

        # Extract frameworks
        for framework, keywords in IntentExtractor.FRAMEWORKS.items():
            for keyword in keywords:
                if re.search(rf'\b{re.escape(keyword)}\b', prompt_lower):
                    if framework not in found_frameworks:
                        found_frameworks.append(framework)
                    constraints.append(f"framework: {framework}")
                    break

        # Extract colors
        for color, keywords in IntentExtractor.COLORS.items():
            for keyword in keywords:
                if re.search(rf'\b{re.escape(keyword)}\b', prompt_lower):
                    if color not in found_colors:
                        found_colors.append(color)
                    constraints.append(f"color: {color}")
                    break

        # Extract objects/entities
        for obj, keywords in IntentExtractor.OBJECTS.items():
            for keyword in keywords:
                if re.search(rf'\b{re.escape(keyword)}\b', prompt_lower):
                    if obj not in found_objects:
                        found_objects.append(obj)
                    constraints.append(f"object: {obj}")
                    break

        # Extract specific patterns
        # Look for "must", "should", "require", "only", "no", "don't" modifiers
        must_patterns = re.findall(r'(must|should|require|needs?|only|no|don\'t|cannot)\s+([a-zA-Z\s]+)', prompt_lower)
        important_keywords = []
        for modal, phrase in must_patterns:
            important_keywords.append(phrase.strip())

        # Calculate confidence based on number of specific constraints found
        total_constraints = len(found_frameworks) + len(found_colors) + len(found_objects) + len(important_keywords)
        confidence = min(0.95, max(0.3, total_constraints / 10.0))

        return {
            "frameworks": found_frameworks,
            "colors": found_colors,
            "objects": found_objects,
            "important_keywords": important_keywords,
            "constraints_found": len(constraints),
            "raw_constraints": constraints,
            "confidence": confidence,
            "original_prompt": prompt[:500],  # Store first 500 chars
        }

    @staticmethod
    async def validate_code_matches_intent(
        generated_code: str,
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate that generated code contains evidence of meeting constraints.

        Returns:
            Validation report with met/violated constraints
        """
        if not generated_code or not constraints:
            return {
                "is_valid": False,
                "reason": "Missing code or constraints",
                "constraints_met": [],
                "constraints_violated": [],
                "confidence": 0.0,
            }

        code_lower = generated_code.lower()
        met = []
        violated = []

        # Check frameworks
        for framework in constraints.get("frameworks", []):
            framework_keywords = IntentExtractor.FRAMEWORKS.get(framework, [])
            found = any(kw in code_lower for kw in framework_keywords)
            if found:
                met.append(f"framework: {framework}")
            else:
                violated.append(f"framework: {framework}")

        # Check colors (look for color values, color classes, or CSS)
        for color in constraints.get("colors", []):
            # Look for color in hex, rgb, named colors, or Tailwind classes
            color_patterns = [
                rf'#{color[:3]}',  # Hex shorthand
                rf'{color}',  # Direct mention
                rf'color.*{color}',
                rf'{color}.*color',
                rf'bg-{color}',  # Tailwind
                rf'text-{color}',  # Tailwind
            ]
            found = any(re.search(pattern, code_lower) for pattern in color_patterns)
            if found:
                met.append(f"color: {color}")
            else:
                violated.append(f"color: {color}")

        # Check objects/components
        for obj in constraints.get("objects", []):
            # Look for component names or related keywords
            pattern = rf'\b{re.escape(obj)}\b'
            found = bool(re.search(pattern, code_lower))
            if found:
                met.append(f"object: {obj}")
            else:
                violated.append(f"object: {obj}")

        # Calculate confidence and validity
        total_constraints = len(met) + len(violated)
        if total_constraints == 0:
            return {
                "is_valid": True,  # No constraints to validate
                "constraints_met": met,
                "constraints_violated": violated,
                "confidence": 0.5,
            }

        match_ratio = len(met) / total_constraints
        is_valid = match_ratio >= 0.7  # 70% threshold

        return {
            "is_valid": is_valid,
            "constraints_met": met,
            "constraints_violated": violated,
            "match_ratio": match_ratio,
            "confidence": min(0.95, match_ratio),
        }

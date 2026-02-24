"""
Vibe Analysis Engine for CrucibAI
Analyzes natural language input to detect coding style, design preferences, and project complexity
"""
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CodeStyle(Enum):
    MINIMALIST = "minimalist"
    VERBOSE = "verbose"
    FUNCTIONAL = "functional"
    OOP = "oop"
    PROCEDURAL = "procedural"


class DesignPreference(Enum):
    DARK_MODE = "dark_mode"
    LIGHT_MODE = "light_mode"
    ANIMATED = "animated"
    MINIMAL = "minimal"
    COLORFUL = "colorful"
    PROFESSIONAL = "professional"
    PLAYFUL = "playful"
    ACCESSIBLE = "accessible"


class ProjectComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


@dataclass
class VibeAnalysis:
    raw_input: str
    code_style: CodeStyle
    design_preferences: List[DesignPreference]
    project_complexity: ProjectComplexity
    detected_frameworks: List[str]
    detected_languages: List[str]
    accessibility_focus: bool
    performance_focus: bool
    security_focus: bool
    testing_focus: bool
    documentation_focus: bool
    confidence_score: float
    keywords: List[str]
    suggestions: List[str]
    mood: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_input": self.raw_input,
            "code_style": self.code_style.value,
            "design_preferences": [p.value for p in self.design_preferences],
            "project_complexity": self.project_complexity.value,
            "detected_frameworks": self.detected_frameworks,
            "detected_languages": self.detected_languages,
            "accessibility_focus": self.accessibility_focus,
            "performance_focus": self.performance_focus,
            "security_focus": self.security_focus,
            "testing_focus": self.testing_focus,
            "documentation_focus": self.documentation_focus,
            "confidence_score": self.confidence_score,
            "keywords": self.keywords,
            "suggestions": self.suggestions,
            "mood": self.mood,
        }


class VibeAnalyzer:
    def __init__(self):
        self.minimalist_keywords = ["clean", "simple", "minimal", "concise", "lean", "lightweight", "efficient", "fast", "quick", "short", "compact"]
        self.verbose_keywords = ["detailed", "comprehensive", "thorough", "well-documented", "explained", "clear", "descriptive", "verbose", "full"]
        self.functional_keywords = ["functional", "immutable", "pure", "lambda", "map", "filter", "reduce", "compose", "higher-order", "declarative"]
        self.oop_keywords = ["class", "object", "inheritance", "polymorphism", "encapsulation", "method", "property", "instance", "constructor", "interface"]
        self.framework_keywords = {
            "react": ["react", "jsx", "hooks", "component", "state", "props"],
            "vue": ["vue", "vuex", "template", "directive"],
            "angular": ["angular", "typescript", "decorator", "service", "module"],
            "svelte": ["svelte", "reactive", "store", "animation"],
            "nextjs": ["next", "nextjs", "ssr", "static", "api routes"],
            "django": ["django", "model", "view", "template", "orm"],
            "flask": ["flask", "blueprint", "route", "decorator"],
            "fastapi": ["fastapi", "async", "endpoint", "pydantic"],
            "express": ["express", "middleware", "route", "handler"],
        }
        self.language_keywords = {
            "javascript": ["js", "javascript", "node", "npm", "yarn"],
            "typescript": ["typescript", "ts", "type", "interface", "generic"],
            "python": ["python", "py", "pip", "django", "flask"],
            "java": ["java", "spring", "maven", "gradle", "jvm"],
            "go": ["go", "golang", "goroutine", "channel"],
            "rust": ["rust", "cargo", "ownership", "borrow"],
        }
        self.design_keywords = {
            "dark_mode": ["dark", "dark mode", "night", "black", "dark theme"],
            "light_mode": ["light", "light mode", "bright", "white", "light theme"],
            "animated": ["animated", "animation", "motion", "smooth", "transition", "interactive"],
            "minimal": ["minimal", "minimalist", "clean", "simple", "flat"],
            "colorful": ["colorful", "vibrant", "bright", "gradient", "color"],
            "professional": ["professional", "corporate", "business", "formal", "enterprise"],
            "playful": ["playful", "fun", "creative", "quirky", "unique"],
            "accessible": ["accessible", "a11y", "wcag", "inclusive"],
        }
        self.focus_keywords = {
            "accessibility": ["accessible", "a11y", "wcag", "inclusive", "screen reader"],
            "performance": ["fast", "performance", "optimize", "speed", "efficient"],
            "security": ["secure", "security", "encryption", "auth", "protection"],
            "testing": ["test", "testing", "unit test", "integration test", "coverage"],
            "documentation": ["document", "doc", "readme", "comment", "explain"],
        }
        self.complexity_indicators = {
            "simple": ["simple", "basic", "starter", "beginner", "todo", "crud"],
            "moderate": ["medium", "moderate", "intermediate", "feature", "dashboard"],
            "complex": ["complex", "advanced", "sophisticated", "algorithm", "optimization"],
            "enterprise": ["enterprise", "scale", "distributed", "microservice", "cloud"],
        }

    def analyze(self, text: str) -> VibeAnalysis:
        text_lower = text.lower()
        code_style = self._detect_code_style(text_lower)
        design_prefs = self._detect_design_preferences(text_lower)
        complexity = self._detect_complexity(text_lower)
        frameworks = self._detect_frameworks(text_lower)
        languages = self._detect_languages(text_lower)
        accessibility = self._has_focus(text_lower, "accessibility")
        performance = self._has_focus(text_lower, "performance")
        security = self._has_focus(text_lower, "security")
        testing = self._has_focus(text_lower, "testing")
        documentation = self._has_focus(text_lower, "documentation")
        keywords = self._extract_keywords(text_lower)
        mood = self._detect_mood(text_lower)
        suggestions = self._generate_suggestions(code_style, design_prefs, complexity, frameworks, languages)
        confidence = self._calculate_confidence(code_style, design_prefs, complexity, frameworks, languages)
        return VibeAnalysis(
            raw_input=text,
            code_style=code_style,
            design_preferences=design_prefs,
            project_complexity=complexity,
            detected_frameworks=frameworks,
            detected_languages=languages,
            accessibility_focus=accessibility,
            performance_focus=performance,
            security_focus=security,
            testing_focus=testing,
            documentation_focus=documentation,
            confidence_score=confidence,
            keywords=keywords,
            suggestions=suggestions,
            mood=mood,
        )

    def _detect_code_style(self, text: str) -> CodeStyle:
        scores = {
            CodeStyle.MINIMALIST: sum(1 for kw in self.minimalist_keywords if kw in text),
            CodeStyle.VERBOSE: sum(1 for kw in self.verbose_keywords if kw in text),
            CodeStyle.FUNCTIONAL: sum(1 for kw in self.functional_keywords if kw in text),
            CodeStyle.OOP: sum(1 for kw in self.oop_keywords if kw in text),
            CodeStyle.PROCEDURAL: 0,
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else CodeStyle.OOP

    def _detect_design_preferences(self, text: str) -> List[DesignPreference]:
        prefs = []
        for pref, keywords in self.design_keywords.items():
            if any(kw in text for kw in keywords):
                try:
                    prefs.append(DesignPreference[pref.upper()])
                except KeyError:
                    pass
        return prefs if prefs else [DesignPreference.PROFESSIONAL]

    def _detect_complexity(self, text: str) -> ProjectComplexity:
        for comp, keywords in self.complexity_indicators.items():
            if any(kw in text for kw in keywords):
                try:
                    return ProjectComplexity[comp.upper()]
                except KeyError:
                    pass
        return ProjectComplexity.MODERATE

    def _detect_frameworks(self, text: str) -> List[str]:
        return [fw for fw, kws in self.framework_keywords.items() if any(kw in text for kw in kws)]

    def _detect_languages(self, text: str) -> List[str]:
        return [lang for lang, kws in self.language_keywords.items() if any(kw in text for kw in kws)]

    def _has_focus(self, text: str, focus_area: str) -> bool:
        kws = self.focus_keywords.get(focus_area, [])
        return any(kw in text for kw in kws)

    def _extract_keywords(self, text: str) -> List[str]:
        all_kw = set(self.minimalist_keywords + self.verbose_keywords + self.functional_keywords + self.oop_keywords)
        words = [w.strip(".,!?;:") for w in text.split() if w.strip(".,!?;:") in all_kw]
        return list(dict.fromkeys(words))[:10]

    def _detect_mood(self, text: str) -> str:
        scores = {
            "professional": sum(1 for w in ["professional", "enterprise", "business", "corporate"] if w in text),
            "casual": sum(1 for w in ["casual", "fun", "simple", "easy", "quick"] if w in text),
            "creative": sum(1 for w in ["creative", "unique", "design", "beautiful", "elegant"] if w in text),
            "technical": sum(1 for w in ["algorithm", "optimization", "performance", "architecture"] if w in text),
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "professional"

    def _generate_suggestions(self, code_style, design_prefs, complexity, frameworks, languages) -> List[str]:
        suggestions = []
        if code_style == CodeStyle.MINIMALIST:
            suggestions.append("Use concise variable names and avoid unnecessary comments")
        elif code_style == CodeStyle.VERBOSE:
            suggestions.append("Add comprehensive documentation and detailed comments")
        if DesignPreference.ACCESSIBLE in design_prefs:
            suggestions.append("Ensure WCAG 2.1 AA compliance for accessibility")
        if not frameworks:
            suggestions.append("Consider using React or Vue for UI development")
        return suggestions

    def _calculate_confidence(self, code_style, design_prefs, complexity, frameworks, languages) -> float:
        score = 0.5
        if frameworks:
            score += 0.15
        if languages:
            score += 0.15
        if design_prefs:
            score += 0.1
        if code_style != CodeStyle.OOP:
            score += 0.1
        return min(score, 1.0)


vibe_analyzer = VibeAnalyzer()

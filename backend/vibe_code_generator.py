"""
Vibe-Aware Code Generator for CrucibAI
Generates code that matches detected vibe and preferences
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from vibe_analysis import CodeStyle, DesignPreference, ProjectComplexity, VibeAnalysis

logger = logging.getLogger(__name__)


@dataclass
class GeneratedCode:
    language: str
    framework: str
    code: str
    style: str
    comments_level: str
    structure: str
    explanation: str


class VibeCodeGenerator:
    def generate(
        self, vibe: VibeAnalysis, prompt: str, language: Optional[str] = None
    ) -> GeneratedCode:
        lang = language or (
            vibe.detected_languages[0] if vibe.detected_languages else "javascript"
        )
        framework = (
            vibe.detected_frameworks[0] if vibe.detected_frameworks else "vanilla"
        )
        code = self._generate_code_for_language(lang, framework, prompt, vibe)
        comments_level = (
            "minimal"
            if vibe.code_style == CodeStyle.MINIMALIST
            else (
                "comprehensive" if vibe.code_style == CodeStyle.VERBOSE else "moderate"
            )
        )
        structure = (
            "simple"
            if vibe.project_complexity == ProjectComplexity.SIMPLE
            else (
                "scalable"
                if vibe.project_complexity == ProjectComplexity.ENTERPRISE
                else "modular"
            )
        )
        explanation = f"Generated {lang} code using {framework}. Style: {vibe.code_style.value}, Complexity: {vibe.project_complexity.value}, Mood: {vibe.mood}."
        return GeneratedCode(
            language=lang,
            framework=framework,
            code=code,
            style=vibe.code_style.value,
            comments_level=comments_level,
            structure=structure,
            explanation=explanation,
        )

    def _generate_code_for_language(
        self, language: str, framework: str, prompt: str, vibe: VibeAnalysis
    ) -> str:
        if language in ("javascript", "typescript"):
            if framework == "react":
                return self._generate_react_code(prompt, vibe)
            elif framework == "vue":
                return self._generate_vue_code(prompt, vibe)
            return self._generate_vanilla_js_code(prompt, vibe)
        elif language == "python":
            if framework == "fastapi":
                return self._generate_fastapi_code(prompt, vibe)
            return self._generate_python_code(prompt, vibe)
        return f"// {prompt}\n// Language: {language}\nfunction main() {{ }}\nmain();"

    def _generate_react_code(self, prompt: str, vibe: VibeAnalysis) -> str:
        if vibe.code_style == CodeStyle.MINIMALIST:
            return f"export default function Component() {{\n  return (\n    <div>\n      {{/* {prompt} */}}\n    </div>\n  );\n}}"
        return f"import React, {{ useState }} from 'react';\nexport default function Component() {{\n  const [state, setState] = useState(null);\n  return (\n    <div>\n      {{/* {prompt} */}}\n    </div>\n  );\n}}"

    def _generate_vue_code(self, prompt: str, vibe: VibeAnalysis) -> str:
        return f"<template>\n  <div>{{{{ {prompt} }}}}</div>\n</template>\n<script>\nexport default {{ name: 'Component' }};\n</script>"

    def _generate_vanilla_js_code(self, prompt: str, vibe: VibeAnalysis) -> str:
        return f"const el = document.querySelector('#app');\nel.innerHTML = `{prompt}`;"

    def _generate_python_code(self, prompt: str, vibe: VibeAnalysis) -> str:
        return f'def main():\n    # {prompt}\n    pass\n\nif __name__ == "__main__":\n    main()'

    def _generate_fastapi_code(self, prompt: str, vibe: VibeAnalysis) -> str:
        return f'from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/")\nasync def root():\n    return {{"message": "{prompt}"}}'


vibe_code_generator = VibeCodeGenerator()

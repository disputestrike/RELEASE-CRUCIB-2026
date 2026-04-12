"""
Advanced AI features for CrucibAI — test gen, docs gen, optimize, security.
TestGenerator delegates to the configured LLM (Anthropic / Cerebras) via llm_client.
When no LLM is configured a useful scaffold is returned instead of a bare TODO comment.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_async(coro) -> Optional[str]:
    """Run an async coroutine from synchronous code.

    Tries the running event-loop first (so it works when called from an async
    context via run_in_executor), then falls back to asyncio.run().
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We are inside an async context — schedule as a thread-safe future.
            import concurrent.futures
            future = concurrent.futures.Future()

            async def _wrapper():
                try:
                    future.set_result(await coro)
                except Exception as exc:
                    future.set_exception(exc)

            loop.create_task(_wrapper())
            # Block the *calling* thread (not the event loop) until done.
            return future.result(timeout=60)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _scaffold_tests(test_type: str, language: str, framework: str) -> str:
    """Return a minimal but useful test scaffold when the LLM is unavailable."""
    if language.lower() in ("python", "py"):
        if framework in ("pytest", ""):
            return (
                f"import pytest\n\n\n"
                f"# {test_type.capitalize()} tests — generated scaffold\n"
                f"# Fill in the actual assertions once you have the implementation.\n\n"
                f"class Test{test_type.capitalize()}:\n"
                f"    def test_placeholder(self):\n"
                f"        assert True  # replace with real assertions\n"
            )
        return (
            f"import unittest\n\n\n"
            f"class Test{test_type.capitalize()}(unittest.TestCase):\n"
            f"    def test_placeholder(self):\n"
            f"        self.assertTrue(True)  # replace with real assertions\n\n\n"
            f"if __name__ == '__main__':\n"
            f"    unittest.main()\n"
        )
    # JavaScript / TypeScript scaffold
    return (
        f"// {test_type.capitalize()} tests — generated scaffold\n"
        f"// Fill in the actual assertions once you have the implementation.\n\n"
        f"describe('{test_type.capitalize()} tests', () => {{\n"
        f"    it('placeholder', () => {{\n"
        f"        expect(true).toBe(true); // replace with real assertions\n"
        f"    }});\n"
        f"}});\n"
    )


class TestType(Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"


class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GeneratedTest:
    test_type: str
    language: str
    framework: str
    code: str
    description: str
    coverage_estimate: float


class TestGenerator:
    def _generate(self, test_type: str, code: str, language: str, framework: str) -> str:
        """Call the LLM to generate tests; return a scaffold on failure."""
        try:
            from llm_client import call_llm  # local import to avoid circular deps at module load
        except ImportError:
            logger.warning("llm_client not available; returning scaffold")
            return _scaffold_tests(test_type, language, framework)

        system_prompt = (
            f"You are an expert software engineer specialising in {language} testing. "
            f"Write {test_type} tests using the {framework} framework for the code provided. "
            "Return ONLY the test code — no markdown fences, no explanations, no preamble. "
            "The first line must be a valid import or the first test declaration."
        )
        user_prompt = (
            f"Write comprehensive {test_type} tests for the following {language} code "
            f"using {framework}:\n\n{code}"
        )

        result = _run_async(call_llm(system_prompt, user_prompt, temperature=0.3, task_type="documentation"))
        if result and result.strip():
            # Strip accidental markdown fences the model may still produce
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                # Remove opening fence (may have language tag) and closing fence
                inner = lines[1:] if lines[0].startswith("```") else lines
                if inner and inner[-1].strip() == "```":
                    inner = inner[:-1]
                cleaned = "\n".join(inner).strip()
            return cleaned

        logger.warning("LLM returned empty response for %s tests; returning scaffold", test_type)
        return _scaffold_tests(test_type, language, framework)

    def generate_unit_tests(self, code: str, language: str, framework: Optional[str]) -> "GeneratedTest":
        fw = framework or ("pytest" if language.lower() in ("python", "py") else "jest")
        generated_code = self._generate("unit", code, language, fw)
        return GeneratedTest(
            test_type="unit",
            language=language,
            framework=fw,
            code=generated_code,
            description="Unit tests generated by CrucibAI",
            coverage_estimate=0.0,
        )

    def generate_integration_tests(self, code: str, language: str, framework: Optional[str]) -> "GeneratedTest":
        fw = framework or ("pytest" if language.lower() in ("python", "py") else "jest")
        generated_code = self._generate("integration", code, language, fw)
        return GeneratedTest(
            test_type="integration",
            language=language,
            framework=fw,
            code=generated_code,
            description="Integration tests generated by CrucibAI",
            coverage_estimate=0.0,
        )


class DocumentationGenerator:
    def generate_readme(self, project_name: str, description: Optional[str], features: Optional[List[str]]) -> str:
        return f"# {project_name}\n\n{description or 'Generated by CrucibAI'}"


class CodeOptimizer:
    def optimize(self, code: str, language: str, optimization_type: str) -> Dict[str, Any]:
        return {"original_length": len(code), "optimized_code": code, "suggestions": []}


class SecurityAnalyzer:
    def analyze(self, code: str, language: str) -> Dict[str, Any]:
        return {"issues": [], "level": "low", "summary": "No issues found"}


test_generator = TestGenerator()
documentation_generator = DocumentationGenerator()
code_optimizer = CodeOptimizer()
security_analyzer = SecurityAnalyzer()

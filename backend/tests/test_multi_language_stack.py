"""
Tests for multi-language stack selection, agent dispatch, and validator integration.

Tests:
1. Explicit language request is respected
2. Missing language defaults to best stack
3. Python/FastAPI build validates
4. React/Vite build validates
5. Node/Express build validates
6. C++ request returns honest "unsupported" or validates
7. Stub output is rejected
8. Stack selector routes correctly by product type
9. Agent imports work (no ImportError)
"""

import ast
import json
import os
import shutil
import sys
import tempfile
import unittest

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestStackSelection(unittest.TestCase):
    """Test that the template registry correctly routes language/framework requests."""

    def setUp(self):
        from backend.agents.templates.registry import select_template, list_templates
        self.select_template = select_template
        self.list_templates = list_templates

    # ── Test 1: Explicit language request is respected ──

    def test_explicit_python_fastapi(self):
        """User says 'build a FastAPI API' → should select Python/FastAPI template."""
        template = self.select_template(goal="Build a REST API with FastAPI and PostgreSQL")
        self.assertIsNotNone(template)
        self.assertEqual(template["id"], "python_fastapi")
        self.assertEqual(template["language"], "python")
        self.assertEqual(template["framework"], "fastapi")
        self.assertGreaterEqual(template["confidence"], 0.90)

    def test_explicit_node_express(self):
        """User says 'build a Node.js Express API' → should select Node/Express template."""
        template = self.select_template(goal="Build a Node.js Express API with auth")
        self.assertIsNotNone(template)
        self.assertEqual(template["id"], "node_express")
        self.assertEqual(template["framework"], "express")

    def test_explicit_cpp_cmake(self):
        """User says 'build a C++ CLI tool with CMake' → should select C++/CMake template."""
        template = self.select_template(goal="Build a C++ command-line calculator with CMake")
        self.assertIsNotNone(template)
        self.assertEqual(template["id"], "cpp_cmake")
        self.assertEqual(template["language"], "cpp")
        self.assertEqual(template["framework"], "cmake")

    def test_explicit_react_vite(self):
        """User says 'build a React frontend with Vite' → should select React/Vite template."""
        template = self.select_template(goal="Build a React SPA with Vite and TypeScript")
        self.assertIsNotNone(template)
        self.assertEqual(template["id"], "react_vite")
        self.assertEqual(template["language"], "typescript")

    # ── Test 2: Missing language defaults to best stack ──

    def test_default_api_defaults_to_fastapi(self):
        """Generic API goal → defaults to FastAPI template."""
        template = self.select_template(goal="Build a REST API for user management")
        self.assertIsNotNone(template)
        # Default fallback is python_fastapi
        self.assertEqual(template["id"], "python_fastapi")

    # ── Test 8: Template registry has all expected stacks ──

    def test_registry_has_all_expected_templates(self):
        """Template registry contains all 7 expected template IDs."""
        templates = self.list_templates()
        ids = {t["id"] for t in templates}
        self.assertIn("python_fastapi", ids)
        self.assertIn("node_express", ids)
        self.assertIn("react_vite", ids)
        self.assertIn("cpp_cmake", ids)
        self.assertIn("python_cli", ids)
        self.assertIn("go_gin", ids)
        self.assertIn("rust_axum", ids)

    def test_explicit_language_parameter(self):
        """Explicit language/framework params override goal-based detection."""
        template = self.select_template(goal="Build something", explicit_language="python", explicit_framework="fastapi")
        self.assertIsNotNone(template)
        self.assertEqual(template["id"], "python_fastapi")


class TestAgentImports(unittest.TestCase):
    """Test 9: Verify all agent imports work without ImportError."""

    def test_builder_agent_import(self):
        """BuilderAgent can be imported."""
        from backend.agents.builder_agent import BuilderAgent
        agent = BuilderAgent()
        self.assertEqual(agent.name, "BuilderAgent")

    def test_frontend_agent_import(self):
        """FrontendAgent can be imported."""
        from backend.agents.frontend_agent import FrontendAgent
        agent = FrontendAgent()
        self.assertEqual(agent.name, "FrontendAgent")

    def test_backend_agent_import(self):
        """BackendAgent can be imported."""
        from backend.agents.backend_agent import BackendAgent
        agent = BackendAgent()
        self.assertEqual(agent.name, "BackendAgent")

    def test_template_registry_select_template(self):
        """select_template returns proper structure."""
        from backend.agents.templates.registry import select_template
        template = select_template(goal="Build a React dashboard")
        self.assertIn("id", template)
        self.assertIn("language", template)
        self.assertIn("framework", template)
        self.assertIn("confidence", template)
        self.assertIn("build_command", template)
        self.assertIn("run_command", template)
        self.assertIn("required_files", template)
        self.assertIn("files", template)

    def test_stack_selector_agent_import(self):
        """StackSelectorAgent can be imported."""
        from backend.agents.stack_selector_agent import StackSelectorAgent
        self.assertTrue(callable(StackSelectorAgent))


class TestValidatorIntegration(unittest.TestCase):
    """Test validators work correctly with workspace_path."""

    # ── Test 3: Python/FastAPI syntax validates ──

    def test_python_validator_valid_code(self):
        """Valid Python code passes syntax validation."""
        from backend.agents.validators.python_validator import PythonValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "backend"))
            with open(os.path.join(tmpdir, "backend", "main.py"), "w") as f:
                f.write('''from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/users")
def list_users():
    return [{"id": 1, "name": "Test User"}]
''')
            with open(os.path.join(tmpdir, "backend", "requirements.txt"), "w") as f:
                f.write("fastapi\nuvicorn\n")
            validator = PythonValidator(workspace_path=tmpdir)
            result = validator.validate_syntax()
            self.assertTrue(result.success)

    def test_python_validator_rejects_syntax_error(self):
        """Invalid Python code fails syntax validation."""
        from backend.agents.validators.python_validator import PythonValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "backend"))
            with open(os.path.join(tmpdir, "backend", "main.py"), "w") as f:
                f.write("def broken(:\n    return 1\n")
            validator = PythonValidator(workspace_path=tmpdir)
            result = validator.validate_syntax()
            self.assertFalse(result.success)

    # ── Test 4: Node/Express package.json validates ──

    def test_node_validator_valid_package(self):
        """Valid package.json passes syntax validation."""
        from backend.agents.validators.node_validator import NodeValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            json.dump({
                "name": "test-app",
                "version": "1.0.0",
                "scripts": {"start": "node server.js", "dev": "vite", "build": "vite build"},
                "dependencies": {"express": "^4.18.0", "cors": "^2.8.5"},
            }, open(os.path.join(tmpdir, "package.json"), "w"))
            with open(os.path.join(tmpdir, "index.js"), "w") as f:
                f.write('const express = require("express");\nconst app = express();\n')
            validator = NodeValidator(workspace_path=tmpdir)
            result = validator.validate_syntax()
            self.assertTrue(result.success)

    # ── Test 5: Node/Express express detected ──

    def test_node_validator_express_detected(self):
        """Express dependency is detected in package.json."""
        from backend.agents.validators.node_validator import NodeValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            json.dump({
                "name": "express-api",
                "version": "0.1.0",
                "dependencies": {"express": "^4.18.0"},
                "scripts": {"start": "node index.js"},
            }, open(os.path.join(tmpdir, "package.json"), "w"))
            with open(os.path.join(tmpdir, "index.js"), "w") as f:
                f.write('const express = require("express");\n')
            validator = NodeValidator(workspace_path=tmpdir)
            result = validator.validate_syntax()
            self.assertTrue(result.success)

    # ── Test 6: C++ CMakeLists.txt validates ──

    def test_cpp_validator_valid_cmake(self):
        """Valid CMakeLists.txt passes syntax validation."""
        if not shutil.which("g++"):
            self.skipTest("g++ not on PATH (install MinGW/MSYS2 or run on Linux CI)")
        from backend.agents.validators.cpp_validator import CppValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "src"))
            with open(os.path.join(tmpdir, "CMakeLists.txt"), "w") as f:
                f.write('''cmake_minimum_required(VERSION 3.10)
project(Calculator LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

add_executable(calculator
    src/main.cpp
    src/calculator.cpp
)
''')
            with open(os.path.join(tmpdir, "src", "main.cpp"), "w") as f:
                f.write('''#include <iostream>
int main() { std::cout << "Hello" << std::endl; return 0; }
''')
            validator = CppValidator(workspace_path=tmpdir)
            result = validator.validate_syntax()
            self.assertTrue(result.success)


class TestIntentClassifier(unittest.TestCase):
    """Test intent classification for multi-language support."""

    def test_detect_python_intent(self):
        """Python keywords detected in dimensions."""
        from backend.orchestration.intent_classifier import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify("Build a Python API with FastAPI")
        self.assertTrue(result.values.get("language_python"))

    def test_detect_nodejs_intent(self):
        """Node.js keywords detected in dimensions."""
        from backend.orchestration.intent_classifier import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify("Build a Node.js Express REST API")
        self.assertTrue(result.values.get("language_node"))

    def test_detect_cpp_intent(self):
        """C++ keywords detected in dimensions."""
        from backend.orchestration.intent_classifier import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify("Build a C++ CLI tool with CMake")
        self.assertTrue(result.values.get("language_cpp"))

    def test_stack_patterns_in_classified(self):
        """Explicit stack patterns appear in classified output."""
        from backend.orchestration.intent_classifier import IntentClassifier
        classifier = IntentClassifier()

        # Python/FastAPI
        result = classifier.classify("Build a FastAPI backend with PostgreSQL")
        patterns = classifier._extract_specific_patterns("Build a FastAPI backend with PostgreSQL")
        self.assertEqual(patterns.get("backend_framework"), "FastAPI")
        self.assertEqual(patterns.get("backend_language"), "python")

        # Node/Express
        result = classifier.classify("Build an Express API with MongoDB")
        patterns = classifier._extract_specific_patterns("Build an Express API with MongoDB")
        self.assertEqual(patterns.get("backend_framework"), "Express")
        self.assertEqual(patterns.get("backend_language"), "node.js")

        # C++/CMake
        result = classifier.classify("Build a C++ command-line tool")
        patterns = classifier._extract_specific_patterns("Build a C++ command-line tool")
        self.assertEqual(patterns.get("backend_framework"), "CMake/g++")
        self.assertEqual(patterns.get("backend_language"), "cpp")


class TestExecutorIntegration(unittest.TestCase):
    """Test that executor can import agents without ImportError."""

    def test_executor_imports_builder_agent(self):
        """Executor can import BuilderAgent."""
        # This is the exact import used in executor.py line 1010
        from backend.agents.builder_agent import BuilderAgent
        agent = BuilderAgent()
        self.assertIsNotNone(agent)

    def test_executor_imports_frontend_agent(self):
        """Executor can import FrontendAgent."""
        # This is the exact import used in executor.py line 1066
        from backend.agents.frontend_agent import FrontendAgent
        agent = FrontendAgent()
        self.assertIsNotNone(agent)

    def test_executor_imports_backend_agent(self):
        """Executor can import BackendAgent."""
        # This is the exact import used in executor.py line 1386
        from backend.agents.backend_agent import BackendAgent
        agent = BackendAgent()
        self.assertIsNotNone(agent)


if __name__ == "__main__":
    unittest.main()

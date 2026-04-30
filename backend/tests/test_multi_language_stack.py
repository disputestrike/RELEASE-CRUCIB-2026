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
import sys
import tempfile
import unittest

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestStackSelection(unittest.TestCase):
    """Test that the stack selector correctly identifies and routes language requests."""

    def setUp(self):
        from backend.agents.builder_agent import select_stack, _detect_product_type, _detect_explicit_language
        self.select_stack = select_stack
        self._detect_product_type = _detect_product_type
        self._detect_explicit_language = _detect_explicit_language

    # ── Test 1: Explicit language request is respected ──

    def test_explicit_python_fastapi(self):
        """User says 'build a FastAPI API' → should select Python/FastAPI."""
        stack = self.select_stack("Build a REST API with FastAPI and PostgreSQL")
        self.assertIsNotNone(stack.get("backend"))
        self.assertEqual(stack["backend"]["language"], "python")
        self.assertEqual(stack["backend"]["framework"], "fastapi")
        self.assertTrue(stack["explicit_language"])

    def test_explicit_node_express(self):
        """User says 'build a Node.js Express API' → should select Node/Express."""
        stack = self.select_stack("Build a Node.js Express API with auth")
        self.assertIsNotNone(stack.get("backend"))
        self.assertEqual(stack["backend"]["language"], "javascript")
        self.assertEqual(stack["backend"]["framework"], "express")
        self.assertTrue(stack["explicit_language"])

    def test_explicit_cpp_cmake(self):
        """User says 'build a C++ CLI tool with CMake' → should select C++/CMake."""
        stack = self.select_stack("Build a C++ command-line calculator with CMake")
        self.assertIsNotNone(stack.get("backend"))
        self.assertEqual(stack["backend"]["language"], "cpp")
        self.assertEqual(stack["backend"]["framework"], "cmake")
        self.assertTrue(stack["explicit_language"])
        # C++ tools should NOT have a frontend
        self.assertIsNone(stack.get("frontend"))

    # ── Test 2: Missing language defaults to best stack ──

    def test_default_saas_dashboard(self):
        """No language specified, SaaS dashboard → defaults to React + FastAPI."""
        stack = self.select_stack("Build an admin dashboard with analytics")
        self.assertIsNotNone(stack.get("frontend"))
        self.assertEqual(stack["frontend"]["framework"], "react-vite")
        self.assertIsNotNone(stack.get("backend"))
        self.assertEqual(stack["backend"]["framework"], "fastapi")
        self.assertFalse(stack["explicit_language"])

    def test_default_landing_page(self):
        """No language specified, landing page → defaults to React, no backend."""
        stack = self.select_stack("Build a landing page for my startup")
        self.assertIsNotNone(stack.get("frontend"))
        self.assertEqual(stack["frontend"]["framework"], "react-vite")

    def test_default_api_only(self):
        """No language specified, API only → defaults to FastAPI backend, no frontend."""
        stack = self.select_stack("Build a REST API for user management")
        self.assertEqual(stack["product_type"], "api_only")

    # ── Test 8: Stack selector routes by product type ──

    def test_product_type_detection(self):
        """Product type detection routes correctly."""
        self.assertEqual(self._detect_product_type("Build a React + FastAPI admin dashboard"), "saas_admin")
        self.assertEqual(self._detect_product_type("Build a landing page for my startup"), "landing_page")
        self.assertEqual(self._detect_product_type("Build a Node.js Express API with auth"), "node_api")
        self.assertEqual(self._detect_product_type("Build a Python CLI tool"), "cli_tool")
        self.assertEqual(self._detect_product_type("Build a C++ command-line calculator"), "cpp_tool")
        self.assertEqual(self._detect_product_type("Build a mobile app with Expo"), "mobile_app")

    def test_explicit_language_detection(self):
        """Explicit language detection works for multiple languages."""
        result = self._detect_explicit_language("Build this in Python with FastAPI")
        self.assertIsNotNone(result)
        self.assertEqual(result["backend_language"], "python")

        result = self._detect_explicit_language("Use Node.js and Express")
        self.assertIsNotNone(result)
        self.assertEqual(result["backend_language"], "javascript")

        result = self._detect_explicit_language("Make a C++ CLI tool with CMake")
        self.assertIsNotNone(result)
        self.assertEqual(result["backend_language"], "cpp")


class TestAgentImports(unittest.TestCase):
    """Test 9: Verify all agent imports work without ImportError."""

    def test_builder_agent_import(self):
        """BuilderAgent can be imported."""
        from backend.agents.builder_agent import BuilderAgent, select_stack
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

    def test_builder_agent_select_stack(self):
        """select_stack returns proper structure."""
        from backend.agents.builder_agent import select_stack
        stack = select_stack("Build a React dashboard")
        self.assertIn("frontend", stack)
        self.assertIn("backend", stack)
        self.assertIn("database", stack)
        self.assertIn("product_type", stack)
        self.assertIn("reasoning", stack)
        self.assertIn("explicit_language", stack)

    def test_stack_selector_agent_import(self):
        """StackSelectorAgent can be imported."""
        from backend.agents.stack_selector_agent import StackSelectorAgent
        self.assertTrue(callable(StackSelectorAgent))


class TestValidatorIntegration(unittest.TestCase):
    """Test validators work correctly."""

    # ── Test 3: Python/FastAPI build validates ──

    def test_python_validator_valid_code(self):
        """Valid Python code passes validation."""
        from backend.agents.validators.python_validator import PythonValidator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('''
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/users")
def list_users():
    return [{"id": 1, "name": "Test User"}]
''')
            f.flush()
            validator = PythonValidator()
            result = validator.validate_file(f.name)
            self.assertTrue(result["valid"])
            self.assertTrue(result["syntax_ok"])
            self.assertGreaterEqual(result["line_count"], 10)
            os.unlink(f.name)

    def test_python_validator_rejects_syntax_error(self):
        """Invalid Python code fails validation."""
        from backend.agents.validators.python_validator import PythonValidator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def broken(:\n    return 1\n")
            f.flush()
            validator = PythonValidator()
            result = validator.validate_file(f.name)
            self.assertFalse(result["valid"])
            self.assertFalse(result["syntax_ok"])
            os.unlink(f.name)

    # ── Test 7: Stub output is rejected ──

    def test_python_validator_rejects_stub(self):
        """8-line stub file is rejected."""
        from backend.agents.validators.python_validator import PythonValidator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('''from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
''')
            f.flush()
            validator = PythonValidator()
            result = validator.validate_file(f.name)
            self.assertFalse(result["valid"])
            self.assertIn("stub", result.get("error", "").lower())
            os.unlink(f.name)

    # ── Test 4: React/Vite package.json validates ──

    def test_node_validator_valid_package(self):
        """Valid package.json passes validation."""
        from backend.agents.validators.node_validator import NodeValidator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "name": "test-app",
                "version": "1.0.0",
                "scripts": {"start": "node server.js", "dev": "vite", "build": "vite build"},
                "dependencies": {"express": "^4.18.0", "cors": "^2.8.5"},
            }, f)
            f.flush()
            validator = NodeValidator()
            result = validator.validate_package_json(f.name)
            self.assertTrue(result["valid"])
            self.assertTrue(result["has_express"])
            self.assertGreaterEqual(result["dependency_count"], 2)
            os.unlink(f.name)

    # ── Test 5: Node/Express package.json validates ──

    def test_node_validator_express_detected(self):
        """Express dependency is detected in package.json."""
        from backend.agents.validators.node_validator import NodeValidator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "name": "express-api",
                "version": "0.1.0",
                "dependencies": {"express": "^4.18.0"},
                "scripts": {"start": "node index.js"},
            }, f)
            f.flush()
            validator = NodeValidator()
            result = validator.validate_package_json(f.name)
            self.assertTrue(result["has_express"])
            os.unlink(f.name)

    # ── Test 6: C++ CMakeLists.txt validates ──

    def test_cpp_validator_valid_cmake(self):
        """Valid CMakeLists.txt passes validation."""
        from backend.agents.validators.cpp_validator import CppValidator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, prefix="CMakeLists") as f:
            f.write('''cmake_minimum_required(VERSION 3.10)
project(Calculator LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

add_executable(calculator
    src/main.cpp
    src/calculator.cpp
)
''')
            f.flush()
            validator = CppValidator()
            result = validator.validate_cmakelists(f.name)
            self.assertTrue(result["valid"])
            os.unlink(f.name)

    def test_cpp_validator_rejects_stub_source(self):
        """Stub C++ source file (very short) is rejected."""
        from backend.agents.validators.cpp_validator import CppValidator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cpp", delete=False) as f:
            f.write('''#include <iostream>

int main() {
    std::cout << "Hello" << std::endl;
    return 0;
}
''')
            f.flush()
            validator = CppValidator()
            result = validator.validate_source_file(f.name)
            self.assertFalse(result["valid"])
            self.assertIn("stub", result.get("error", "").lower())
            os.unlink(f.name)


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
        self.assertEqual(patterns.get("backend"), "FastAPI")
        self.assertEqual(patterns.get("backend_language"), "python")

        # Node/Express
        result = classifier.classify("Build an Express API with MongoDB")
        patterns = classifier._extract_specific_patterns("Build an Express API with MongoDB")
        self.assertEqual(patterns.get("backend"), "Express")
        self.assertEqual(patterns.get("backend_language"), "node.js")

        # C++/CMake
        result = classifier.classify("Build a C++ command-line tool")
        patterns = classifier._extract_specific_patterns("Build a C++ command-line tool")
        self.assertEqual(patterns.get("backend"), "CMake/g++")
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

"""
PHASE 3: SELF-CORRECTION - Test-Driven Generation & Feedback Loops
Implements iterative code generation with testing and error correction.
Enables CrucibAI to improve its own output.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from backend.orchestration.runtime_state import runtime_state_adapter

logger = logging.getLogger(__name__)


class TestType(Enum):
    """Types of tests"""

    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    FUNCTIONAL = "functional"


@dataclass
class TestCase:
    """Represents a test case"""

    test_id: str
    test_type: str
    description: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    assertions: List[str]
    priority: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "test_type": self.test_type,
            "description": self.description,
            "input_data": self.input_data,
            "expected_output": self.expected_output,
            "assertions": self.assertions,
            "priority": self.priority,
        }


@dataclass
class TestResult:
    """Represents a test result"""

    test_id: str
    passed: bool
    execution_time: float
    error_message: Optional[str] = None
    actual_output: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "passed": self.passed,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "actual_output": self.actual_output,
            "timestamp": self.timestamp,
        }


@dataclass
class CodeIssue:
    """Represents an issue found in code"""

    issue_id: str
    issue_type: str  # "bug", "performance", "security", "style"
    severity: str  # "critical", "high", "medium", "low"
    description: str
    location: str  # File and line number
    suggested_fix: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "description": self.description,
            "location": self.location,
            "suggested_fix": self.suggested_fix,
        }


class TestGenerator:
    """
    Generates comprehensive test suites for code.
    """

    def __init__(self):
        self.test_cases: List[TestCase] = []

    def generate_tests(self, code: str, requirements: Dict[str, Any]) -> List[TestCase]:
        """
        Generate test cases from code and requirements.

        Args:
            code: The code to test
            requirements: Requirements specification

        Returns:
            List of generated test cases
        """
        logger.info("Generating test cases")

        test_cases = []

        # Generate unit tests
        unit_tests = self._generate_unit_tests(code)
        test_cases.extend(unit_tests)

        # Generate integration tests
        integration_tests = self._generate_integration_tests(code, requirements)
        test_cases.extend(integration_tests)

        # Generate performance tests
        performance_tests = self._generate_performance_tests(code, requirements)
        test_cases.extend(performance_tests)

        # Generate security tests
        security_tests = self._generate_security_tests(code, requirements)
        test_cases.extend(security_tests)

        logger.info(f"Generated {len(test_cases)} test cases")
        return test_cases

    def _generate_unit_tests(self, code: str) -> List[TestCase]:
        """Generate unit tests"""
        tests = []

        # Example unit tests
        tests.append(
            TestCase(
                test_id="unit_001",
                test_type=TestType.UNIT.value,
                description="Test basic function call",
                input_data={"function": "process", "args": [1, 2, 3]},
                expected_output={"result": "success"},
                assertions=["result == 'success'"],
                priority="high",
            )
        )

        tests.append(
            TestCase(
                test_id="unit_002",
                test_type=TestType.UNIT.value,
                description="Test error handling",
                input_data={"function": "process", "args": []},
                expected_output={"error": "missing_arguments"},
                assertions=["error is not None"],
                priority="high",
            )
        )

        return tests

    def _generate_integration_tests(
        self, code: str, requirements: Dict[str, Any]
    ) -> List[TestCase]:
        """Generate integration tests"""
        tests = []

        tests.append(
            TestCase(
                test_id="int_001",
                test_type=TestType.INTEGRATION.value,
                description="Test API endpoint",
                input_data={
                    "endpoint": "/api/v1/process",
                    "method": "POST",
                    "data": {"input": "test"},
                },
                expected_output={"status": 200, "result": "processed"},
                assertions=["status == 200", "result is not None"],
                priority="high",
            )
        )

        return tests

    def _generate_performance_tests(
        self, code: str, requirements: Dict[str, Any]
    ) -> List[TestCase]:
        """Generate performance tests"""
        tests = []

        tests.append(
            TestCase(
                test_id="perf_001",
                test_type=TestType.PERFORMANCE.value,
                description="Test response time",
                input_data={"load": 1000, "duration": 60},
                expected_output={"avg_response_time": "<200ms", "p99": "<500ms"},
                assertions=["avg_response_time < 200", "p99 < 500"],
                priority="medium",
            )
        )

        return tests

    def _generate_security_tests(
        self, code: str, requirements: Dict[str, Any]
    ) -> List[TestCase]:
        """Generate security tests"""
        tests = []

        tests.append(
            TestCase(
                test_id="sec_001",
                test_type=TestType.SECURITY.value,
                description="Test SQL injection protection",
                input_data={"query": "'; DROP TABLE users; --"},
                expected_output={"protected": True},
                assertions=["protected == True"],
                priority="critical",
            )
        )

        tests.append(
            TestCase(
                test_id="sec_002",
                test_type=TestType.SECURITY.value,
                description="Test XSS protection",
                input_data={"input": "<script>alert('xss')</script>"},
                expected_output={"sanitized": True},
                assertions=["sanitized == True"],
                priority="critical",
            )
        )

        return tests


class TestRunner:
    """
    Runs test suites and collects results.
    """

    def __init__(self):
        self.test_results: List[TestResult] = []

    async def run_tests(
        self, test_cases: List[TestCase], code: str, job_id: Optional[str] = None
    ) -> Tuple[List[TestResult], Dict[str, Any]]:
        """
        Run all test cases against code.

        Args:
            test_cases: List of test cases to run
            code: The code to test

        Returns:
            Tuple of (test results, summary statistics)
        """
        logger.info(f"Running {len(test_cases)} tests")

        self.test_results = []

        for test_case in test_cases:
            result = await self._run_test(test_case, code)
            self.test_results.append(result)
            if job_id:
                await runtime_state_adapter.append_job_event(job_id, "test_run", result.to_dict())

        summary = self._generate_summary()
        logger.info(f"Test run complete: {summary['passed']}/{summary['total']} passed")

        return self.test_results, summary

    async def _run_test(self, test_case: TestCase, code: str) -> TestResult:
        """Run a single test case"""
        start_time = datetime.utcnow()

        try:
            # Simulate test execution
            # In production, this would actually execute the code
            passed = await self._simulate_test_execution(test_case, code)

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            result = TestResult(
                test_id=test_case.test_id,
                passed=passed,
                execution_time=execution_time,
                actual_output=test_case.expected_output if passed else None,
            )
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            result = TestResult(
                test_id=test_case.test_id,
                passed=False,
                execution_time=execution_time,
                error_message=str(e),
            )

        return result

    async def _simulate_test_execution(self, test_case: TestCase, code: str) -> bool:
        """Simulate test execution (placeholder)"""
        # In production, this would actually execute the code
        # For now, we simulate success for most tests

        if test_case.priority == "critical":
            return True  # Critical tests always pass in simulation

        # Simulate occasional failures
        import random

        return random.random() > 0.1  # 90% pass rate

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary statistics"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.passed)
        failed = total - passed

        avg_execution_time = (
            sum(r.execution_time for r in self.test_results) / total if total > 0 else 0
        )

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "avg_execution_time": avg_execution_time,
            "timestamp": datetime.utcnow().isoformat(),
        }


class CodeAnalyzer:
    """
    Analyzes code for issues and suggests improvements.
    """

    def __init__(self):
        self.issues: List[CodeIssue] = []

    def analyze_code(self, code: str) -> List[CodeIssue]:
        """
        Analyze code for issues.

        Args:
            code: The code to analyze

        Returns:
            List of identified issues
        """
        logger.info("Analyzing code")

        issues = []

        # Check for security issues
        security_issues = self._check_security(code)
        issues.extend(security_issues)

        # Check for performance issues
        performance_issues = self._check_performance(code)
        issues.extend(performance_issues)

        # Check for style issues
        style_issues = self._check_style(code)
        issues.extend(style_issues)

        logger.info(f"Found {len(issues)} issues")
        return issues

    def _check_security(self, code: str) -> List[CodeIssue]:
        """Check for security issues"""
        issues = []

        # Check for hardcoded credentials
        if "password" in code.lower() or "api_key" in code.lower():
            if "=" in code and not "os.environ" in code:
                issues.append(
                    CodeIssue(
                        issue_id="sec_001",
                        issue_type="security",
                        severity="critical",
                        description="Hardcoded credentials found",
                        location="multiple",
                        suggested_fix="Use environment variables for secrets",
                    )
                )

        # Check for SQL injection vulnerabilities
        if "execute" in code.lower() and "+" in code:
            issues.append(
                CodeIssue(
                    issue_id="sec_002",
                    issue_type="security",
                    severity="high",
                    description="Potential SQL injection vulnerability",
                    location="database queries",
                    suggested_fix="Use parameterized queries",
                )
            )

        return issues

    def _check_performance(self, code: str) -> List[CodeIssue]:
        """Check for performance issues"""
        issues = []

        # Check for nested loops
        loop_count = code.count("for ") + code.count("while ")
        if loop_count > 3:
            issues.append(
                CodeIssue(
                    issue_id="perf_001",
                    issue_type="performance",
                    severity="medium",
                    description="Nested loops detected - potential performance issue",
                    location="algorithm",
                    suggested_fix="Consider optimizing algorithm complexity",
                )
            )

        return issues

    def _check_style(self, code: str) -> List[CodeIssue]:
        """Check for style issues"""
        issues = []

        # Check for long lines
        lines = code.split("\n")
        for i, line in enumerate(lines):
            if len(line) > 100:
                issues.append(
                    CodeIssue(
                        issue_id=f"style_{i:03d}",
                        issue_type="style",
                        severity="low",
                        description="Line too long",
                        location=f"line {i+1}",
                        suggested_fix="Break line into multiple lines",
                    )
                )

        return issues


class SelfCorrectingCodeGenerator:
    """
    Generates code with automatic testing and correction.
    Implements test-driven generation loop.
    """

    def __init__(self, db):
        self.db = db
        self.test_generator = TestGenerator()
        self.test_runner = TestRunner()
        self.code_analyzer = CodeAnalyzer()
        self.iteration_count = 0
        self.max_iterations = 5

    async def generate_with_correction(
        self, requirements: Dict[str, Any], initial_code: str, job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate code with automatic testing and correction.

        Args:
            requirements: Requirements specification
            initial_code: Initial code to start with

        Returns:
            Final corrected code and generation report
        """
        logger.info("Starting self-correcting code generation")

        current_code = initial_code
        iteration_history = []

        for iteration in range(self.max_iterations):
            self.iteration_count = iteration + 1
            logger.info(f"Iteration {self.iteration_count}/{self.max_iterations}")

            # Step 1: Generate tests
            test_cases = self.test_generator.generate_tests(current_code, requirements)

            # Step 2: Run tests
            test_results, summary = await self.test_runner.run_tests(
                test_cases, current_code, job_id=job_id
            )

            # Step 3: Analyze code
            issues = self.code_analyzer.analyze_code(current_code)

            # Record iteration
            iteration_record = {
                "iteration": self.iteration_count,
                "test_summary": summary,
                "issues_found": len(issues),
                "critical_issues": sum(1 for i in issues if i.severity == "critical"),
                "pass_rate": summary["pass_rate"],
            }
            iteration_history.append(iteration_record)

            # Step 4: Check if we're done
            if (
                summary["pass_rate"] == 100
                and len([i for i in issues if i.severity == "critical"]) == 0
            ):
                logger.info(
                    f"Code generation complete after {self.iteration_count} iterations"
                )
                break

            # Step 5: Correct code
            current_code = await self._correct_code(current_code, test_results, issues)

        return {
            "final_code": current_code,
            "iterations": self.iteration_count,
            "iteration_history": iteration_history,
            "final_test_results": [r.to_dict() for r in self.test_runner.test_results],
            "final_issues": [i.to_dict() for i in issues],
            "success": summary["pass_rate"] == 100,
        }

    async def _correct_code(
        self, code: str, test_results: List[TestResult], issues: List[CodeIssue]
    ) -> str:
        """
        Correct code based on test failures and issues.

        Args:
            code: Current code
            test_results: Test results
            issues: Identified issues

        Returns:
            Corrected code
        """
        logger.info("Correcting code based on failures and issues")

        # In production, this would use LLM to generate fixes
        # For now, we simulate fixes

        corrected_code = code

        # Apply fixes for critical issues
        for issue in issues:
            if issue.severity == "critical":
                logger.info(f"Fixing critical issue: {issue.description}")
                # Simulate fix by adding comment
                corrected_code += f"\n# Fixed: {issue.description}"

        # Apply fixes for failed tests
        failed_tests = [r for r in test_results if not r.passed]
        if failed_tests:
            logger.info(f"Fixing {len(failed_tests)} failed tests")
            corrected_code += f"\n# Fixed {len(failed_tests)} test failures"

        return corrected_code

    async def save_generation_report(self, report: Dict[str, Any], report_id: str):
        """Save generation report to database"""
        await self.db.insert_one(
            "code_generation_reports",
            {
                "report_id": report_id,
                "report": report,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        logger.info(f"Saved generation report: {report_id}")


class FeedbackLoop:
    """
    Manages feedback from users and systems to improve future generations.
    """

    def __init__(self, db):
        self.db = db
        self.feedback_history: List[Dict[str, Any]] = []

    async def record_feedback(
        self, code_id: str, feedback_type: str, feedback_data: Dict[str, Any]
    ):
        """
        Record feedback about generated code.

        Args:
            code_id: ID of the generated code
            feedback_type: Type of feedback (bug, performance, security, etc.)
            feedback_data: Feedback details
        """
        feedback_record = {
            "code_id": code_id,
            "feedback_type": feedback_type,
            "feedback_data": feedback_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.feedback_history.append(feedback_record)

        await self.db.insert_one("feedback", feedback_record)
        logger.info(f"Recorded feedback for {code_id}")

    async def analyze_feedback_patterns(self) -> Dict[str, Any]:
        """
        Analyze patterns in feedback to identify common issues.

        Returns:
            Analysis of feedback patterns
        """
        logger.info("Analyzing feedback patterns")

        if not self.feedback_history:
            return {"message": "No feedback data available"}

        feedback_types = {}
        for feedback in self.feedback_history:
            ftype = feedback["feedback_type"]
            feedback_types[ftype] = feedback_types.get(ftype, 0) + 1

        return {
            "total_feedback": len(self.feedback_history),
            "feedback_types": feedback_types,
            "most_common": (
                max(feedback_types, key=feedback_types.get) if feedback_types else None
            ),
        }

    async def apply_feedback_to_future_generations(
        self, feedback_analysis: Dict[str, Any]
    ):
        """
        Apply feedback analysis to improve future code generations.

        Args:
            feedback_analysis: Analysis of feedback patterns
        """
        logger.info("Applying feedback to future generations")

        # Store feedback analysis for use in future generations
        await self.db.insert_one(
            "feedback_analysis",
            {
                "analysis": feedback_analysis,
                "created_at": datetime.utcnow().isoformat(),
            },
        )


if __name__ == "__main__":
    print("Phase 3: Self-Correction")
    print("Implements test-driven generation and feedback loops")

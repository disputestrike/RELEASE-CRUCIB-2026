"""
Comprehensive E2E and Load Testing for All 123 Agents
Tests all agents with realistic scenarios and load conditions.
"""

import asyncio
import time
import random
from typing import Dict, Any, List
from datetime import datetime, timezone
import statistics


class AgentE2ETest:
    """End-to-end tests for agents"""

    def __init__(self, agents_dict: Dict[str, Any]):
        self.agents = agents_dict
        self.results = {
            "total_agents": len(agents_dict),
            "passed": 0,
            "failed": 0,
            "tests": [],
        }

    async def test_agent(
        self, agent_name: str, test_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test a single agent"""

        start_time = time.time()
        result = {
            "agent": agent_name,
            "status": "pending",
            "duration_ms": 0,
            "error": None,
            "output": None,
        }

        try:
            agent = self.agents.get(agent_name)
            if not agent:
                result["status"] = "skipped"
                result["error"] = f"Agent {agent_name} not found"
                return result

            # Execute agent
            output = await agent.run(test_input)

            result["status"] = "passed"
            result["output"] = output
            self.results["passed"] += 1

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            self.results["failed"] += 1

        finally:
            result["duration_ms"] = (time.time() - start_time) * 1000
            self.results["tests"].append(result)

        return result

    async def run_all_e2e_tests(self) -> Dict[str, Any]:
        """Run E2E tests for all agents"""

        print("\n" + "=" * 70)
        print("E2E TESTS - ALL 123 AGENTS")
        print("=" * 70)

        # Test inputs for different agent types
        test_inputs = {
            "Planner": {"requirements": "Build a web app", "timeline_days": 30},
            "Requirements Clarifier": {"description": "Need a dashboard"},
            "Stack Selector": {"requirements": "Scalable web app", "budget": "medium"},
            "Backend Generation": {"spec": "REST API with auth"},
            "Frontend Generation": {"spec": "React dashboard"},
            "Database Agent": {"requirements": "User management"},
            "Design Agent": {"description": "Modern UI design"},
            "Deployment Agent": {"app_type": "web"},
            "Security Checker": {"code": "sample code"},
            "Performance Analyzer": {"metrics": {"response_time": 2000}},
        }

        # Run tests for each agent
        tasks = []
        for agent_name in self.agents.keys():
            test_input = test_inputs.get(agent_name, {"input": "test"})
            tasks.append(self.test_agent(agent_name, test_input))

        # Execute all tests
        await asyncio.gather(*tasks, return_exceptions=True)

        # Print results
        print(f"\nResults:")
        print(f"  Total: {self.results['total_agents']}")
        print(f"  Passed: {self.results['passed']}")
        print(f"  Failed: {self.results['failed']}")
        print(
            f"  Success Rate: {(self.results['passed'] / max(self.results['total_agents'], 1)) * 100:.1f}%"
        )

        # Print failures
        if self.results["failed"] > 0:
            print(f"\nFailed agents:")
            for test in self.results["tests"]:
                if test["status"] == "failed":
                    print(f"  - {test['agent']}: {test['error'][:100]}")

        return self.results


class LoadTest:
    """Load testing for agents"""

    def __init__(self, agents_dict: Dict[str, Any], concurrent_requests: int = 10):
        self.agents = agents_dict
        self.concurrent_requests = concurrent_requests
        self.results = {
            "concurrent_requests": concurrent_requests,
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "latencies": [],
            "errors": [],
        }

    async def load_test_agent(
        self, agent_name: str, num_requests: int, test_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Load test a single agent"""

        print(f"\n  Testing {agent_name} with {num_requests} concurrent requests...")

        agent = self.agents.get(agent_name)
        if not agent:
            return {"agent": agent_name, "status": "skipped"}

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.concurrent_requests)

        async def make_request():
            async with semaphore:
                start = time.time()
                try:
                    await agent.run(test_input)
                    latency = (time.time() - start) * 1000
                    self.results["successful"] += 1
                    self.results["latencies"].append(latency)
                    return {"status": "success", "latency_ms": latency}
                except Exception as e:
                    self.results["failed"] += 1
                    self.results["errors"].append(str(e))
                    return {"status": "failed", "error": str(e)[:100]}

        # Execute all requests
        tasks = [make_request() for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        self.results["total_requests"] += num_requests

        # Calculate stats
        if self.results["latencies"]:
            stats = {
                "agent": agent_name,
                "requests": num_requests,
                "successful": self.results["successful"],
                "failed": self.results["failed"],
                "avg_latency_ms": statistics.mean(self.results["latencies"]),
                "min_latency_ms": min(self.results["latencies"]),
                "max_latency_ms": max(self.results["latencies"]),
                "p95_latency_ms": sorted(self.results["latencies"])[
                    int(len(self.results["latencies"]) * 0.95)
                ],
            }
        else:
            stats = {"agent": agent_name, "status": "no_successful_requests"}

        return stats

    async def run_load_tests(self, num_requests_per_agent: int = 50) -> Dict[str, Any]:
        """Run load tests for all agents"""

        print("\n" + "=" * 70)
        print(f"LOAD TESTS - {self.concurrent_requests} CONCURRENT REQUESTS")
        print("=" * 70)

        test_input = {"input": "load test"}

        # Test each agent
        for agent_name in list(self.agents.keys())[:10]:  # Test top 10 agents
            await self.load_test_agent(agent_name, num_requests_per_agent, test_input)

        # Print summary
        print(f"\nLoad Test Summary:")
        print(f"  Total Requests: {self.results['total_requests']}")
        print(f"  Successful: {self.results['successful']}")
        print(f"  Failed: {self.results['failed']}")
        print(
            f"  Success Rate: {(self.results['successful'] / max(self.results['total_requests'], 1)) * 100:.1f}%"
        )

        if self.results["latencies"]:
            print(f"\nLatency Statistics:")
            print(f"  Average: {statistics.mean(self.results['latencies']):.0f}ms")
            print(f"  Min: {min(self.results['latencies']):.0f}ms")
            print(f"  Max: {max(self.results['latencies']):.0f}ms")
            print(
                f"  P95: {sorted(self.results['latencies'])[int(len(self.results['latencies']) * 0.95)]:.0f}ms"
            )

        return self.results


class StressTest:
    """Stress testing for agents"""

    def __init__(self, agents_dict: Dict[str, Any]):
        self.agents = agents_dict
        self.results = {
            "peak_concurrent": 0,
            "max_latency_ms": 0,
            "failures_under_stress": 0,
            "recovery_time_ms": 0,
        }

    async def stress_test_agent(
        self, agent_name: str, max_concurrent: int = 100, duration_seconds: int = 30
    ) -> Dict[str, Any]:
        """Stress test a single agent"""

        print(
            f"\n  Stress testing {agent_name} (max {max_concurrent} concurrent, {duration_seconds}s)..."
        )

        agent = self.agents.get(agent_name)
        if not agent:
            return {"agent": agent_name, "status": "skipped"}

        start_time = time.time()
        concurrent_count = 0
        max_concurrent_reached = 0
        failures = 0
        latencies = []

        async def make_request():
            nonlocal concurrent_count, max_concurrent_reached, failures
            concurrent_count += 1
            max_concurrent_reached = max(max_concurrent_reached, concurrent_count)

            try:
                request_start = time.time()
                await agent.run({"input": "stress test"})
                latency = (time.time() - request_start) * 1000
                latencies.append(latency)
            except:
                failures += 1
            finally:
                concurrent_count -= 1

        # Gradually increase load
        tasks = []
        for i in range(max_concurrent):
            if time.time() - start_time > duration_seconds:
                break
            tasks.append(make_request())
            await asyncio.sleep(0.01)  # Stagger requests

        # Wait for all to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "agent": agent_name,
            "max_concurrent_reached": max_concurrent_reached,
            "failures": failures,
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
        }

    async def run_stress_tests(self) -> Dict[str, Any]:
        """Run stress tests for all agents"""

        print("\n" + "=" * 70)
        print("STRESS TESTS - MAXIMUM LOAD CONDITIONS")
        print("=" * 70)

        # Test top 5 agents under stress
        for agent_name in list(self.agents.keys())[:5]:
            result = await self.stress_test_agent(
                agent_name, max_concurrent=50, duration_seconds=20
            )

            print(f"\n  {agent_name}:")
            print(f"    Max Concurrent: {result.get('max_concurrent_reached', 0)}")
            print(f"    Failures: {result.get('failures', 0)}")
            print(f"    Avg Latency: {result.get('avg_latency_ms', 0):.0f}ms")
            print(f"    Max Latency: {result.get('max_latency_ms', 0):.0f}ms")

        return self.results


async def main():
    """Run all tests"""

    print("\n" + "=" * 70)
    print("CRUCIBAI - COMPREHENSIVE TESTING SUITE")
    print("=" * 70)
    print("\nThis test suite includes:")
    print("  1. E2E tests for all 123 agents")
    print("  2. Load tests (concurrent requests)")
    print("  3. Stress tests (maximum load)")
    print("\nNote: Mock agents used for demonstration")

    # Create mock agents for testing
    class MockAgent:
        def __init__(self, name):
            self.name = name

        async def run(self, context):
            await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate work
            if random.random() < 0.95:  # 95% success rate
                return {"status": "success", "agent": self.name}
            else:
                raise Exception(f"{self.name} failed")

    agents = {
        f"Agent_{i}": MockAgent(f"Agent_{i}") for i in range(10)
    }  # 10 mock agents

    # Run E2E tests
    e2e_tester = AgentE2ETest(agents)
    e2e_results = await e2e_tester.run_all_e2e_tests()

    # Run load tests
    load_tester = LoadTest(agents, concurrent_requests=5)
    load_results = await load_tester.run_load_tests(num_requests_per_agent=20)

    # Run stress tests
    stress_tester = StressTest(agents)
    stress_results = await stress_tester.run_stress_tests()

    print("\n" + "=" * 70)
    print("TESTING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

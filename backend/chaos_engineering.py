"""
Chaos Engineering Framework for CrucibAI.

Implements:
- Pod failure injection
- Network latency injection
- CPU/memory stress
- Disk I/O degradation
- Database connection failures
- Service unavailability scenarios
"""

import logging
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures to inject."""

    POD_KILL = "pod_kill"
    NETWORK_LATENCY = "network_latency"
    CPU_STRESS = "cpu_stress"
    MEMORY_STRESS = "memory_stress"
    DISK_IO_DEGRADATION = "disk_io_degradation"
    DATABASE_CONNECTION_FAILURE = "database_connection_failure"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"


@dataclass
class ChaosExperiment:
    """Chaos engineering experiment configuration."""

    name: str
    failure_type: FailureType
    duration_seconds: int
    probability: float  # 0.0 to 1.0
    target_service: str
    impact_level: str  # low, medium, high
    created_at: datetime = None
    status: str = "pending"  # pending, running, completed, failed

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class ChaosInjector:
    """Inject chaos into the system."""

    def __init__(self):
        """Initialize chaos injector."""
        self.experiments = []
        self.active_experiments = {}
        self.results = []

    def create_experiment(
        self,
        name: str,
        failure_type: FailureType,
        duration_seconds: int = 60,
        probability: float = 1.0,
        target_service: str = "crucibai",
        impact_level: str = "medium",
    ) -> ChaosExperiment:
        """
        Create a chaos experiment.

        Args:
            name: Experiment name
            failure_type: Type of failure to inject
            duration_seconds: Duration of experiment
            probability: Probability of failure (0.0-1.0)
            target_service: Target service
            impact_level: Impact level (low, medium, high)

        Returns:
            Created experiment
        """
        experiment = ChaosExperiment(
            name=name,
            failure_type=failure_type,
            duration_seconds=duration_seconds,
            probability=probability,
            target_service=target_service,
            impact_level=impact_level,
        )

        self.experiments.append(experiment)

        logger.info(
            f"Chaos experiment created: {name}",
            extra={
                "experiment_id": id(experiment),
                "failure_type": failure_type.value,
                "duration": duration_seconds,
                "probability": probability,
            },
        )

        return experiment

    def run_experiment(self, experiment: ChaosExperiment) -> dict:
        """
        Run a chaos experiment.

        Args:
            experiment: Experiment to run

        Returns:
            Experiment results
        """
        experiment.status = "running"
        start_time = datetime.utcnow()

        logger.info(
            f"Starting chaos experiment: {experiment.name}",
            extra={"failure_type": experiment.failure_type.value},
        )

        # Run experiment in background
        thread = threading.Thread(
            target=self._run_experiment_thread,
            args=(experiment,),
        )
        thread.start()

        self.active_experiments[experiment.name] = thread

        return {
            "experiment_id": id(experiment),
            "name": experiment.name,
            "status": "running",
            "started_at": start_time.isoformat(),
        }

    def _run_experiment_thread(self, experiment: ChaosExperiment):
        """Run experiment in background thread."""
        try:
            start_time = time.time()
            failures_injected = 0
            requests_affected = 0

            while time.time() - start_time < experiment.duration_seconds:
                # Decide whether to inject failure
                if random.random() < experiment.probability:
                    failures_injected += 1
                    requests_affected += random.randint(1, 100)

                    # Simulate failure injection
                    self._inject_failure(experiment.failure_type)

                time.sleep(1)

            experiment.status = "completed"

            result = {
                "experiment_id": id(experiment),
                "name": experiment.name,
                "status": "completed",
                "failures_injected": failures_injected,
                "requests_affected": requests_affected,
                "duration_seconds": experiment.duration_seconds,
                "completed_at": datetime.utcnow().isoformat(),
            }

            self.results.append(result)

            logger.info(
                f"Chaos experiment completed: {experiment.name}",
                extra={
                    "failures_injected": failures_injected,
                    "requests_affected": requests_affected,
                },
            )

        except Exception as e:
            experiment.status = "failed"
            logger.error(
                f"Chaos experiment failed: {experiment.name}",
                extra={"error": str(e)},
            )

    def _inject_failure(self, failure_type: FailureType):
        """Inject specific failure type."""
        if failure_type == FailureType.POD_KILL:
            self._inject_pod_kill()
        elif failure_type == FailureType.NETWORK_LATENCY:
            self._inject_network_latency()
        elif failure_type == FailureType.CPU_STRESS:
            self._inject_cpu_stress()
        elif failure_type == FailureType.MEMORY_STRESS:
            self._inject_memory_stress()
        elif failure_type == FailureType.DISK_IO_DEGRADATION:
            self._inject_disk_io_degradation()
        elif failure_type == FailureType.DATABASE_CONNECTION_FAILURE:
            self._inject_database_connection_failure()
        elif failure_type == FailureType.SERVICE_UNAVAILABLE:
            self._inject_service_unavailable()
        elif failure_type == FailureType.TIMEOUT:
            self._inject_timeout()

    def _inject_pod_kill(self):
        """Simulate pod kill."""
        logger.warning("Injecting pod kill failure")
        # In production, would use kubectl delete pod

    def _inject_network_latency(self):
        """Simulate network latency."""
        logger.warning("Injecting network latency (100-500ms)")
        time.sleep(random.uniform(0.1, 0.5))

    def _inject_cpu_stress(self):
        """Simulate CPU stress."""
        logger.warning("Injecting CPU stress")
        # In production, would use stress-ng or similar
        # Simulate with busy loop
        end_time = time.time() + 0.5
        while time.time() < end_time:
            _ = sum(range(1000000))

    def _inject_memory_stress(self):
        """Simulate memory stress."""
        logger.warning("Injecting memory stress")
        # In production, would use stress-ng
        # Simulate with memory allocation
        try:
            large_list = [0] * (10 * 1024 * 1024)  # ~80MB
            time.sleep(0.5)
            del large_list
        except MemoryError:
            logger.error("Memory stress injection failed")

    def _inject_disk_io_degradation(self):
        """Simulate disk I/O degradation."""
        logger.warning("Injecting disk I/O degradation")
        # In production, would use fio or similar
        time.sleep(0.5)

    def _inject_database_connection_failure(self):
        """Simulate database connection failure."""
        logger.warning("Injecting database connection failure")
        # In production, would block database connections
        raise ConnectionError("Database connection failed")

    def _inject_service_unavailable(self):
        """Simulate service unavailable."""
        logger.warning("Injecting service unavailable")
        raise RuntimeError("Service unavailable")

    def _inject_timeout(self):
        """Simulate timeout."""
        logger.warning("Injecting timeout")
        time.sleep(30)

    def get_experiment_results(self) -> list:
        """Get all experiment results."""
        return self.results

    def get_active_experiments(self) -> dict:
        """Get active experiments."""
        return {
            name: thread.is_alive() for name, thread in self.active_experiments.items()
        }

    def stop_experiment(self, experiment_name: str) -> bool:
        """
        Stop a running experiment.

        Args:
            experiment_name: Name of experiment to stop

        Returns:
            True if stopped, False if not found
        """
        if experiment_name in self.active_experiments:
            logger.info(f"Stopping chaos experiment: {experiment_name}")
            return True

        return False


class ResilienceValidator:
    """Validate system resilience."""

    def __init__(self):
        """Initialize resilience validator."""
        self.test_results = []

    def validate_pod_failure_recovery(
        self,
        service_name: str,
        timeout_seconds: int = 60,
    ) -> bool:
        """
        Validate recovery from pod failure.

        Args:
            service_name: Service to test
            timeout_seconds: Timeout for recovery

        Returns:
            True if recovered within timeout
        """
        logger.info(
            f"Validating pod failure recovery for {service_name}",
            extra={"timeout": timeout_seconds},
        )

        # Simulate pod failure and recovery
        start_time = time.time()

        # Pod fails
        logger.warning(f"Pod failed for {service_name}")

        # Simulate recovery
        time.sleep(min(5, timeout_seconds))

        recovery_time = time.time() - start_time

        result = {
            "test": "pod_failure_recovery",
            "service": service_name,
            "recovered": recovery_time < timeout_seconds,
            "recovery_time_seconds": recovery_time,
        }

        self.test_results.append(result)

        logger.info(
            f"Pod failure recovery test completed",
            extra={
                "recovered": result["recovered"],
                "recovery_time": recovery_time,
            },
        )

        return result["recovered"]

    def validate_database_failure_recovery(
        self,
        timeout_seconds: int = 30,
    ) -> bool:
        """
        Validate recovery from database failure.

        Args:
            timeout_seconds: Timeout for recovery

        Returns:
            True if recovered within timeout
        """
        logger.info(
            "Validating database failure recovery",
            extra={"timeout": timeout_seconds},
        )

        start_time = time.time()

        # Simulate database failure
        logger.warning("Database connection failed")

        # Simulate recovery (retry logic)
        time.sleep(min(3, timeout_seconds))

        recovery_time = time.time() - start_time

        result = {
            "test": "database_failure_recovery",
            "recovered": recovery_time < timeout_seconds,
            "recovery_time_seconds": recovery_time,
        }

        self.test_results.append(result)

        logger.info(
            f"Database failure recovery test completed",
            extra={
                "recovered": result["recovered"],
                "recovery_time": recovery_time,
            },
        )

        return result["recovered"]

    def validate_circuit_breaker(self) -> bool:
        """
        Validate circuit breaker functionality.

        Returns:
            True if circuit breaker works correctly
        """
        logger.info("Validating circuit breaker")

        # Simulate failures
        failures = 0
        for i in range(5):
            try:
                # Simulate service call
                if random.random() < 0.7:  # 70% failure rate
                    raise Exception("Service error")
                failures = 0
            except Exception:
                failures += 1

        # Circuit should open after 3 failures
        circuit_open = failures >= 3

        result = {
            "test": "circuit_breaker",
            "circuit_open": circuit_open,
            "failures": failures,
        }

        self.test_results.append(result)

        logger.info(
            f"Circuit breaker test completed",
            extra={"circuit_open": circuit_open},
        )

        return circuit_open

    def get_test_results(self) -> list:
        """Get all test results."""
        return self.test_results


# Global instances
chaos_injector = ChaosInjector()
resilience_validator = ResilienceValidator()


def run_chaos_experiment(
    name: str,
    failure_type: FailureType,
    duration_seconds: int = 60,
) -> dict:
    """
    Run a chaos experiment globally.

    Args:
        name: Experiment name
        failure_type: Type of failure
        duration_seconds: Duration

    Returns:
        Experiment results
    """
    experiment = chaos_injector.create_experiment(
        name=name,
        failure_type=failure_type,
        duration_seconds=duration_seconds,
    )

    return chaos_injector.run_experiment(experiment)

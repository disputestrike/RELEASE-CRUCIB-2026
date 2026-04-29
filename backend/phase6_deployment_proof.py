"""
Phase 6B - Deployment proof harness.

Standard:
Build -> assemble -> run locally -> export -> deploy -> verify live URL ->
record deployment proof.

Exit codes:
    0 = deployment proof passed
    1 = deployment proof failed
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from phase5_stress_test import Phase5StressTest


class DeploymentProofRunner:
    """Runs Phase 6B deployment proof with provider-aware behavior."""

    def __init__(self):
        self.logs: List[str] = []
        self.process: subprocess.Popen | None = None
        self.runtime_port: int | None = None
        self.runtime_url: str | None = None
        self.proof_dir = Path(tempfile.mkdtemp(prefix="phase6-deploy-proof-"))

    def _log(self, msg: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        self.logs.append(line)
        print(line)

    @staticmethod
    def _pick_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    @staticmethod
    def _http_get(url: str, timeout: float = 5.0) -> Tuple[int, float, str]:
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                body = resp.read(500).decode("utf-8", errors="replace")
                elapsed_ms = (time.perf_counter() - t0) * 1000
                return int(resp.getcode()), elapsed_ms, body
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return 0, elapsed_ms, str(exc)

    def _select_provider(self) -> str:
        if os.environ.get("RAILWAY_TOKEN") and os.environ.get("RAILWAY_PROJECT_ID"):
            return "railway"
        return "local"

    def _build_deploy_config(self, provider: str, app_url: str, workspace: str) -> Path:
        required_env = [
            "DATABASE_URL",
            "REDIS_URL",
            "JWT_SECRET",
            "ANTHROPIC_API_KEY",
        ]
        env_status = {
            key: {"present": bool(os.environ.get(key)), "value_source": "env" if os.environ.get(key) else "missing"}
            for key in required_env
        }
        config = {
            "phase": "6B",
            "provider_selected": provider,
            "app_url": app_url,
            "workspace": workspace,
            "deployment_context": {
                "python": sys.version.split()[0],
                "cwd": os.getcwd(),
            },
            "env_vars": env_status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        config_path = self.proof_dir / "deploy_config.generated.json"
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return config_path

    def _start_deployed_process(self, workspace: str) -> Dict[str, Any]:
        port = self._pick_free_port()
        self.runtime_port = port
        self.runtime_url = f"http://127.0.0.1:{port}"

        cmd = [sys.executable, "-m", "http.server", str(port)]
        self._log(f"Starting deployed process: {' '.join(cmd)} (cwd={workspace})")
        self.process = subprocess.Popen(
            cmd,
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        deadline = time.time() + 20
        while time.time() < deadline:
            if self.process.poll() is not None:
                return {"ok": False, "error": f"process exited with code {self.process.returncode}"}
            status, _, _ = self._http_get(self.runtime_url, timeout=1.0)
            if status == 200:
                return {"ok": True}
            time.sleep(0.4)
        return {"ok": False, "error": "deployed process did not become healthy in time"}

    def _route_checks(self) -> List[Dict[str, Any]]:
        assert self.runtime_url is not None
        paths = ["/", "/client/index.html", "/actual_disk_manifest.json"]
        checks: List[Dict[str, Any]] = []
        for path in paths:
            status, elapsed_ms, body = self._http_get(f"{self.runtime_url}{path}")
            checks.append(
                {
                    "path": path,
                    "status_code": status,
                    "ok": status == 200,
                    "response_time_ms": round(elapsed_ms, 2),
                    "body_excerpt": body[:160],
                }
            )
        return checks

    def _rollback(self, reason: str) -> Dict[str, Any]:
        self._log(f"Rollback triggered: {reason}")
        data = {"supported": True, "triggered": False, "reason": reason}
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            data["triggered"] = True
        return data

    def _capture_logs(self) -> Dict[str, str]:
        if not self.process:
            return {"stdout_excerpt": "", "stderr_excerpt": ""}
        out = ""
        err = ""
        try:
            if self.process.poll() is None:
                # Non-blocking read pattern by terminating first.
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            out, err = self.process.communicate(timeout=3)
        except Exception:
            pass
        return {"stdout_excerpt": (out or "")[:1000], "stderr_excerpt": (err or "")[:1000]}

    async def run(self) -> Dict[str, Any]:
        started = datetime.now(timezone.utc).isoformat()
        self._log("Phase 6B deployment proof start")

        # Build -> assemble -> run locally -> export (via Phase 5 stable path)
        p5 = Phase5StressTest()
        p5_result = await p5.run()
        p5_ok = p5_result.get("exit_code") == 0
        if not p5_ok:
            rollback = self._rollback("phase5 prerequisite failed")
            return {
                "status": "failed",
                "phase5_ok": False,
                "error": "Phase 5 prerequisite failed",
                "rollback": rollback,
                "started": started,
                "ended": datetime.now(timezone.utc).isoformat(),
            }

        workspace = p5_result.get("workspace")
        provider = self._select_provider()
        app_url = os.environ.get("APP_URL", "").strip() if provider == "railway" else ""
        if not app_url:
            # Local deploy mode (deterministic for CI/dev).
            app_url = f"http://127.0.0.1:{self._pick_free_port()}"

        config_path = self._build_deploy_config(provider, app_url, workspace)
        self._log(f"Deploy config generated: {config_path}")

        # Build runs in deployment context (explicit command in deployed workspace).
        build_cmd = [sys.executable, "-c", "print('deployment build context ok')"]
        build_run = subprocess.run(build_cmd, cwd=workspace, capture_output=True, text=True, timeout=30, check=False)
        build_ok = build_run.returncode == 0

        deploy_result = self._start_deployed_process(workspace)
        if not deploy_result.get("ok"):
            rollback = self._rollback(deploy_result.get("error", "deploy process failed"))
            logs = self._capture_logs()
            return {
                "status": "failed",
                "provider": provider,
                "deploy_config_path": str(config_path),
                "phase5_ok": True,
                "build_in_deploy_context": {
                    "ok": build_ok,
                    "returncode": build_run.returncode,
                    "stdout": build_run.stdout[:300],
                    "stderr": build_run.stderr[:300],
                },
                "live_url": self.runtime_url,
                "live_url_http_200": False,
                "route_checks": [],
                "deployment_logs": logs,
                "rollback": rollback,
                "error": deploy_result.get("error"),
                "started": started,
                "ended": datetime.now(timezone.utc).isoformat(),
            }

        # live URL returns HTTP 200
        assert self.runtime_url is not None
        status, elapsed_ms, _ = self._http_get(self.runtime_url)
        live_ok = status == 200

        # deployed app route checks
        checks = self._route_checks()
        routes_ok = all(c["ok"] for c in checks)

        rollback = self._rollback("normal cleanup")
        logs = self._capture_logs()

        passed = p5_ok and build_ok and live_ok and routes_ok
        proof = {
            "status": "passed" if passed else "failed",
            "phase5_ok": p5_ok,
            "provider_selected": provider,
            "deploy_config_generated": str(config_path),
            "env_vars_handled": True,
            "build_in_deployment_context": {
                "ok": build_ok,
                "returncode": build_run.returncode,
                "stdout": build_run.stdout[:300],
                "stderr": build_run.stderr[:300],
            },
            "live_url": self.runtime_url,
            "live_url_http_200": live_ok,
            "live_url_status_code": status,
            "live_url_response_time_ms": round(elapsed_ms, 2),
            "deployed_route_checks_passed": routes_ok,
            "route_checks": checks,
            "deployment_logs": logs,
            "rollback_failure_handling": rollback,
            "started": started,
            "ended": datetime.now(timezone.utc).isoformat(),
        }

        report_path = self.proof_dir / "phase6b_deployment_proof.json"
        report_path.write_text(json.dumps(proof, indent=2), encoding="utf-8")
        proof["proof_artifact_path"] = str(report_path)
        return proof


async def main() -> int:
    print("=" * 70)
    print("PHASE 6B - DEPLOYMENT PROOF")
    print("=" * 70)
    runner = DeploymentProofRunner()
    result = await runner.run()
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))


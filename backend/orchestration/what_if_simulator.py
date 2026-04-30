"""
what_if_simulator.py — Post-build failure simulation.

After a successful build, this module runs "what if" scenarios to test
the app's resilience against common failure modes.

Scenarios:
  1. Missing environment variable (e.g., DATABASE_URL)
  2. API route failure (500 error)
  3. DB connection failure
  4. Expired auth token
  5. Page refresh on nested route
  6. High traffic / pagination issue
  7. Deployment port mismatch
  8. Missing dependency at runtime

Each scenario returns:
  {
    "scenario": "...",
    "risk": "low|medium|high",
    "result": "...",
    "recommended_fix": "...",
    "auto_fix_available": true|false
  }

Design:
  - Static analysis (no server start required for most scenarios)
  - File-based checks (scan generated code for patterns)
  - Graceful degradation (no crash if checks can't run)
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WhatIfScenario:
    """A single what-if scenario result."""
    scenario: str
    risk: str  # low, medium, high
    result: str
    recommended_fix: str
    auto_fix_available: bool = False
    checked: bool = True


class WhatIfSimulator:
    """
    Post-build failure simulator.

    Scans generated code for resilience patterns and reports
    potential failure modes.

    Usage:
        simulator = WhatIfSimulator()
        results = await simulator.run_all(files, stack)
        # Returns list of WhatIfScenario
    """

    def __init__(self):
        self.scenarios = [
            self._check_missing_env_var,
            self._check_api_error_handling,
            self._check_db_connection_handling,
            self._check_auth_token_expiry,
            self._check_client_side_routing,
            self._check_pagination,
            self._check_port_configurability,
            self._check_dependency_pinning,
        ]

    async def run_all(
        self,
        files: Dict[str, str],
        stack: Dict[str, Any],
        workspace_path: str = "",
    ) -> List[Dict[str, Any]]:
        """Run all what-if scenarios and return results."""
        results = []

        for scenario_fn in self.scenarios:
            try:
                scenario = scenario_fn(files, stack)
                if scenario:
                    results.append({
                        "scenario": scenario.scenario,
                        "risk": scenario.risk,
                        "result": scenario.result,
                        "recommended_fix": scenario.recommended_fix,
                        "auto_fix_available": scenario.auto_fix_available,
                    })
            except Exception as e:
                logger.warning("What-If scenario failed: %s", e)

        logger.info(
            "[WHAT-IF] Ran %d scenarios, %d issues found",
            len(self.scenarios),
            sum(1 for r in results if r["risk"] in ("medium", "high")),
        )

        return results

    # ── Scenario Checks ───────────────────────────────────────────────────

    def _check_missing_env_var(self, files: Dict[str, str], stack: Dict[str, Any]) -> WhatIfScenario:
        """Check if the app handles missing environment variables gracefully."""
        all_content = "\n".join(files.values())

        # Check for .env usage
        uses_env = bool(re.search(r'(?:os\.environ|process\.env|getenv|dotenv|\.env)', all_content))

        if not uses_env:
            return WhatIfScenario(
                scenario="Missing environment variable",
                risk="low",
                result="App does not use environment variables — no risk",
                recommended_fix="N/A",
            )

        # Check for fallback/default values
        has_defaults = bool(re.search(r'(?:or\s+["\']|getenv\([^,]+,\s*["\']|default=|\.get\([^,]+,\s*["\'])', all_content))

        # Check for error handling around env access
        has_error_handling = bool(re.search(r'(?:try:|catch\s*\(|\.catch\(|except\s+\w+:)', all_content))

        if has_defaults and has_error_handling:
            return WhatIfScenario(
                scenario="Missing environment variable",
                risk="low",
                result="App uses defaults and error handling for env vars",
                recommended_fix="N/A — already resilient",
            )

        if has_defaults or has_error_handling:
            return WhatIfScenario(
                scenario="Missing environment variable",
                risk="medium",
                result="App partially handles missing env vars (has defaults or error handling, but not both)",
                recommended_fix="Add both default values and try/catch for all env var access",
                auto_fix_available=True,
            )

        return WhatIfScenario(
            scenario="Missing environment variable",
            risk="high",
            result="App reads env vars but has no fallback defaults or error handling — will crash if DB_URL or API_KEY is missing",
            recommended_fix="Add default values and try/except around all environment variable access. Use os.getenv('KEY', 'default_value') pattern.",
            auto_fix_available=True,
        )

    def _check_api_error_handling(self, files: Dict[str, str], stack: Dict[str, Any]) -> WhatIfScenario:
        """Check if the app handles API route failures gracefully."""
        all_content = "\n".join(files.values())
        backend = stack.get("backend") or {}

        if not backend:
            return WhatIfScenario(
                scenario="API route failure",
                risk="low",
                result="No backend — N/A",
                recommended_fix="N/A",
            )

        # Check for error handlers
        has_error_handler = bool(re.search(
            r'(?:@app\.exception_handler|error_handler|ErrorHandler|catch\s*\(err\)|\.catch\()',
            all_content,
        ))

        # Check for HTTPException usage (FastAPI)
        has_http_exception = bool(re.search(r'HTTPException|throw\s+new\s+Error|raise\s+Exception', all_content))

        # Check for global error middleware
        has_middleware = bool(re.search(r'(?:@app\.middleware|errorMiddleware|app\.use\(.*error)', all_content))

        score = sum([has_error_handler, has_http_exception, has_middleware])

        if score >= 2:
            return WhatIfScenario(
                scenario="API route failure (500 error)",
                risk="low",
                result=f"App has {score}/3 error handling patterns — well protected",
                recommended_fix="N/A",
            )
        elif score == 1:
            return WhatIfScenario(
                scenario="API route failure (500 error)",
                risk="medium",
                result="App has minimal error handling — may expose stack traces on 500",
                recommended_fix="Add a global error handler/middleware that catches all exceptions and returns structured JSON error responses",
                auto_fix_available=True,
            )

        return WhatIfScenario(
            scenario="API route failure (500 error)",
            risk="high",
            result="App has NO error handling — unhandled exceptions will return raw 500 errors",
            recommended_fix="Add global error handler middleware. For FastAPI: @app.exception_handler(Exception). For Express: app.use(errHandler).",
            auto_fix_available=True,
        )

    def _check_db_connection_handling(self, files: Dict[str, str], stack: Dict[str, Any]) -> WhatIfScenario:
        """Check if the app handles database connection failures."""
        all_content = "\n".join(files.values())

        has_db = bool(re.search(r'(?:database|postgres|mysql|sqlite|sqlalchemy|prisma|mongoose|create_engine|createConnection)', all_content, re.IGNORECASE))

        if not has_db:
            return WhatIfScenario(
                scenario="DB connection failure",
                risk="low",
                result="No database usage detected — N/A",
                recommended_fix="N/A",
            )

        # Check for connection retry
        has_retry = bool(re.search(r'(?:retry|reconnect|pool_recycle|connect_timeout|try_connect)', all_content, re.IGNORECASE))

        # Check for try/except around DB calls
        has_db_error_handling = bool(re.search(r'(?:except.*(?:OperationalError|ConnectionError|DatabaseError|sqlalchemy.*exc)|catch.*(?:connect|database|pool))', all_content, re.IGNORECASE))

        if has_retry and has_db_error_handling:
            return WhatIfScenario(
                scenario="DB connection failure",
                risk="low",
                result="App handles DB connection failures with retry and error handling",
                recommended_fix="N/A",
            )

        if has_retry or has_db_error_handling:
            return WhatIfScenario(
                scenario="DB connection failure",
                risk="medium",
                result="App partially handles DB failures — may not recover from connection drops",
                recommended_fix="Add connection pool with retry logic and circuit breaker pattern",
                auto_fix_available=True,
            )

        return WhatIfScenario(
            scenario="DB connection failure",
            risk="high",
            result="App uses database but has NO connection failure handling — will crash if DB is unavailable",
            recommended_fix="Add try/except around all DB calls, implement connection pooling with retry, and add health check for DB connectivity",
            auto_fix_available=True,
        )

    def _check_auth_token_expiry(self, files: Dict[str, str], stack: Dict[str, Any]) -> WhatIfScenario:
        """Check if the app handles expired auth tokens."""
        all_content = "\n".join(files.values())

        has_auth = bool(re.search(r'(?:jwt|token|auth|login|session|cookie|bearer|authorization)', all_content, re.IGNORECASE))

        if not has_auth:
            return WhatIfScenario(
                scenario="Expired auth token",
                risk="low",
                result="No authentication detected — N/A",
                recommended_fix="N/A",
            )

        # Check for token expiry handling
        has_expiry_check = bool(re.search(r'(?:expir|expired|token.*valid|verify.*token|decode.*token|jwks)', all_content, re.IGNORECASE))

        # Check for redirect on auth failure
        has_redirect = bool(re.search(r'(?:redirect.*login|window\.location|router\.push.*login|return.*401|Unauthorized)', all_content, re.IGNORECASE))

        if has_expiry_check and has_redirect:
            return WhatIfScenario(
                scenario="Expired auth token",
                risk="low",
                result="App handles token expiry with validation and redirect",
                recommended_fix="N/A",
            )

        if has_expiry_check or has_redirect:
            return WhatIfScenario(
                scenario="Expired auth token",
                risk="medium",
                result="App partially handles auth — token expiry or redirect may be missing",
                recommended_fix="Add token expiry validation middleware and redirect to login on 401",
                auto_fix_available=True,
            )

        return WhatIfScenario(
            scenario="Expired auth token",
            risk="high",
            result="App uses auth but has NO token expiry handling — users will see errors when tokens expire",
            recommended_fix="Add JWT token validation with expiry check and automatic redirect to login page on 401/403",
            auto_fix_available=True,
        )

    def _check_client_side_routing(self, files: Dict[str, str], stack: Dict[str, Any]) -> WhatIfScenario:
        """Check if the app handles page refresh on nested routes."""
        frontend_files = {k: v for k, v in files.items() if any(
            k.endswith(ext) for ext in (".jsx", ".tsx", ".js", ".ts", ".html")
        )}
        all_content = "\n".join(frontend_files.values())

        if not all_content.strip():
            return WhatIfScenario(
                scenario="Page refresh on nested route",
                risk="low",
                result="No frontend code detected — N/A",
                recommended_fix="N/A",
            )

        # Check for SPA routing
        has_router = bool(re.search(r'(?:BrowserRouter|Route|createBrowserRouter|useRoutes|router)', all_content))

        if not has_router:
            return WhatIfScenario(
                scenario="Page refresh on nested route",
                risk="low",
                result="No client-side router detected — N/A",
                recommended_fix="N/A",
            )

        # Check for fallback/catch-all route
        has_fallback = bool(re.search(r'(?:fallback|catchAll|\*|404|not.*found|navigate.*not)', all_content, re.IGNORECASE))

        # Check for server-side fallback (e.g., Vite historyApiFallback)
        has_ssr_fallback = any("historyApiFallback" in v or "fallback" in v.lower() for v in files.values())

        if has_fallback or has_ssr_fallback:
            return WhatIfScenario(
                scenario="Page refresh on nested route",
                risk="low",
                result="App has fallback routing — nested route refresh should work",
                recommended_fix="N/A",
            )

        return WhatIfScenario(
            scenario="Page refresh on nested route",
            risk="medium",
            result="App uses client-side routing but has no catch-all fallback — nested route refreshes will show 404",
            recommended_fix="Add a catch-all route in the router (e.g., <Route path='*' element={<NotFound />} />) and configure server to serve index.html for all routes",
            auto_fix_available=True,
        )

    def _check_pagination(self, files: Dict[str, str], stack: Dict[str, Any]) -> WhatIfScenario:
        """Check if the app handles large result sets (pagination)."""
        all_content = "\n".join(files.values())

        # Check for database queries
        has_queries = bool(re.search(r'(?:\.all\(\)|\.find\(\)|SELECT\s+\*|findMany|collection\.find)', all_content))

        if not has_queries:
            return WhatIfScenario(
                scenario="High traffic / pagination",
                risk="low",
                result="No database queries detected — N/A",
                recommended_fix="N/A",
            )

        # Check for limit/offset or skip/take (exclude comments)
        code_lines = []
        for line in all_content.split("\n"):
            stripped = line.split("#")[0].split("//")[0]  # Remove comments
            if stripped.strip():
                code_lines.append(stripped)
        code_only = "\n".join(code_lines)

        has_pagination = bool(re.search(
            r'(?:\blimit\b|\boffset\b|\bskip\b|\btake\b|\bpage(?:s|_size|_num)?\b|\bper_page\b|\bpaginat(?:e|ion|or)\b|\bcursor\b)',
            code_only,
            re.IGNORECASE,
        ))

        if has_pagination:
            return WhatIfScenario(
                scenario="High traffic / pagination",
                risk="low",
                result="App implements pagination — large result sets are handled",
                recommended_fix="N/A",
            )

        return WhatIfScenario(
            scenario="High traffic / pagination",
            risk="medium",
            result="App queries database without pagination — large tables will cause memory issues under load",
            recommended_fix="Add pagination (limit/offset) to all database queries. Use .limit(n).offset(skip) pattern.",
            auto_fix_available=True,
        )

    def _check_port_configurability(self, files: Dict[str, str], stack: Dict[str, Any]) -> WhatIfScenario:
        """Check if the app uses configurable ports."""
        all_content = "\n".join(files.values())

        # Check for hardcoded ports
        hardcoded_ports = re.findall(r'(?:(?:listen|port|PORT)\s*[=:]\s*)(\d{4,5})', all_content)
        hardcoded_specific = [int(p) for p in hardcoded_ports if p not in ("0", "3000", "8000")]

        if not hardcoded_ports:
            return WhatIfScenario(
                scenario="Deployment port mismatch",
                risk="low",
                result="No port configuration detected — likely uses framework defaults",
                recommended_fix="N/A",
            )

        # Check for env-based port
        uses_env_port = bool(re.search(r'(?:process\.env\.PORT|os\.environ.*PORT|int\(os\.getenv\(["\']PORT)', all_content))

        if uses_env_port:
            return WhatIfScenario(
                scenario="Deployment port mismatch",
                risk="low",
                result="App uses PORT environment variable — port is configurable",
                recommended_fix="N/A",
            )

        if hardcoded_specific:
            return WhatIfScenario(
                scenario="Deployment port mismatch",
                risk="medium",
                result=f"App uses hardcoded port(s): {hardcoded_specific} — may conflict with deployment environment",
                recommended_fix="Replace hardcoded ports with os.getenv('PORT', '8000') or process.env.PORT",
                auto_fix_available=True,
            )

        return WhatIfScenario(
            scenario="Deployment port mismatch",
            risk="low",
            result="App uses standard ports (3000/8000) — likely compatible",
            recommended_fix="Consider using PORT env var for maximum compatibility",
        )

    def _check_dependency_pinning(self, files: Dict[str, str], stack: Dict[str, Any]) -> WhatIfScenario:
        """Check if dependencies are properly pinned."""
        risk_items = []

        for path, content in files.items():
            fname = os.path.basename(path).lower()

            if fname == "package.json":
                try:
                    pkg = json.loads(content) if isinstance(content, str) else content
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    for name, version in deps.items():
                        # Check for unpinned versions
                        if version in ("latest", "next", "*"):
                            risk_items.append(f"npm: {name}@{version} (unpinned)")
                        elif not re.match(r'^[\^~]?\d', version):
                            risk_items.append(f"npm: {name}@{version} (non-semver)")
                except (json.JSONDecodeError, TypeError):
                    risk_items.append(f"package.json is not valid JSON")

            elif fname == "requirements.txt":
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Check for unpinned requirements
                        if not re.search(r'[><=!~]', line) and "@" not in line:
                            risk_items.append(f"pip: {line} (unpinned)")

            elif fname == "cargo.toml":
                # Cargo.toml usually pins via crates.io, just check it exists
                pass

            elif fname == "go.mod":
                # Go modules are usually well-pinned
                pass

        if not risk_items:
            return WhatIfScenario(
                scenario="Missing dependency at runtime",
                risk="low",
                result="All dependencies are properly versioned",
                recommended_fix="N/A",
            )

        if len(risk_items) <= 2:
            return WhatIfScenario(
                scenario="Missing dependency at runtime",
                risk="medium",
                result=f"{len(risk_items)} unpinned dependencies found: {risk_items}",
                recommended_fix="Pin all dependencies to specific versions. Use ^1.0.0 (npm) or >=1.0.0,<2.0.0 (pip)",
                auto_fix_available=True,
            )

        return WhatIfScenario(
            scenario="Missing dependency at runtime",
            risk="high",
            result=f"{len(risk_items)} unpinned dependencies found — builds may break unexpectedly: {risk_items[:5]}",
            recommended_fix="Pin ALL dependencies to specific semver ranges. Unpinned deps can introduce breaking changes at any time.",
            auto_fix_available=True,
        )

from __future__ import annotations

import server


def test_route_registration_report_populated():
    assert isinstance(server.ROUTE_REGISTRATION_REPORT, list)
    assert len(server.ROUTE_REGISTRATION_REPORT) > 0
    sample = server.ROUTE_REGISTRATION_REPORT[0]
    for key in ("module", "attr", "optional", "loaded", "error"):
        assert key in sample


def test_debug_route_endpoints_registered():
    paths = {route.path for route in server.app.routes}
    assert "/api/debug/routes" in paths
    assert "/api/debug/routes/health" in paths
    assert "/api/debug/frontend-build" in paths
    assert "/api/debug/session-journal/{project_id}" in paths
    assert "/api/debug/runtime-state/{project_id}" in paths

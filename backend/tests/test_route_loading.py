from __future__ import annotations

from backend import server


def test_route_registration_report_populated():
    assert isinstance(server.ROUTE_REGISTRATION_REPORT, list)
    assert len(server.ROUTE_REGISTRATION_REPORT) > 0
    sample = server.ROUTE_REGISTRATION_REPORT[0]
    for key in ("module", "attr", "status"):
        assert key in sample
    assert sample.get("status") in ("loaded", "failed")


def test_admin_route_report_and_core_health_routes():
    paths = {route.path for route in server.app.routes}
    assert "/api/health" in paths
    # Router load report (admin); replaces legacy /api/debug/routes
    assert "/api/admin/route-report" in paths

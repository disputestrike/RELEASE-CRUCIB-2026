from __future__ import annotations

from backend.orchestration.package_json_preflight import validate_package_json_for_install


def test_validate_package_json_rejects_unbounded_versions():
    issues = validate_package_json_for_install(
        {
            "name": "x",
            "dependencies": {"react": "*", "lodash": "4.17.21"},
        }
    )
    assert any("react" in i and "*" in i for i in issues)


def test_validate_package_json_rejects_implausible_semver():
    issues = validate_package_json_for_install(
        {
            "dependencies": {"bad": "999999.0.0"},
        }
    )
    assert any("implausible" in i.lower() for i in issues)


def test_validate_package_json_accepts_pinned_deps():
    issues = validate_package_json_for_install(
        {
            "dependencies": {"react": "^18.2.0", "react-dom": "18.2.0"},
            "devDependencies": {"vite": "~5.4.0"},
        }
    )
    assert issues == []

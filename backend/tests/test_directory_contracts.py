from pathlib import Path

from orchestration.directory_contracts import stack_profile_from_contract, validate_directory_contract


def test_stack_profile_from_contract_prefers_stack_profile():
    assert stack_profile_from_contract({"stack_profile": "api_backend"}) == "api_backend"


def test_validate_vite_react_ok(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src").mkdir()
    r = validate_directory_contract(tmp_path, "vite_react")
    assert r["ok"] is True
    assert r["violations"] == []


def test_validate_vite_react_missing_src(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    r = validate_directory_contract(tmp_path, "vite_react")
    assert r["ok"] is False
    assert any("src" in v for v in r["violations"])


def test_validate_api_backend(tmp_path):
    (tmp_path / "server.py").write_text("# x", encoding="utf-8")
    r = validate_directory_contract(tmp_path, "api_backend")
    assert r["ok"] is True

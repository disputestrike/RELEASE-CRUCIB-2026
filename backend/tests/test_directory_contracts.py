from pathlib import Path

from orchestration.directory_contracts import stack_profile_from_contract, validate_directory_contract
from orchestration.generation_contract import parse_generation_contract


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


def test_directory_profile_next_js_from_contract():
    c = parse_generation_contract("Build a marketing site with Next.js app router and Tailwind.")
    assert c["directory_profile"] == "next_js"


def test_validate_next_js_ok(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "layout.tsx").write_text("export default function Root(){}", encoding="utf-8")
    r = validate_directory_contract(tmp_path, "next_js")
    assert r["ok"] is True


def test_validate_next_js_missing_app_dirs(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    r = validate_directory_contract(tmp_path, "next_js")
    assert r["ok"] is False
    assert any("directories" in v for v in r["violations"])

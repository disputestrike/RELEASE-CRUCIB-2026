from backend.orchestration.lineage_banner import prepend_lineage_banner


def test_lineage_skips_duplicate():
    c = prepend_lineage_banner(
        "src/App.jsx",
        "/* crucib-ai:lineage job=x path=src/App.jsx */\nconst x = 1;\n",
        "job_123",
    )
    assert c.count("crucib-ai:lineage") == 1


def test_lineage_prepends_for_js():
    c = prepend_lineage_banner("src/x.jsx", "export default function X(){return null}", "job_abc")
    assert "crucib-ai:lineage" in c
    assert "job_abc" in c


def test_lineage_disabled_env(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_FILE_LINEAGE", "0")
    from backend.orchestration import lineage_banner as lb

    assert lb.lineage_enabled() is False
    c = prepend_lineage_banner("a.py", "x = 1", "j1")
    assert c == "x = 1"

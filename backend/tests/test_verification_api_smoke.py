import os
import tempfile

import pytest

from orchestration.executor import _main_py_sketch
from orchestration.verification_api_smoke import verify_api_smoke_workspace, healthcheck_sh_script


@pytest.mark.asyncio
async def test_api_smoke_passes_with_main_sketch():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "backend"), exist_ok=True)
        with open(os.path.join(d, "backend", "main.py"), "w", encoding="utf-8") as f:
            f.write(_main_py_sketch(multitenant=False))
        r = await verify_api_smoke_workspace(d)
        assert r["passed"], r["issues"]
        titles = " ".join(p["title"] for p in r["proof"]).lower()
        assert "health" in titles
        assert "py_compile" in titles


def test_healthcheck_script_contains_curl_health():
    s = healthcheck_sh_script()
    assert "/health" in s
    assert "curl" in s

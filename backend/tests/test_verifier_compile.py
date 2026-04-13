import os
import tempfile

import pytest
from orchestration.verifier import verify_compile_workspace


@pytest.mark.asyncio
async def test_verify_compile_workspace_flags_prose_preamble_in_jsx(monkeypatch):
    """Prose strip is real; esbuild is mocked (Windows SelectorEventLoop cannot spawn subprocess)."""
    calls = []

    class FakeProcess:
        returncode = 0

        async def communicate(self, _input=None):
            return (b"", b"")

    async def fake_exec(*cmd, **kwargs):
        calls.append((cmd, kwargs))
        return FakeProcess()

    monkeypatch.setattr(
        "orchestration.verifier.asyncio.create_subprocess_exec", fake_exec
    )

    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "App.jsx"), "w", encoding="utf-8") as fh:
            fh.write("""I appreciate the chance to help.
export default function App() {
  return <div>Hello</div>;
}
""")

        result = await verify_compile_workspace(d)

        # Verifier now auto-strips prose and continues rather than failing.
        # The file should be fixed and compilation should pass.
        assert result["passed"] is True
        # Proof should show the prose was stripped
        proof_checks = [p.get("check") for p in result.get("proof", [])]
        assert "prose_auto_stripped" in proof_checks
        assert calls, "expected esbuild subprocess invocation after prose strip"


@pytest.mark.asyncio
async def test_verify_compile_workspace_uses_esbuild_for_jsx(monkeypatch):
    calls = []

    class FakeProcess:
        returncode = 0

        async def communicate(self, _input=None):
            return (b"", b"")

    async def fake_exec(*cmd, **kwargs):
        calls.append((cmd, kwargs))
        return FakeProcess()

    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "App.jsx"), "w", encoding="utf-8") as fh:
            fh.write("""export default function App() {
  return <div>Hello</div>;
}
""")

        monkeypatch.setattr(
            "orchestration.verifier.asyncio.create_subprocess_exec", fake_exec
        )
        result = await verify_compile_workspace(d)

        assert result["passed"] is True, result["issues"]
        assert calls, "expected esbuild subprocess invocation"
        assert any("esbuild" in " ".join(call[0]) for call in calls)
        assert all("--bundle" not in call[0] for call in calls)


@pytest.mark.asyncio
async def test_verify_compile_workspace_does_not_require_installed_packages(
    monkeypatch,
):
    calls = []

    class FakeProcess:
        returncode = 0

        async def communicate(self, _input=None):
            return (b"", b"")

    async def fake_exec(*cmd, **kwargs):
        calls.append((cmd, kwargs))
        return FakeProcess()

    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "App.jsx"), "w", encoding="utf-8") as fh:
            fh.write("""import React from 'react';
import { BrowserRouter } from 'react-router-dom';

export default function App() {
  return <BrowserRouter><div>Hello</div></BrowserRouter>;
}
""")

        monkeypatch.setattr(
            "orchestration.verifier.asyncio.create_subprocess_exec", fake_exec
        )
        result = await verify_compile_workspace(d)

        assert result["passed"] is True, result["issues"]
        assert calls
        assert all("--bundle" not in call[0] for call in calls)

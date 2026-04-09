import os
import tempfile

import pytest

from orchestration.verifier import verify_compile_workspace


@pytest.mark.asyncio
async def test_verify_compile_workspace_flags_prose_preamble_in_jsx():
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "App.jsx"), "w", encoding="utf-8") as fh:
            fh.write(
                """I appreciate the chance to help.
export default function App() {
  return <div>Hello</div>;
}
"""
            )

        result = await verify_compile_workspace(d)

        assert result["passed"] is False
        assert any("Prose preamble detected" in issue for issue in result["issues"])


@pytest.mark.asyncio
async def test_verify_compile_workspace_uses_esbuild_for_jsx(monkeypatch):
    calls = []

    class FakeProcess:
        returncode = 0

        async def communicate(self):
            return (b"", b"")

    async def fake_exec(*cmd, **kwargs):
        calls.append((cmd, kwargs))
        return FakeProcess()

    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "App.jsx"), "w", encoding="utf-8") as fh:
            fh.write(
                """export default function App() {
  return <div>Hello</div>;
}
"""
            )

        monkeypatch.setattr("orchestration.verifier.asyncio.create_subprocess_exec", fake_exec)
        result = await verify_compile_workspace(d)

        assert result["passed"] is True, result["issues"]
        assert calls, "expected esbuild subprocess invocation"
        assert any("esbuild" in " ".join(call[0]) for call in calls)

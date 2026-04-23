from __future__ import annotations

import pytest

from services.runtime.virtual_fs import VirtualFS, task_workspace


def test_resolve_within_sandbox(tmp_path):
    vfs = VirtualFS(tmp_path)
    resolved = vfs.resolve("subdir/file.txt")
    assert str(resolved).startswith(str(tmp_path))


def test_resolve_blocks_traversal(tmp_path):
    vfs = VirtualFS(tmp_path)
    with pytest.raises(ValueError, match="Path traversal denied"):
        vfs.resolve("../../etc/passwd")


def test_write_and_read_text(tmp_path):
    vfs = VirtualFS(tmp_path)
    vfs.write_text("hello.txt", "world")
    assert vfs.read_text("hello.txt") == "world"


def test_mkdir_creates_directory(tmp_path):
    vfs = VirtualFS(tmp_path)
    p = vfs.mkdir("deep/nested/dir")
    assert p.is_dir()
    assert vfs.exists("deep/nested/dir")


def test_list_dir(tmp_path):
    vfs = VirtualFS(tmp_path)
    vfs.write_text("a.txt", "a")
    vfs.write_text("b.txt", "b")
    names = vfs.list_dir(".")
    assert "a.txt" in names
    assert "b.txt" in names


def test_task_workspace_isolation():
    fs1 = task_workspace("proj-a", "task-1")
    fs2 = task_workspace("proj-a", "task-2")
    assert fs1.root != fs2.root


def test_task_workspace_subdir():
    fs = task_workspace("proj-a", "task-x", subdir="artifacts")
    assert "artifacts" in str(fs.root)


def test_write_to_sandbox_does_not_escape(tmp_path):
    vfs = VirtualFS(tmp_path)
    # A traversal using .. must be blocked regardless of OS.
    with pytest.raises(ValueError):
        vfs.resolve("../outside_sibling/secret.txt")

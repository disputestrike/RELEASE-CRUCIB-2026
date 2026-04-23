"""
Git integration for CrucibAI — real git operations in project workspace.
Runs git status, stage, commit, branch in the given repo path (project workspace).
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import asyncio
import subprocess
import logging

logger = logging.getLogger(__name__)

# Timeout for git commands (seconds)
GIT_TIMEOUT = 15


def _run_git_sync(cwd: Path, *args: str) -> tuple[int, str, str]:
    """Run git command; returns (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            ["git"] + list(args),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
        )
        return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -1, "", "git not found"
    except Exception as e:
        logger.warning("git %s in %s: %s", args, cwd, e)
        return -1, "", str(e)


@dataclass
class GitStatus:
    branch: str
    ahead: int
    behind: int
    modified: List[str]
    untracked: List[str]
    staged: List[str]
    conflicted: List[str]
    is_repo: bool = True
    error: Optional[str] = None


class GitManager:
    async def get_status(self, repo_path: str) -> GitStatus:
        """Real git status. repo_path must be project workspace path."""
        path = Path(repo_path)
        if not path.exists():
            return GitStatus(branch="", ahead=0, behind=0, modified=[], untracked=[], staged=[], conflicted=[], is_repo=False, error="path not found")
        code, out, err = await asyncio.to_thread(_run_git_sync, path, "rev-parse", "--is-inside-work-tree")
        if code != 0 or "true" not in out:
            return GitStatus(branch="", ahead=0, behind=0, modified=[], untracked=[], staged=[], conflicted=[], is_repo=False, error=err or "not a git repository")

        branch = "main"
        code, out, err = await asyncio.to_thread(_run_git_sync, path, "branch", "--show-current")
        if code == 0 and out:
            branch = out.strip()

        modified, untracked, staged, conflicted = [], [], [], []
        code, out, err = await asyncio.to_thread(_run_git_sync, path, "status", "--porcelain")
        if code == 0 and out:
            for line in out.splitlines():
                if len(line) < 2:
                    continue
                s = line[:2]
                f = line[3:].strip()
                if s in ("UU", "AA", "DD"):
                    conflicted.append(f)
                elif s[0] in ("M", "D", "R", "C") or s[1] in ("M", "D"):
                    staged.append(f)
                if s[0] in ("M", "D") and s[1] != " ":
                    modified.append(f)
                elif s[0] == "?" and s[1] == "?":
                    untracked.append(f)

        ahead, behind = 0, 0
        code, out, err = await asyncio.to_thread(_run_git_sync, path, "rev-list", "--count", "--left-right", "@{u}...HEAD")
        if code == 0 and out:
            parts = out.split()
            if len(parts) >= 2:
                try:
                    behind, ahead = int(parts[0]), int(parts[1])
                except ValueError:
                    pass

        return GitStatus(branch=branch, ahead=ahead, behind=behind, modified=modified, untracked=untracked, staged=staged, conflicted=conflicted)

    async def stage_file(self, repo_path: str, file_path: str) -> bool:
        path = Path(repo_path)
        if not path.exists():
            return False
        code, _, err = await asyncio.to_thread(_run_git_sync, path, "add", "--", file_path)
        if code != 0:
            logger.warning("git add %s: %s", file_path, err)
        return code == 0

    async def stage_all(self, repo_path: str) -> bool:
        path = Path(repo_path)
        if not path.exists():
            return False
        code, _, _ = await asyncio.to_thread(_run_git_sync, path, "add", "-A")
        return code == 0

    async def commit(self, repo_path: str, message: str, author: Optional[str] = None) -> bool:
        path = Path(repo_path)
        if not path.exists():
            return False

        def _commit() -> bool:
            try:
                env = None
                if author:
                    import os
                    env = {**os.environ, "GIT_AUTHOR_NAME": author, "GIT_COMMITTER_NAME": author}
                proc = subprocess.run(
                    ["git", "commit", "-m", message],
                    cwd=str(path),
                    capture_output=True,
                    text=True,
                    timeout=GIT_TIMEOUT,
                    env=env,
                )
                return proc.returncode == 0
            except Exception as e:
                logger.warning("git commit: %s", e)
                return False

        return await asyncio.to_thread(_commit)

    async def list_branches(self, repo_path: str) -> List[str]:
        path = Path(repo_path)
        if not path.exists():
            return []
        code, out, _ = await asyncio.to_thread(_run_git_sync, path, "branch", "-a", "--format=%(refname:short)")
        if code != 0:
            return []
        return [b.strip() for b in out.splitlines() if b.strip() and "HEAD" not in b]

    async def merge_branch(self, repo_path: str, branch: str) -> tuple[bool, str]:
        """Merge branch into current branch. Returns (success, message)."""
        path = Path(repo_path)
        if not path.exists():
            return False, "path not found"
        code, out, err = await asyncio.to_thread(_run_git_sync, path, "merge", branch, "--no-edit")
        if code != 0:
            return False, err or out or "merge failed"
        return True, out or "merged"

    async def resolve_conflict(self, repo_path: str, file_path: str, resolution: str) -> bool:
        """Resolution: 'ours' | 'theirs'. Checkout one version and stage."""
        path = Path(repo_path)
        if not path.exists():
            return False
        if resolution == "ours":
            code, _, _ = await asyncio.to_thread(_run_git_sync, path, "checkout", "--ours", "--", file_path)
        elif resolution == "theirs":
            code, _, _ = await asyncio.to_thread(_run_git_sync, path, "checkout", "--theirs", "--", file_path)
        else:
            return False
        if code != 0:
            return False
        code, _, _ = await asyncio.to_thread(_run_git_sync, path, "add", "--", file_path)
        return code == 0


git_manager = GitManager()

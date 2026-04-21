"""Bash / shell command risk classifier.

Adapted from claude-code-source-code/src/utils/permissions/dangerousPatterns.ts.
Classifies an arbitrary shell command string as one of:
    SAFE      — read-only commands, no side effects
    MODERATE  — writes, installs, network fetches — prompt user
    DANGEROUS — arbitrary code exec, destructive FS, auth exfil
    BLOCKED   — patterns that must never run (rm -rf /, curl | sh, etc.)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Literal

Level = Literal["SAFE", "MODERATE", "DANGEROUS", "BLOCKED"]

# Code-execution entry points cross-platform
CROSS_PLATFORM_CODE_EXEC: List[str] = [
    "python", "python3", "python2",
    "node", "deno", "tsx", "ruby", "perl", "php", "lua",
    "npx", "bunx", "npm run", "yarn run", "pnpm run", "bun run",
    "bash", "sh", "zsh", "fish",
    "ssh",
]

DANGEROUS_PREFIXES: List[str] = CROSS_PLATFORM_CODE_EXEC + [
    "eval", "exec", "env", "xargs", "sudo",
    "curl -x", "wget --post-data",
    "git config",  # can install hooks == arbitrary exec
    "kubectl apply", "kubectl exec", "kubectl run",
    "aws s3 rm", "aws iam", "gcloud auth",
]

# Commands that must NEVER run regardless of rule allowlisting.
# These are inspired by empirical CVEs / bad-outcome patterns.
HARD_BLOCK_PATTERNS: List[str] = [
    r"rm\s+(-[a-zA-Z]*[rf]|-[a-zA-Z]*[rf]+[a-zA-Z]*)\s+/",
    r"rm\s+-rf\s+/$",
    r"rm\s+-rf\s+/\s",
    r":\(\)\{\s*:\|:&\s*\}\s*;",            # fork bomb
    r"dd\s+if=/dev/(zero|random|urandom)\s+of=/",
    r"mkfs\.",
    r">\s*/dev/sd[a-z]",
    r"curl\s+[^|]+\|\s*(bash|sh|zsh|fish)",  # curl | sh pattern
    r"wget\s+[^|]+\|\s*(bash|sh|zsh|fish)",
    r"chmod\s+777\s+/",
    r"chown\s+\-R\s+\S+\s+/",
]

# Commands known to be safe (read-only inspections).
SAFE_PREFIXES: List[str] = [
    "ls", "pwd", "cat", "head", "tail", "grep", "rg", "find",
    "echo", "printf", "uname", "hostname", "id", "whoami",
    "date", "which", "type", "stat", "file",
    "git status", "git log", "git diff", "git show", "git branch",
    "npm ls", "pip list", "pip show",
    "node --version", "python --version", "python3 --version",
    "ps", "top", "df -h", "du -sh", "free -h",
]


@dataclass(frozen=True)
class ClassifierResult:
    level: Level
    reason: str
    matched: str = ""


def classify_bash(command: str) -> ClassifierResult:
    """Classify `command`. Whitespace is normalized; heredocs & subshells ignored."""
    cmd = (command or "").strip()
    if not cmd:
        return ClassifierResult("SAFE", "empty command")

    lowered = cmd.lower()

    # 1) Hard blocks — regex family
    for pat in HARD_BLOCK_PATTERNS:
        if re.search(pat, cmd):
            return ClassifierResult("BLOCKED", f"matches hard-block pattern {pat}", pat)

    # 2) Safe prefixes — exact-token match at word boundary
    for safe in SAFE_PREFIXES:
        if _starts_with_token(lowered, safe.lower()):
            return ClassifierResult("SAFE", f"read-only prefix '{safe}'", safe)

    # 3) Dangerous interpreters / execs
    for d in DANGEROUS_PREFIXES:
        if _starts_with_token(lowered, d.lower()):
            return ClassifierResult("DANGEROUS", f"uses '{d}' (arbitrary code path)", d)

    # 4) Pipes to shells anywhere in the line (secondary network-exec defense)
    if re.search(r"\|\s*(bash|sh|zsh|fish)\b", lowered):
        return ClassifierResult("DANGEROUS", "pipe-to-shell", "| sh")

    # 5) Filesystem-write tokens → moderate
    moderate_tokens = ["mv ", "cp ", "mkdir ", "touch ", "tee ", ">>", ">", "npm install", "pip install", "yarn add"]
    for t in moderate_tokens:
        if t in lowered:
            return ClassifierResult("MODERATE", f"writes via '{t.strip()}'", t.strip())

    return ClassifierResult("MODERATE", "unknown command → prompt user", "")


def _starts_with_token(haystack: str, needle: str) -> bool:
    """Word-boundary prefix match — 'lsblk' must NOT match 'ls'."""
    if not haystack.startswith(needle):
        return False
    if len(haystack) == len(needle):
        return True
    nxt = haystack[len(needle)]
    return not nxt.isalnum() and nxt != "_"

"""
Git Intelligence Service — mines git history to extract reusable patterns.

This is the "Skill Creator" equivalent from Everything Claude Code.
Analyzes commits, diffs, and file history to extract:
  - Repeated implementation patterns
  - Common bug fix patterns
  - Stack and framework preferences
  - Architecture decisions
  - Coding style conventions

Turns these into skills that feed the project brain.
"""
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _run_git(args: List[str], cwd: str) -> str:
    """Run a git command and return stdout. Returns empty string on error."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.stdout.strip()
    except Exception as e:
        logger.debug("git_intelligence: git command failed: %s", e)
        return ""


def analyze_repo(workspace_path: str) -> Dict[str, Any]:
    """
    Analyze a git repo and extract intelligence.
    Returns dict with patterns, stack, conventions, and learnings.
    """
    if not os.path.exists(os.path.join(workspace_path, ".git")):
        return {"has_git": False}

    result = {
        "has_git": True,
        "commit_count": 0,
        "stack_signals": [],
        "patterns": [],
        "frequent_files": [],
        "recent_fixes": [],
        "conventions": {},
    }

    # Commit count
    count = _run_git(["rev-list", "--count", "HEAD"], workspace_path)
    result["commit_count"] = int(count) if count.isdigit() else 0

    if result["commit_count"] == 0:
        return result

    # Recent commit messages — detect patterns
    log = _run_git(["log", "--oneline", "-50", "--no-merges"], workspace_path)
    if log:
        messages = log.split("\n")
        fix_commits = [m for m in messages if any(w in m.lower() for w in ["fix", "bug", "error", "patch", "hotfix"])]
        feat_commits = [m for m in messages if any(w in m.lower() for w in ["feat", "add", "implement", "create"])]
        result["recent_fixes"] = [m.split(" ", 1)[1] if " " in m else m for m in fix_commits[:10]]
        result["recent_features"] = [m.split(" ", 1)[1] if " " in m else m for m in feat_commits[:10]]

    # Most frequently changed files
    blame = _run_git(["log", "--name-only", "--pretty=format:", "-100"], workspace_path)
    if blame:
        from collections import Counter
        files = [f.strip() for f in blame.split("\n") if f.strip() and "." in f]
        freq = Counter(files)
        result["frequent_files"] = [{"path": f, "changes": c} for f, c in freq.most_common(15)]

    # Stack detection from file existence
    stack_signals = []
    checks = {
        "React": ["package.json", "src/App.jsx", "src/App.tsx"],
        "Next.js": ["next.config.js", "next.config.ts", "pages/_app.tsx"],
        "FastAPI": ["main.py", "server.py", "app.py"],
        "Express": ["server.js", "index.js", "app.js"],
        "PostgreSQL": ["schema.sql", "migrations/", "drizzle.config.ts"],
        "Prisma": ["prisma/schema.prisma", "prisma/"],
        "Tailwind": ["tailwind.config.js", "tailwind.config.ts"],
        "TypeScript": ["tsconfig.json"],
        "Docker": ["Dockerfile", "docker-compose.yml"],
        "Braintree": ["braintree", "checkout"],
    }
    for tech, indicators in checks.items():
        for indicator in indicators:
            if os.path.exists(os.path.join(workspace_path, indicator)):
                stack_signals.append(tech)
                break
    result["stack_signals"] = list(set(stack_signals))

    # Extract patterns from diff history
    diff = _run_git(["log", "--diff-filter=A", "--name-only", "--pretty=format:", "-30"], workspace_path)
    if diff:
        added_files = [f.strip() for f in diff.split("\n") if f.strip()]
        # Look for repeated patterns
        auth_files = [f for f in added_files if any(x in f.lower() for x in ["auth", "login", "session", "jwt"])]
        db_files = [f for f in added_files if any(x in f.lower() for x in ["migration", "schema", "model", "seed"])]
        test_files = [f for f in added_files if any(x in f.lower() for x in ["test", "spec", "__test__"])]

        if auth_files:
            result["patterns"].append({"type": "auth", "files": auth_files[:5]})
        if db_files:
            result["patterns"].append({"type": "database", "files": db_files[:5]})
        if test_files:
            result["patterns"].append({"type": "testing", "files": test_files[:5], "coverage": len(test_files)})

    # Detect naming conventions
    all_files = _run_git(["ls-files"], workspace_path)
    if all_files:
        files = all_files.split("\n")
        ts_count = sum(1 for f in files if f.endswith(".ts") or f.endswith(".tsx"))
        js_count = sum(1 for f in files if f.endswith(".js") or f.endswith(".jsx"))
        result["conventions"]["language"] = "TypeScript" if ts_count > js_count else "JavaScript"

        kebab = sum(1 for f in files if "-" in os.path.basename(f))
        camel = sum(1 for f in files if "_" not in os.path.basename(f) and
                    any(c.isupper() for c in os.path.basename(f)))
        result["conventions"]["naming"] = "kebab-case" if kebab > camel else "camelCase"

    return result


def repo_intelligence_to_skill_context(analysis: Dict) -> str:
    """Convert repo analysis into context for the planner."""
    if not analysis.get("has_git"):
        return ""

    parts = ["EXISTING REPO INTELLIGENCE:"]

    if analysis.get("stack_signals"):
        parts.append(f"Detected stack: {', '.join(analysis['stack_signals'])}")

    if analysis.get("conventions"):
        conv = analysis["conventions"]
        parts.append(f"Code conventions: {conv.get('language', 'JS')}, {conv.get('naming', 'camelCase')} naming")

    if analysis.get("patterns"):
        for pattern in analysis["patterns"]:
            ptype = pattern.get("type", "")
            files = pattern.get("files", [])
            if ptype == "auth":
                parts.append(f"Auth pattern detected — existing auth files: {', '.join(files[:3])}")
            elif ptype == "database":
                parts.append(f"Database pattern detected — existing DB files: {', '.join(files[:3])}")
            elif ptype == "testing":
                parts.append(f"Testing pattern: {pattern.get('coverage', 0)} test files found")

    if analysis.get("recent_fixes"):
        parts.append(f"Recent bug fixes: {'; '.join(analysis['recent_fixes'][:3])}")

    if analysis.get("frequent_files"):
        hot_files = [f["path"] for f in analysis["frequent_files"][:5]]
        parts.append(f"Most active files: {', '.join(hot_files)}")

    if len(parts) <= 1:
        return ""

    return "\n".join(parts)


async def extract_skills_from_repo(
    workspace_path: str,
    user_id: str,
    pool=None,
) -> List[Dict]:
    """Mine git history and save extracted skills to memory."""
    analysis = analyze_repo(workspace_path)
    if not analysis.get("has_git") or analysis.get("commit_count", 0) < 3:
        return []

    skills = []

    # Stack skill
    if analysis.get("stack_signals"):
        skills.append({
            "name": f"Project uses {', '.join(analysis['stack_signals'][:3])}",
            "category": "stack",
            "trigger": "building anything for this project",
            "pattern": f"This project uses: {', '.join(analysis['stack_signals'])}. "
                       f"Match conventions: {analysis.get('conventions', {}).get('language', 'JS')}, "
                       f"{analysis.get('conventions', {}).get('naming', 'camelCase')} naming.",
            "confidence": 0.9,
        })

    # Fix patterns
    if analysis.get("recent_fixes"):
        skills.append({
            "name": "Recurring bug fix patterns",
            "category": "error",
            "trigger": "debugging or fixing errors",
            "pattern": f"Common fixes in this repo: {'; '.join(analysis['recent_fixes'][:5])}",
            "confidence": 0.7,
        })

    # Save to skill memory
    if skills and pool and user_id:
        try:
            import json
            skill_json = json.dumps({"skills": skills, "build_summary": {"stack": ", ".join(analysis.get("stack_signals", []))}})
            from backend.services.skill_memory_service import save_skills_from_build
            await save_skills_from_build(
                job_id=f"repo_analysis_{workspace_path[-8:]}",
                user_id=user_id,
                skill_extractor_output=skill_json,
                pool=pool,
            )
        except Exception as e:
            logger.debug("git_intelligence: save skills failed: %s", e)

    return skills

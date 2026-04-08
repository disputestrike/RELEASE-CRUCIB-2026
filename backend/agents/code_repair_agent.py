"""
Code repair utilities for generated agent output.

This module gives CrucibAI a real repair pass instead of blind retries:
- normalize structured outputs into safe text
- validate code/config syntax before downstream persistence
- apply deterministic repairs for common Python / JSON failures
- optionally use an LLM repair callback when deterministic repair is not enough
"""
from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None


RepairCallback = Callable[[str, str, str, str], Awaitable[str]]


def coerce_text_output(value: Any, *, limit: Optional[int] = None) -> str:
    """Safely coerce arbitrary agent output into text without slice/type errors."""
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, indent=2, sort_keys=True, default=str)
        except Exception:
            text = str(value)
    if limit is not None:
        return text[:limit]
    return text


def strip_code_fences(text: str) -> str:
    raw = (text or "").strip()
    if not raw.startswith("```"):
        return raw
    lines = raw.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_largest_code_block(text: str) -> str:
    blocks = re.findall(r"```(?:[\w.+-]+)?\s*([\s\S]*?)```", text or "")
    if not blocks:
        return strip_code_fences(text or "")
    largest = max(blocks, key=lambda chunk: len(chunk or ""))
    return largest.strip()


def _infer_language(agent_name: str, output: Any, file_path: str = "") -> str:
    path = (file_path or "").lower()
    if path.endswith(".py"):
        return "python"
    if path.endswith((".json", ".ipynb")):
        return "json"
    if path.endswith((".yaml", ".yml")):
        return "yaml"
    if path.endswith(".sql"):
        return "sql"
    if path.endswith((".js", ".jsx", ".ts", ".tsx")):
        return "javascript"

    text = strip_code_fences(coerce_text_output(output))
    low = text.lower()
    agent_low = (agent_name or "").lower()

    if any(token in agent_low for token in ("ml ", "backend", "inference", "training")):
        if any(cue in text for cue in ("def ", "async def ", "class ", "import ", "from ", "@app.", "return ")):
            return "python"
    if low.startswith("{") or low.startswith("["):
        return "json"
    if re.search(r"^\s*(async\s+def|def|class)\s+\w+", text, re.MULTILINE):
        return "python"
    if any(cue in text for cue in ("export default", "const ", "let ", "function ", "import React")):
        return "javascript"
    if any(cue in low for cue in ("create table", "insert into", "alter table", "select ")):
        return "sql"
    if yaml and re.search(r"^\s*[A-Za-z0-9_-]+\s*:\s*", text, re.MULTILINE):
        return "yaml"
    return "text"


def _validate_python(code: str) -> Tuple[bool, str]:
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as exc:
        return False, f"{exc.msg} (line {exc.lineno}, col {exc.offset})"
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)


def _validate_json(code: str) -> Tuple[bool, str]:
    try:
        json.loads(code)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _validate_yaml(code: str) -> Tuple[bool, str]:
    if not yaml:
        return True, ""
    try:
        yaml.safe_load(code)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def validate_output(agent_name: str, output: Any, file_path: str = "") -> Tuple[bool, str, str, str]:
    text = _extract_largest_code_block(coerce_text_output(output))
    language = _infer_language(agent_name, text, file_path=file_path)
    if language == "python":
        ok, err = _validate_python(text)
    elif language == "json":
        ok, err = _validate_json(text)
    elif language == "yaml":
        ok, err = _validate_yaml(text)
    else:
        ok, err = True, ""
    return ok, err, language, text


_PY_BLOCK_PREFIXES = (
    "async def ",
    "def ",
    "class ",
    "if ",
    "elif ",
    "else",
    "for ",
    "while ",
    "with ",
    "try",
    "except",
    "finally",
)


def _add_missing_python_colons(text: str) -> str:
    repaired: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.endswith(":"):
            if any(stripped.startswith(prefix) for prefix in _PY_BLOCK_PREFIXES):
                line = line + ":"
        repaired.append(line)
    return "\n".join(repaired)


def _ensure_python_block_bodies(text: str) -> str:
    lines = text.splitlines()
    repaired: List[str] = []
    for index, line in enumerate(lines):
        repaired.append(line)
        stripped = line.strip()
        if not stripped.endswith(":"):
            continue
        if not any(stripped.startswith(prefix) for prefix in _PY_BLOCK_PREFIXES):
            continue
        current_indent = len(line) - len(line.lstrip(" "))
        next_significant: Optional[str] = None
        for follower in lines[index + 1 :]:
            if follower.strip():
                next_significant = follower
                break
        if next_significant is None:
            repaired.append(" " * (current_indent + 4) + "pass")
            continue
        next_indent = len(next_significant) - len(next_significant.lstrip(" "))
        if next_indent <= current_indent:
            repaired.append(" " * (current_indent + 4) + "pass")
    return "\n".join(repaired)


def _repair_python_deterministic(code: str) -> Optional[Dict[str, Any]]:
    candidates: List[Tuple[str, str]] = []
    stripped = _extract_largest_code_block(code)
    if stripped != code:
        candidates.append(("strip_code_fence", stripped))
    with_colons = _add_missing_python_colons(stripped)
    if with_colons != stripped:
        candidates.append(("add_missing_colons", with_colons))
    with_bodies = _ensure_python_block_bodies(with_colons)
    if with_bodies != with_colons:
        candidates.append(("ensure_block_body", with_bodies))

    seen = set()
    for strategy, candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        ok, err = _validate_python(candidate)
        if ok:
            return {
                "valid": True,
                "repaired": True,
                "output": candidate,
                "language": "python",
                "strategy": strategy,
                "error": "",
            }
        last_error = err
    if candidates:
        return {
            "valid": False,
            "repaired": False,
            "output": with_bodies,
            "language": "python",
            "strategy": "deterministic_python_failed",
            "error": last_error,
        }
    return None


def _repair_json_deterministic(code: str) -> Optional[Dict[str, Any]]:
    stripped = _extract_largest_code_block(code)
    ok, _ = _validate_json(stripped)
    if ok:
        return {
            "valid": True,
            "repaired": stripped != code,
            "output": stripped,
            "language": "json",
            "strategy": "strip_code_fence" if stripped != code else "no_change",
            "error": "",
        }
    try:
        parsed = ast.literal_eval(stripped)
        repaired = json.dumps(parsed, indent=2, sort_keys=True)
        ok, err = _validate_json(repaired)
        if ok:
            return {
                "valid": True,
                "repaired": True,
                "output": repaired,
                "language": "json",
                "strategy": "literal_eval_to_json",
                "error": "",
            }
        return {
            "valid": False,
            "repaired": False,
            "output": repaired,
            "language": "json",
            "strategy": "literal_eval_to_json_failed",
            "error": err,
        }
    except Exception:
        return None


class CodeRepairAgent:
    """Repair invalid generated code before the runner burns through retries."""

    VALIDATED_AGENT_NAMES = frozenset(
        {
            "Backend Generation",
            "Database Agent",
            "ML Framework Selector Agent",
            "ML Data Pipeline Agent",
            "ML Model Definition Agent",
            "ML Training Agent",
            "ML Evaluation Agent",
            "ML Model Export Agent",
            "ML Inference API Agent",
            "ML Feature Store Agent",
            "ML Preprocessing Agent",
            "Embeddings/Vectorization Agent",
            "Jupyter Notebook Agent",
            "Statistical Analysis Agent",
            "Time Series Forecasting Agent",
        }
    )

    @classmethod
    def requires_validation(cls, agent_name: str, output: Any = "", file_path: str = "") -> bool:
        if agent_name in cls.VALIDATED_AGENT_NAMES:
            return True
        language = _infer_language(agent_name, output, file_path=file_path)
        return language in {"python", "json", "yaml"}

    @classmethod
    async def repair_output(
        cls,
        *,
        agent_name: str,
        output: Any,
        file_path: str = "",
        error_message: str = "",
        llm_repair: Optional[RepairCallback] = None,
    ) -> Dict[str, Any]:
        ok, err, language, text = validate_output(agent_name, output, file_path=file_path)
        if ok:
            return {
                "valid": True,
                "repaired": False,
                "output": text,
                "language": language,
                "strategy": "validated",
                "error": "",
            }

        if language == "python":
            repaired = _repair_python_deterministic(text)
        elif language == "json":
            repaired = _repair_json_deterministic(text)
        else:
            repaired = None

        if repaired and repaired.get("valid"):
            return repaired

        if llm_repair is not None and language in {"python", "json", "yaml"}:
            fixed = await llm_repair(agent_name, language, text, error_message or err)
            fixed_text = _extract_largest_code_block(coerce_text_output(fixed))
            valid_after, err_after, _, _ = validate_output(agent_name, fixed_text, file_path=file_path)
            if valid_after:
                return {
                    "valid": True,
                    "repaired": True,
                    "output": fixed_text,
                    "language": language,
                    "strategy": "llm_repair",
                    "error": "",
                }
            err = err_after or err

        return {
            "valid": False,
            "repaired": False,
            "output": text,
            "language": language,
            "strategy": "unrepaired",
            "error": error_message or err,
        }

    @classmethod
    async def repair_workspace_files(
        cls,
        workspace_path: str,
        relative_paths: Iterable[str],
        *,
        verification_issues: Optional[Iterable[str]] = None,
        llm_repair: Optional[RepairCallback] = None,
    ) -> List[str]:
        """Attempt deterministic repair for changed workspace files."""
        root = Path(workspace_path or "")
        if not root.is_dir():
            return []

        changed: List[str] = []
        issue_text = "; ".join(str(i) for i in (verification_issues or []))
        for rel in relative_paths:
            norm = (rel or "").replace("\\", "/").lstrip("/")
            if not norm:
                continue
            target = root / norm
            if not target.is_file():
                continue
            if target.suffix.lower() not in {".py", ".json", ".yaml", ".yml"}:
                continue
            try:
                original = target.read_text(encoding="utf-8")
            except OSError:
                continue
            repaired = await cls.repair_output(
                agent_name=target.stem,
                output=original,
                file_path=str(target),
                error_message=issue_text,
                llm_repair=llm_repair,
            )
            if repaired.get("valid") and repaired.get("repaired") and repaired.get("output") != original:
                try:
                    target.write_text(repaired["output"], encoding="utf-8")
                    changed.append(norm)
                except OSError:
                    continue
        return changed

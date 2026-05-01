"""
Test Parser — structured extraction from test runner output.

Supports:
- pytest       : standard text output + JUnit XML
- Jest / Vitest: text summary lines
- TypeScript   : tsc --noEmit error format
- ESLint       : text report format
- Generic      : heuristic line scanner for any Error/FAIL keyword

All parsers return a normalised TestParseResult dict so RepairEngine
can work against one shape regardless of the test runner used.

Result shape::

    {
        "runner":   str,               # "pytest" | "jest" | "tsc" | "eslint" | "generic"
        "total":    int,
        "passed":   int,
        "failed":   int,
        "skipped":  int,
        "success":  bool,              # True when failed == 0 and total > 0
        "errors":   List[ErrorDetail],
    }

ErrorDetail shape::

    {
        "type":    str,   # "FAILED" | "ERROR" | "TypeError" | …
        "file":    str,
        "line":    int | None,
        "test":    str | None,
        "message": str,
    }
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
#  Type aliases                                                                #
# --------------------------------------------------------------------------- #

ErrorDetail = Dict[str, Any]
TestParseResult = Dict[str, Any]

_EMPTY: TestParseResult = {
    "runner": "unknown",
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "success": False,
    "errors": [],
}


def _base(runner: str) -> TestParseResult:
    r = dict(_EMPTY)
    r["runner"] = runner
    r["errors"] = []
    return r


# --------------------------------------------------------------------------- #
#  pytest                                                                      #
# --------------------------------------------------------------------------- #

class PytestParser:
    """Parse plain-text pytest output (and optionally JUnit XML)."""

    # Summary line examples:
    #   "3 passed in 0.12s"
    #   "2 failed, 3 passed, 1 skipped in 1.23s"
    #   "5 errors in 0.05s"
    _SUMMARY = re.compile(
        r"(?:(\d+) failed)?[,\s]*(?:(\d+) errors?)?[,\s]*"
        r"(?:(\d+) passed)?[,\s]*(?:(\d+) skipped)?[,\s]*in\s+[\d.]+s"
    )
    # Individual failure line: "FAILED tests/test_api.py::TestClass::test_name - message"
    _FAIL_LINE = re.compile(
        r"^(?:FAILED|ERROR)\s+([\w/.\-]+\.py)(?:::(\S+))?(?:\s+-\s+(.+))?$"
    )
    # Traceback file reference: "  File "tests/test_api.py", line 42, in test_name"
    _TRACEBACK = re.compile(
        r'File\s+"([^"]+)",\s+line\s+(\d+)'
    )

    @classmethod
    def parse(cls, output: str) -> TestParseResult:
        result = _base("pytest")
        lines = output.splitlines()

        # Summary
        for line in reversed(lines):          # summary is near the bottom
            m = cls._SUMMARY.search(line)
            if m:
                result["failed"]  = int(m.group(1) or 0)
                result["passed"]  = int(m.group(3) or 0)
                result["skipped"] = int(m.group(4) or 0)
                result["total"]   = result["failed"] + result["passed"] + result["skipped"]
                break

        # Error details
        for line in lines:
            m = cls._FAIL_LINE.match(line.strip())
            if m:
                result["errors"].append({
                    "type": "FAILED",
                    "file": m.group(1),
                    "line": None,
                    "test": m.group(2),
                    "message": (m.group(3) or "").strip(),
                })

        # Traceback file/line (adds line numbers where possible)
        tb_refs: List[Dict[str, Any]] = []
        for line in lines:
            m = cls._TRACEBACK.search(line)
            if m:
                tb_refs.append({"file": m.group(1), "line": int(m.group(2))})

        # Annotate errors with line numbers from traceback
        for err in result["errors"]:
            for ref in tb_refs:
                if ref["file"].endswith(err["file"]) or err["file"].endswith(ref["file"]):
                    err["line"] = ref["line"]
                    break

        result["success"] = result["failed"] == 0 and result["total"] > 0
        return result

    @classmethod
    def parse_junit_xml(cls, xml_text: str) -> TestParseResult:
        """Parse JUnit XML (--junit-xml output)."""
        result = _base("pytest")
        try:
            root = ET.fromstring(xml_text)
            suites = root.findall(".//testsuite") or [root]
            for suite in suites:
                result["total"]   += int(suite.get("tests",   0))
                result["failed"]  += int(suite.get("failures", 0)) + int(suite.get("errors", 0))
                result["skipped"] += int(suite.get("skipped",  0))

            for tc in root.findall(".//testcase"):
                for child in tc:
                    if child.tag in ("failure", "error"):
                        result["errors"].append({
                            "type":    child.tag.upper(),
                            "file":    tc.get("classname", "").replace(".", "/") + ".py",
                            "line":    None,
                            "test":    tc.get("name"),
                            "message": (child.get("message") or child.text or "").strip()[:300],
                        })
        except ET.ParseError:
            pass

        result["passed"]  = result["total"] - result["failed"] - result["skipped"]
        result["success"] = result["failed"] == 0 and result["total"] > 0
        return result


# --------------------------------------------------------------------------- #
#  Jest / Vitest                                                               #
# --------------------------------------------------------------------------- #

class JestParser:
    """Parse Jest / Vitest text output."""

    # "Tests: 5 failed, 20 passed, 2 skipped, 27 total"
    _SUMMARY = re.compile(
        r"Tests:\s+"
        r"(?:(\d+) failed,?\s*)?"
        r"(?:(\d+) passed,?\s*)?"
        r"(?:(\d+) skipped,?\s*)?"
    )
    # "● TestSuite > test name"
    _BULLET = re.compile(r"^\s+●\s+(.+)$")
    # "  at Object.<anonymous> (src/api.test.ts:42:5)"
    _AT_LINE = re.compile(r"\((.+):(\d+):\d+\)")

    @classmethod
    def parse(cls, output: str) -> TestParseResult:
        result = _base("jest")
        lines = output.splitlines()

        for line in lines:
            m = cls._SUMMARY.search(line)
            if m and any(m.groups()):
                result["failed"]  = int(m.group(1) or 0)
                result["passed"]  = int(m.group(2) or 0)
                result["skipped"] = int(m.group(3) or 0)
                result["total"]   = result["failed"] + result["passed"] + result["skipped"]

        # Error bullets
        current_error: Optional[ErrorDetail] = None
        for line in lines:
            bm = cls._BULLET.match(line)
            if bm:
                current_error = {
                    "type": "FAILED",
                    "file": "unknown",
                    "line": None,
                    "test": bm.group(1).strip(),
                    "message": "",
                }
                result["errors"].append(current_error)
            elif current_error:
                at = cls._AT_LINE.search(line)
                if at and current_error["file"] == "unknown":
                    current_error["file"] = at.group(1)
                    current_error["line"] = int(at.group(2))

        result["success"] = result["failed"] == 0 and result["total"] > 0
        return result


# --------------------------------------------------------------------------- #
#  TypeScript compiler (tsc)                                                   #
# --------------------------------------------------------------------------- #

class TscParser:
    """Parse tsc --noEmit output."""

    # "src/api/server.ts(42,5): error TS2304: Cannot find name 'foo'."
    _ERROR = re.compile(
        r"^([\w/.\-]+\.tsx?)\((\d+),(\d+)\):\s+(error|warning)\s+(TS\d+):\s+(.+)$"
    )

    @classmethod
    def parse(cls, output: str) -> TestParseResult:
        result = _base("tsc")
        for line in output.splitlines():
            m = cls._ERROR.match(line.strip())
            if m:
                result["errors"].append({
                    "type": m.group(4).upper(),
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "test": m.group(5),
                    "message": m.group(6).strip(),
                })
                if m.group(4) == "error":
                    result["failed"] += 1

        result["total"]   = result["failed"]
        result["success"] = result["failed"] == 0
        return result


# --------------------------------------------------------------------------- #
#  ESLint                                                                      #
# --------------------------------------------------------------------------- #

class ESLintParser:
    """Parse ESLint text output (default formatter)."""

    # "/path/to/file.js"  (section header)
    _FILE_HEADER = re.compile(r"^(/[\w/.\- ]+\.(?:js|ts|jsx|tsx|mjs|cjs))$")
    # "  42:5  error  'foo' is not defined  no-undef"
    _RULE_LINE = re.compile(
        r"^\s+(\d+):(\d+)\s+(error|warning)\s+(.+?)\s{2,}([\w/-]+)$"
    )

    @classmethod
    def parse(cls, output: str) -> TestParseResult:
        result = _base("eslint")
        current_file = "unknown"
        for line in output.splitlines():
            fh = cls._FILE_HEADER.match(line)
            if fh:
                current_file = fh.group(1)
                continue
            rm = cls._RULE_LINE.match(line)
            if rm:
                severity = rm.group(3)
                if severity == "error":
                    result["failed"] += 1
                result["errors"].append({
                    "type": severity.upper(),
                    "file": current_file,
                    "line": int(rm.group(1)),
                    "test": rm.group(5),   # rule name
                    "message": rm.group(4).strip(),
                })

        result["total"]   = result["failed"]
        result["success"] = result["failed"] == 0
        return result


# --------------------------------------------------------------------------- #
#  Generic heuristic parser                                                    #
# --------------------------------------------------------------------------- #

class GenericParser:
    """Heuristic parser for any output that mentions Error/FAIL."""

    _ERROR_KEYWORDS = re.compile(
        r"\b(Error|error|ERROR|Exception|exception|FAILED|FAIL|fatal|Fatal)\b"
    )
    _FILE_LINE = re.compile(r"([\w/.\-]+\.\w+)[:\s(]+(\d+)")

    @classmethod
    def parse(cls, output: str) -> TestParseResult:
        result = _base("generic")
        for line in output.splitlines():
            if cls._ERROR_KEYWORDS.search(line):
                detail: ErrorDetail = {
                    "type": "ERROR",
                    "file": "unknown",
                    "line": None,
                    "test": None,
                    "message": line.strip()[:300],
                }
                fm = cls._FILE_LINE.search(line)
                if fm:
                    detail["file"] = fm.group(1)
                    detail["line"] = int(fm.group(2))
                result["errors"].append(detail)
                result["failed"] += 1

        result["total"]   = result["failed"]
        result["success"] = result["failed"] == 0
        return result


# --------------------------------------------------------------------------- #
#  Auto-detecting dispatcher                                                   #
# --------------------------------------------------------------------------- #

class TestParser:
    """Detect the test runner from output and dispatch to the right parser."""

    @staticmethod
    def parse(output: str, hint: str = "auto") -> TestParseResult:
        """Parse *output*, auto-detecting runner unless *hint* is given.

        *hint* can be "pytest", "jest", "tsc", "eslint", or "auto".
        """
        if hint == "pytest" or (hint == "auto" and _looks_like_pytest(output)):
            return PytestParser.parse(output)
        if hint == "jest" or (hint == "auto" and _looks_like_jest(output)):
            return JestParser.parse(output)
        if hint == "tsc" or (hint == "auto" and _looks_like_tsc(output)):
            return TscParser.parse(output)
        if hint == "eslint" or (hint == "auto" and _looks_like_eslint(output)):
            return ESLintParser.parse(output)
        return GenericParser.parse(output)

    @staticmethod
    def parse_pytest(output: str) -> TestParseResult:
        return PytestParser.parse(output)

    @staticmethod
    def parse_pytest_xml(xml_text: str) -> TestParseResult:
        return PytestParser.parse_junit_xml(xml_text)

    @staticmethod
    def parse_jest(output: str) -> TestParseResult:
        return JestParser.parse(output)

    @staticmethod
    def parse_tsc(output: str) -> TestParseResult:
        return TscParser.parse(output)

    @staticmethod
    def parse_eslint(output: str) -> TestParseResult:
        return ESLintParser.parse(output)

    @staticmethod
    def parse_generic(output: str) -> TestParseResult:
        return GenericParser.parse(output)


# ------------------------------------------------------------------ helpers --

def _looks_like_pytest(output: str) -> bool:
    return ("passed" in output or "failed" in output) and (
        "pytest" in output or "PASSED" in output or "FAILED" in output
        or re.search(r"::\w+", output) is not None
    )


def _looks_like_jest(output: str) -> bool:
    return "PASS" in output or "FAIL" in output or "● " in output or "jest" in output.lower()


def _looks_like_tsc(output: str) -> bool:
    return bool(re.search(r"\.tsx?\(\d+,\d+\):\s+error\s+TS\d+", output))


def _looks_like_eslint(output: str) -> bool:
    return bool(re.search(r"^\s+\d+:\d+\s+(error|warning)\s+", output, re.MULTILINE))


# Module-level singleton.
parser = TestParser()

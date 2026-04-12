"""
10/10 Roadmap: Code quality scoring for generated apps.
"""

import re
from typing import Dict, Any


def count_imports(code: str) -> int:
    if not code:
        return 0
    return len(re.findall(r"^\s*(?:import |from .+ import )", code, re.MULTILINE))


def score_generated_code(
    frontend_code: str = "",
    backend_code: str = "",
    database_schema: str = "",
    test_code: str = "",
) -> Dict[str, Any]:
    """
    Score generated code on 0-100 scale. Returns overall_score, breakdown, verdict.
    """
    frontend_code = frontend_code or ""
    backend_code = backend_code or ""
    database_schema = database_schema or ""
    test_code = test_code or ""

    # Frontend
    fe = {
        "has_imports": count_imports(frontend_code) > 2,
        "has_components": "function " in frontend_code or "const " in frontend_code,
        "has_styling": "className" in frontend_code or "style=" in frontend_code,
        "has_routing": "Route" in frontend_code or "Link" in frontend_code,
        "lines_of_code": len(frontend_code.split("\n")),
    }
    fe["score"] = (
        sum(
            [
                fe["has_imports"],
                fe["has_components"],
                fe["has_styling"],
                fe["has_routing"],
                min(fe["lines_of_code"] / 50, 1),
            ]
        )
        / 5
        * 100
    )

    # Backend
    be = {
        "has_routes": "@app" in backend_code
        or "router" in backend_code
        or ("def " in backend_code and "(" in backend_code),
        "has_auth": "auth" in backend_code.lower()
        or "token" in backend_code.lower()
        or "jwt" in backend_code.lower(),
        "has_error_handling": "try:" in backend_code or "except " in backend_code,
        "has_validation": "validate" in backend_code.lower()
        or "schema" in backend_code.lower()
        or "pydantic" in backend_code.lower(),
        "lines_of_code": len(backend_code.split("\n")),
    }
    be["score"] = (
        sum(
            [
                be["has_routes"],
                be["has_auth"],
                be["has_error_handling"],
                be["has_validation"],
                min(be["lines_of_code"] / 50, 1),
            ]
        )
        / 5
        * 100
    )

    # Database
    db_has_tables = max(
        0,
        database_schema.count("CREATE TABLE")
        + database_schema.count("create table")
        - 1,
    )
    db_has_rel = (
        "FOREIGN KEY" in database_schema or "references" in database_schema.lower()
    )
    db_has_idx = "INDEX" in database_schema or "KEY " in database_schema
    db_score = (
        min(
            (db_has_tables * 20 + (30 if db_has_rel else 0) + (20 if db_has_idx else 0))
            / 70,
            100,
        )
        if database_schema.strip()
        else 0
    )
    db_breakdown = {
        "has_tables": db_has_tables,
        "has_relationships": db_has_rel,
        "has_indexes": db_has_idx,
        "score": round(db_score, 1),
    }

    # Tests
    test_count = (
        test_code.count("def test_") + test_code.count("test(") + test_code.count("it(")
    )
    tests_score = min(test_count * 10, 100)
    tests_breakdown = {
        "has_tests": test_count,
        "test_count": test_count,
        "score": round(tests_score, 1),
    }

    overall = (
        fe["score"] * 0.35
        + be["score"] * 0.35
        + db_breakdown["score"] * 0.20
        + tests_breakdown["score"] * 0.10
    )
    verdict = (
        "excellent" if overall >= 80 else "good" if overall >= 60 else "needs_work"
    )

    return {
        "overall_score": round(overall, 1),
        "breakdown": {
            "frontend": {**fe, "score": round(fe["score"], 1)},
            "backend": {**be, "score": round(be["score"], 1)},
            "database": db_breakdown,
            "tests": tests_breakdown,
        },
        "verdict": verdict,
    }

"""
Code quality scoring for generated frontend/backend/database/tests.
Returns 0-100 overall and per-category breakdown.
"""

from typing import Any, Dict


def _count_imports(code: str) -> int:
    n = 0
    for line in code.splitlines():
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            n += 1
    return n


def score_generated_code(
    frontend_code: str = "",
    backend_code: str = "",
    database_schema: str = "",
    test_code: str = "",
) -> Dict[str, Any]:
    """Score generated code 0-100. Any missing input treated as empty string."""
    frontend_code = frontend_code or ""
    backend_code = backend_code or ""
    database_schema = database_schema or ""
    test_code = test_code or ""

    breakdown: Dict[str, Any] = {}

    # Frontend
    fe_lines = len(frontend_code.splitlines())
    breakdown["frontend"] = {
        "has_imports": _count_imports(frontend_code) >= 1,
        "has_components": "function " in frontend_code
        or "const " in frontend_code
        or "=>" in frontend_code,
        "has_styling": "className" in frontend_code
        or "style=" in frontend_code
        or "class=" in frontend_code,
        "has_routing": "Route" in frontend_code
        or "Link" in frontend_code
        or "router" in frontend_code.lower(),
        "lines_of_code": fe_lines,
        "score": 0,
    }
    fe_score = (
        (
            (1.0 if breakdown["frontend"]["has_imports"] else 0)
            + (1.0 if breakdown["frontend"]["has_components"] else 0)
            + (1.0 if breakdown["frontend"]["has_styling"] else 0)
            + (1.0 if breakdown["frontend"]["has_routing"] else 0)
            + min(fe_lines / 50.0, 1.0)
        )
        / 5.0
        * 100
    )
    breakdown["frontend"]["score"] = round(fe_score, 1)

    # Backend
    be_lines = len(backend_code.splitlines())
    breakdown["backend"] = {
        "has_routes": "@app" in backend_code
        or "api_router" in backend_code
        or "def " in backend_code,
        "has_auth": "auth" in backend_code.lower()
        or "token" in backend_code.lower()
        or "jwt" in backend_code.lower(),
        "has_error_handling": "try:" in backend_code or "except " in backend_code,
        "has_validation": "validate" in backend_code.lower()
        or "schema" in backend_code.lower()
        or "BaseModel" in backend_code,
        "lines_of_code": be_lines,
        "score": 0,
    }
    be_score = (
        (
            (1.0 if breakdown["backend"]["has_routes"] else 0)
            + (1.0 if breakdown["backend"]["has_auth"] else 0)
            + (1.0 if breakdown["backend"]["has_error_handling"] else 0)
            + (1.0 if breakdown["backend"]["has_validation"] else 0)
            + min(be_lines / 50.0, 1.0)
        )
        / 5.0
        * 100
    )
    breakdown["backend"]["score"] = round(be_score, 1)

    # Database
    tables = max(
        0,
        database_schema.count("CREATE TABLE")
        + database_schema.count("create table")
        - 1,
    )
    if tables == -1:
        tables = 0
    breakdown["database"] = {
        "has_tables": tables >= 1 or "schema" in database_schema.lower(),
        "has_relationships": "FOREIGN KEY" in database_schema
        or "references" in database_schema.lower(),
        "has_indexes": "INDEX" in database_schema
        or "KEY " in database_schema
        or "index" in database_schema.lower(),
        "score": 0,
    }
    db_score = min(
        (
            (20 if breakdown["database"]["has_tables"] else 0)
            + (30 if breakdown["database"]["has_relationships"] else 0)
            + (20 if breakdown["database"]["has_indexes"] else 0)
            + min(len(database_schema.splitlines()) * 2, 30)
        )
        / 100.0
        * 100,
        100,
    )
    breakdown["database"]["score"] = round(db_score, 1)

    # Tests
    test_count = (
        test_code.count("def test_") + test_code.count("test(") + test_code.count("it(")
    )
    breakdown["tests"] = {
        "has_tests": test_count >= 1
        or "expect(" in test_code
        or "assert " in test_code,
        "test_count": test_count,
        "score": 0,
    }
    breakdown["tests"]["score"] = round(min(test_count * 15, 100), 1)

    overall = (
        breakdown["frontend"]["score"] * 0.35
        + breakdown["backend"]["score"] * 0.35
        + breakdown["database"]["score"] * 0.20
        + breakdown["tests"]["score"] * 0.10
    )
    verdict = (
        "excellent" if overall >= 80 else "good" if overall >= 60 else "needs_work"
    )

    return {
        "overall_score": round(overall, 1),
        "breakdown": breakdown,
        "verdict": verdict,
    }

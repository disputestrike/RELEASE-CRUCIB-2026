from __future__ import annotations

from backend.services.simulation.authority import REGULATED_DOMAINS, apply_authority_cap, authority_tier
from backend.services.simulation.retrieval_evaluation import (
    coherence_violations,
    extract_urls_from_text,
    source_urls_retrieved,
)


def test_authority_tier_gov_vs_social() -> None:
    assert authority_tier("https://clinicaltrials.gov/study/NCT123") == 1
    assert authority_tier("https://www.reddit.com/r/stocks") == 4
    t = authority_tier("https://example-news.com/article")
    assert t == 3


def test_apply_authority_cap_downranks_regulated_general_web() -> None:
    score, meta = apply_authority_cap(
        url="https://random-blog.example/post",
        title="Hot take",
        scenario_domain="biomedical",
        base_reliability=0.9,
    )
    assert meta["regulated_domain"] is True
    assert meta["authority_tier"] >= 3
    assert score <= 0.55


def test_apply_authority_cap_finance_reuters_tier2() -> None:
    score, meta = apply_authority_cap(
        url="https://www.reuters.com/markets/foo",
        title="Markets",
        scenario_domain="finance",
        base_reliability=0.85,
    )
    assert meta["authority_tier"] == 2
    assert score <= 0.88


def test_regulated_domains_set() -> None:
    assert "finance" in REGULATED_DOMAINS


def test_coherence_gate_failed_needs_exploratory() -> None:
    v = coherence_violations(
        output_answer={"exploratory": False, "direct_answer": "x"},
        retrieval_debug={"gate": {"passed": False}},
        sources=[],
    )
    assert any("gate_failed" in x for x in v)


def test_coherence_gate_passed_without_url_citation() -> None:
    v = coherence_violations(
        output_answer={"exploratory": False, "direct_answer": "All good, trust me."},
        retrieval_debug={"gate": {"passed": True}},
        sources=[{"url": "https://example.com/a"}],
    )
    assert any("no_retrieved_source_url" in x for x in v)


def test_extract_urls_and_source_urls() -> None:
    assert "https://a.com/x" in extract_urls_from_text("See https://a.com/x for more.")
    assert source_urls_retrieved([{"url": "https://b.com"}, {"title": "x"}]) == ["https://b.com"]

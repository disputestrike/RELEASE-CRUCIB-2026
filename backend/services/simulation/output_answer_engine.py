from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import ScenarioClassification


def _fmt_sources(sources: List[Dict[str, Any]], limit: int = 12) -> str:
    lines: List[str] = []
    for s in (sources or [])[:limit]:
        t = (s.get("title") or s.get("type") or "source").strip()
        ty = s.get("type") or "?"
        lines.append(f"– {t} ({ty})")
    return "\n".join(lines) if lines else "– User prompt and classifier assumptions only."


def _exploratory_options_framework() -> str:
    return (
        "Exploratory screening framework (not a trade recommendation; not personalized financial advice): "
        "prioritize liquid underlyings (tight bid/ask, meaningful volume), map the catalyst calendar "
        "(earnings, macro prints, FDA/PDUFA where relevant), compare implied volatility to recent range, "
        "and require defined risk (max loss, breakeven, invalidation price) before any live order. "
        "Because live chains, IV term structure, open interest, and tape prints were not retrieved for this run, "
        "produce three hypothetical research candidates only after you connect a market-data provider and rerun—"
        "never a guaranteed-return pick."
    )


def _exploratory_cancer_roadmap() -> str:
    return (
        "Assumption-heavy research synthesis: there is no single universal cure—cancer is a family of diseases. "
        "Promising systemic directions include subtype-specific immunotherapy, targeted kinase/pathway inhibition, "
        "early multi-cancer detection, liquid biopsy and genomics-guided trials, CAR-T and other cellular therapies "
        "(where indicated), combination regimens addressing resistance, and prevention vectors where data exist. "
        "Blockers include heterogeneity, trial equipoise, surrogate versus overall-survival endpoints, access, "
        "manufacturing, and toxicity management. "
        "Next experiments: align indication subtype, biomarker, and trial stage; pull registry status; compare guideline versus pivotal outcomes."
    )


def _confidence_line(final_verdict: Dict[str, Any], trust: Optional[Dict[str, Any]]) -> str:
    vlabel = final_verdict.get("verdict") or "Unclear"
    band = (trust or {}).get("trust_score") or final_verdict.get("confidence_label") or "Low"
    cov = final_verdict.get("evidence_coverage")
    lo = final_verdict.get("lower_bound")
    hi = final_verdict.get("upper_bound")
    parts = [f"Verdict bucket: {vlabel}", f"Trust band: {band}"]
    if cov is not None:
        parts.append(f"modeled evidence coverage ≈ {float(cov):.0%}")
    if lo is not None and hi is not None:
        parts.append(f"probability interval {float(lo):.0%}–{float(hi):.0%} on the structural forecast lane")
    return "; ".join(parts)


def _evidence_status(ledger: Dict[str, Any], live_used: bool, live_count: int) -> str:
    tv = ledger.get("tavily") or {}
    pw = ledger.get("playwright") or {}
    ch = ledger.get("cheerio") or {}
    api = ledger.get("official_api") or {}
    ct = api.get("clinicaltrials_gov") or {}
    pm = api.get("pubmed_eutils") or {}
    ofa = api.get("openfda") or {}
    up = ledger.get("uploaded_files") or {}
    parts = [
        f"Tavily attempted: {'yes' if tv.get('attempted') else 'no'}"
        + (f" (success: {tv.get('success')})" if tv.get("attempted") else ""),
        f"Playwright attempted: {'yes' if pw.get('attempted') else 'no'} — wired: {pw.get('wired', False)}",
        f"Cheerio attempted: {'yes' if ch.get('attempted') else 'no'} — wired: {ch.get('wired', False)}",
        (
            "Official API: "
            f"ClinicalTrials.gov attempted {ct.get('attempted')}, success {ct.get('success')}; "
            f"PubMed attempted {pm.get('attempted')}, success {pm.get('success')}; "
            f"openFDA attempted {ofa.get('attempted')}, success {ofa.get('success')}"
        ),
        f"Uploaded files: {up.get('count', 0)}",
        f"Ingested live source rows: {live_count}; live_data_used flag: {live_used}",
    ]
    if tv.get("failure_reason"):
        parts.append(f"Tavily note: {tv['failure_reason']}")
    return " | ".join(parts)


def _direct_answer(
    *,
    prompt: str,
    classification: ScenarioClassification,
    routed_intent: Dict[str, Any],
    final_verdict: Dict[str, Any],
    evidence_summary: Dict[str, Any],
) -> str:
    verdict = final_verdict.get("verdict") or "Unclear"
    dom = classification.domain
    intent = (routed_intent.get("primary_intent") or "").lower()
    quality = evidence_summary.get("quality") or {}
    live_used = bool(quality.get("live_data_used"))
    missing = evidence_summary.get("missing_evidence") or []

    why_gate = final_verdict.get("why") or ""
    base_action = final_verdict.get("next_best_action") or ""

    if dom == "finance" and intent == "market_scan":
        if verdict == "Insufficient Evidence":
            return (
                "Direct answer: I cannot name a decision-grade **best options trade for this week** because live option chains, "
                "quoted IV, volume/open interest, bid/ask quality, earnings and macro catalysts, and your risk profile were not retrieved "
                "or confirmed in this run. "
                + _exploratory_options_framework()
                + f" Best next step (research posture): {base_action or 'connect a market-data connector and rerun with tickers and expiry horizon specified.'}"
            )
        return (
            "Direct answer: Treat any candidate structure as a **research screening output** only—not personal financial advice. "
            f"{why_gate} Use defined-risk framing (max loss, breakeven, invalidation). {base_action}"
        )

    if dom == "biomedical" and intent in {"scientific_roadmap", "research", "discovery"}:
        lead = (
            "Direct answer: Stating a single 'cure for cancer' is not scientifically honest; efficacy is modality- and subtype-specific. "
            + _exploratory_cancer_roadmap()
        )
        if why_gate:
            lead += f" Structural model note: {why_gate}"
        return lead

    if verdict == "Insufficient Evidence":
        gaps = ", ".join(str(m)[:120] for m in missing[:4]) if missing else "primary external corroboration"
        return (
            f"Direct answer: The executive verdict is **{verdict}**, meaning the audit graph does not yet support a confident Yes/No. "
            f"That is not the end of the response—you still get a working conclusion: {why_gate or 'frame the decision as provisional and evidence-limited.'} "
            f"Key missing layers: {gaps}. {base_action}"
        )

    return (
        f"Direct answer: Executive label **{verdict}**. {why_gate} "
        f"{base_action}"
    )


def _assumption_insight(
    classification: ScenarioClassification,
    final_verdict: Dict[str, Any],
    evidence_summary: Dict[str, Any],
) -> str:
    verdict = final_verdict.get("verdict") or ""
    quality = evidence_summary.get("quality") or {}
    if verdict == "Insufficient Evidence" or not quality.get("live_data_used"):
        parts = classification.assumptions or []
        extra = " ".join(parts) if parts else "Exploratory layer uses classifier defaults where live connectors returned sparse rows."
        return (
            "Assumption-based insight: "
            + extra
            + " Separate anything stamped as exploratory from evidence-tight claims once live pulls succeed."
        )
    return (
        "Assumption-based insight: lighter extrapolation than in low-coverage runs—still validate against primary sources before operational bets."
    )


def _safety_note(classification: ScenarioClassification, routed_intent: Dict[str, Any]) -> str:
    if classification.domain == "finance" or routed_intent.get("primary_intent") == "market_scan":
        return (
            "Not financial advice. Outputs are research screening and risk framing only; you are responsible for compliance, "
            "suitability, and jurisdictional rules."
        )
    if classification.domain == "biomedical":
        return "Not medical advice. Consult licensed clinicians for care decisions; this is a research-roadmap synthesis."
    return "General decision-support content—verify facts and policies that apply to your situation."


def build_output_answer(
    *,
    prompt: str,
    classification: ScenarioClassification,
    routed_intent: Dict[str, Any],
    evidence_summary: Dict[str, Any],
    final_verdict: Dict[str, Any],
    trust: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ledger = evidence_summary.get("retrieval_ledger") or {}
    quality = evidence_summary.get("quality") or {}
    live_used = bool(quality.get("live_data_used"))
    live_count = int(quality.get("live_source_count") or 0)
    sources = evidence_summary.get("sources") or []

    direct = _direct_answer(
        prompt=prompt,
        classification=classification,
        routed_intent=routed_intent,
        final_verdict=final_verdict,
        evidence_summary=evidence_summary,
    )
    reasoning = (
        (final_verdict.get("why") or "").strip()
        + " "
        + "Missing evidence flagged: "
        + "; ".join(str(x)[:200] for x in (evidence_summary.get("missing_evidence") or [])[:5])
    ).strip()

    return {
        "direct_answer": direct.strip(),
        "confidence": _confidence_line(final_verdict, trust),
        "evidence_status": _evidence_status(ledger, live_used, live_count),
        "reasoning_summary": reasoning[:4000] or reasoning,
        "data_used_summary": _fmt_sources(sources),
        "data_missing": list(evidence_summary.get("missing_evidence") or []),
        "best_next_action": final_verdict.get("next_best_action") or "",
        "assumption_based_insight": _assumption_insight(classification, final_verdict, evidence_summary),
        "safety_compliance_note": _safety_note(classification, routed_intent),
        "retrieval_ledger": ledger,
        "exploratory": (final_verdict.get("verdict") == "Insufficient Evidence") or not live_used,
    }

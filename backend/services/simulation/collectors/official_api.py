from __future__ import annotations

import os
import urllib.parse
from typing import Any, Dict, List, Tuple

from ..models import ScenarioClassification
from .provenance import fingerprint_text, utc_now_iso
from .types import NormalizedRow


async def _clinicaltrials_gov_snapshots(prompt: str, max_results: int) -> List[Dict[str, Any]]:
    if os.getenv("REALITY_ENGINE_CTGOV", "1").lower() not in {"1", "true", "yes", "on"}:
        return []
    term = urllib.parse.quote((prompt or "").strip()[:220] or "oncology")
    try:
        import httpx

        url = f"https://clinicaltrials.gov/api/v2/studies?query.term={term}&pageSize={max(1, min(10, max_results))}&format=json"
        async with httpx.AsyncClient(timeout=18.0) as client:
            response = await client.get(url)
        if response.status_code != 200:
            return []
        data = response.json()
        out: List[Dict[str, Any]] = []
        for st in (data.get("studies") or [])[:max_results]:
            ps = (st or {}).get("protocolSection") or {}
            im = ps.get("identificationModule") or {}
            title = im.get("briefTitle") or im.get("officialTitle") or "clinical trial snapshot"
            nct = str((st.get("nctId") or im.get("nctId") or st.get("id") or "")).strip()
            pid = urllib.parse.quote(nct.replace(" ", ""))
            canonical = f"https://clinicaltrials.gov/study/{pid}" if nct else "https://clinicaltrials.gov"
            out.append(
                {
                    "title": title[:400],
                    "url": canonical,
                    "snippet": (
                        "Registry-derived trial metadata (ClinicalTrials.gov v2)—check inclusion criteria and primary outcome before extrapolating."
                    ),
                    "_nct": nct,
                }
            )
            if len(out) >= max_results:
                break
        return out
    except Exception:
        return []


async def _pubmed_eutils_snapshots(prompt: str, max_results: int) -> List[Dict[str, Any]]:
    if os.getenv("REALITY_ENGINE_PUBMED", "1").lower() not in {"1", "true", "yes", "on"}:
        return []
    term_raw = (prompt or "").strip()[:400] or "oncology randomized controlled trial"
    term = urllib.parse.quote(term_raw)
    retmax = max(1, min(12, int(max_results)))
    tool_email = urllib.parse.quote((os.getenv("CRUCIB_NCBI_EMAIL") or "dev@crucib.ai").strip())
    try:
        import httpx

        base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        async with httpx.AsyncClient(timeout=22.0) as client:
            esearch_url = (
                f"{base}esearch.fcgi?db=pubmed&retmax={retmax}&retmode=json&tool=CrucibAI&email={tool_email}&term={term}"
            )
            er = await client.get(esearch_url)
            if er.status_code != 200:
                return []
            idlist = (er.json().get("esearchresult") or {}).get("idlist") or []
            idlist = [str(x).strip() for x in idlist if x]
            if not idlist:
                return []
            idstr = ",".join(idlist[:retmax])
            summary_url = f"{base}esummary.fcgi?db=pubmed&id={idstr}&retmode=json&tool=CrucibAI&email={tool_email}"
            sr = await client.get(summary_url)
            if sr.status_code != 200:
                return []
            summ_data = sr.json().get("result") or {}
        out: List[Dict[str, Any]] = []
        for uid in (summ_data.get("uids") or idlist[:retmax]):
            rec = summ_data.get(str(uid))
            if not isinstance(rec, dict):
                continue
            title = (rec.get("title") or "").strip() or "PubMed citation"
            url = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
            journal = str(rec.get("source") or "").strip()
            jp = journal[:120]
            snippet = (
                f"PubMed catalog hit ( PMID:{uid}"
                + (f" · {jp}" if jp else "")
                + " ) — review abstract for indication/method specificity before citing clinical effect."
            )
            out.append({"title": title[:400], "url": url, "snippet": snippet, "pmid": uid})
            if len(out) >= max_results:
                break
        return out
    except Exception:
        return []


async def _openfda_label_snapshot(prompt: str, max_results: int) -> List[Dict[str, Any]]:
    if os.getenv("REALITY_ENGINE_OPENFDA", "1").lower() not in {"1", "true", "yes", "on"}:
        return []
    raw = " ".join((prompt or "").replace(",", " ").split()[:14])[:200] or "cancer therapy"
    term = urllib.parse.quote(raw)
    try:
        import httpx

        url = f"https://api.fda.gov/drug/label.json?search={term}&limit={max(1, min(5, max_results))}"
        async with httpx.AsyncClient(timeout=18.0) as client:
            response = await client.get(url)
        if response.status_code != 200:
            return []
        data = response.json()
        out: List[Dict[str, Any]] = []
        for rec in (data.get("results") or [])[:max_results]:
            openfda = rec.get("openfda") or {}
            brands = openfda.get("brand_name") or []
            brand = brands[0] if isinstance(brands, list) and brands else ""
            title = (brand or "openFDA drug label hit")[:400]
            set_id = str(rec.get("set_id") or rec.get("id") or "").strip()
            link = f"https://api.fda.gov/drug/label.json?search=set_id:{urllib.parse.quote(set_id)}" if set_id else "https://www.fda.gov/drugs"
            ind = rec.get("indications_and_usage")
            if isinstance(ind, list):
                ind = ind[0] if ind else ""
            ind_s = str(ind or "")[:320]
            out.append(
                {
                    "title": title,
                    "url": link,
                    "snippet": (
                        "openFDA drug label snapshot—verify indication, dosing, and warnings in the full SPL PDF. "
                        f"Snippet hint: {ind_s}"
                    ),
                }
            )
            if len(out) >= max_results:
                break
        return out
    except Exception:
        return []


def _dict_to_normalized(d: Dict[str, Any], collector: str) -> NormalizedRow:
    u = str(d.get("url") or "").strip()
    body = str(d.get("snippet") or d.get("content") or "")
    now = utc_now_iso()
    return NormalizedRow(
        title=str(d.get("title") or d.get("url") or "source")[:500],
        url=u,
        snippet=body[:1200],
        content=body[:8000],
        collector=collector,
        score=0.75,
        http_status=200,
        request_url=u,
        final_url=u,
        redirect_count=0,
        content_sha256=fingerprint_text(f"{u}\n{body}"),
        retrieved_at_iso=now,
    )


async def collect_official(
    *,
    classification: ScenarioClassification,
    prompt: str,
    evidence_depth: int,
) -> Tuple[List[NormalizedRow], Dict[str, Any]]:
    ledger = {
        "clinicaltrials_gov": {"attempted": False, "success": False, "failure_reason": None},
        "pubmed_eutils": {"attempted": False, "success": False, "failure_reason": None},
        "openfda": {"attempted": False, "success": False, "failure_reason": None},
    }
    rows: List[NormalizedRow] = []
    if classification.domain != "biomedical":
        return [], {"name": "official_api", "attempted": False, "success": False, "detail": "No official biomedical pull for this domain.", "ledger": ledger}

    ct_on = os.getenv("REALITY_ENGINE_CTGOV", "1").lower() in {"1", "true", "yes", "on"}
    ledger["clinicaltrials_gov"]["attempted"] = ct_on
    ct = await _clinicaltrials_gov_snapshots(prompt, max_results=max(2, min(evidence_depth + 1, 8)))
    ledger["clinicaltrials_gov"]["success"] = len(ct) > 0
    if ct_on and not ct:
        ledger["clinicaltrials_gov"]["failure_reason"] = "Registry HTTP non-200, empty studies, or parse failure."
    for item in ct:
        rows.append(_dict_to_normalized(item, "official_clinicaltrials"))

    pm_on = os.getenv("REALITY_ENGINE_PUBMED", "1").lower() in {"1", "true", "yes", "on"}
    ledger["pubmed_eutils"]["attempted"] = pm_on
    pm = await _pubmed_eutils_snapshots(prompt, max_results=max(3, min(evidence_depth + 2, 10)))
    ledger["pubmed_eutils"]["success"] = len(pm) > 0
    if pm_on and not pm:
        ledger["pubmed_eutils"]["failure_reason"] = "PubMed E-utilities returned no PMIDs or non-200 response."
    for item in pm:
        rows.append(_dict_to_normalized(item, "official_pubmed"))

    fda_on = os.getenv("REALITY_ENGINE_OPENFDA", "1").lower() in {"1", "true", "yes", "on"}
    ledger["openfda"]["attempted"] = fda_on
    fd = await _openfda_label_snapshot(prompt, max_results=max(2, min(evidence_depth, 5)))
    ledger["openfda"]["success"] = len(fd) > 0
    if fda_on and not fd:
        ledger["openfda"]["failure_reason"] = "openFDA label search returned no records or HTTP error."
    for item in fd:
        rows.append(_dict_to_normalized(item, "official_openfda"))

    debug = {
        "name": "official_api",
        "attempted": True,
        "success": len(rows) > 0,
        "rows_returned": len(rows),
        "ledger": ledger,
        "latency_ms": 0.0,
    }
    return rows, debug

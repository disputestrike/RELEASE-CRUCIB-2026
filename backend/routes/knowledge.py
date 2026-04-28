from __future__ import annotations

import base64
import hashlib
import io
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["knowledge"])


def _get_auth():
    from ..deps import get_current_user

    return get_current_user


def _get_optional_user():
    from ..deps import get_optional_user

    return get_optional_user


def _uid(user: Any) -> str:
    if isinstance(user, dict):
        return str(user.get("id") or user.get("user_id") or "anonymous")
    return str(getattr(user, "id", None) or getattr(user, "user_id", None) or "anonymous")


async def _db():
    from ..db_pg import get_db

    return await get_db()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def _chunks(text: str, *, size: int = 1200, overlap: int = 160) -> List[Dict[str, Any]]:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return []
    out: List[Dict[str, Any]] = []
    start = 0
    idx = 0
    while start < len(clean):
        end = min(len(clean), start + size)
        excerpt = clean[start:end].strip()
        if excerpt:
            out.append({"index": idx, "text": excerpt, "char_start": start, "char_end": end})
            idx += 1
        if end >= len(clean):
            break
        start = max(0, end - overlap)
    return out


def _extract_text_from_base64(file_base64: str, mime_type: str | None, file_name: str | None) -> tuple[str, List[str]]:
    warnings: List[str] = []
    if not file_base64:
        return "", warnings
    try:
        raw = base64.b64decode(file_base64, validate=False)
    except Exception:
        raise HTTPException(status_code=400, detail="file_base64 could not be decoded")
    mime = (mime_type or "").lower()
    name = (file_name or "").lower()
    if "pdf" in mime or name.endswith(".pdf"):
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(io.BytesIO(raw))
            pages = [(page.extract_text() or "") for page in reader.pages]
            text = "\n\n".join(pages).strip()
            if not text:
                warnings.append("pdf_decoded_but_no_text_extracted")
            return text, warnings
        except Exception as exc:
            warnings.append(f"pdf_text_extraction_unavailable: {str(exc)[:160]}")
            return "", warnings
    try:
        return raw.decode("utf-8", errors="ignore").strip(), warnings
    except Exception:
        warnings.append("binary_file_type_requires_dedicated_extractor")
        return "", warnings


class KnowledgeIngestBody(BaseModel):
    source_type: str = Field("document", max_length=40)
    title: str = Field("", max_length=240)
    content: str = Field("", max_length=1_000_000)
    type: str = Field("Custom", max_length=80)
    url: Optional[str] = Field(None, max_length=2000)
    file_name: Optional[str] = Field(None, max_length=240)
    mime_type: Optional[str] = Field(None, max_length=160)
    file_base64: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(10, ge=1, le=50)


@router.get("/knowledge")
async def knowledge_home(user: dict = Depends(_get_optional_user())):
    return {
        "status": "available",
        "purpose": "Persistent project/user knowledge sources for RAG, document grounding, and skill-agent context.",
        "endpoints": {
            "sources": "/api/knowledge/sources",
            "ingest": "/api/knowledge/ingest",
            "search": "/api/knowledge/search",
            "capabilities": "/api/knowledge/ingestion-capabilities",
        },
        "truth_statement": "JSON text and URL records are live. PDF text extraction is live when pypdf is installed; otherwise the endpoint reports an unsupported extraction warning.",
    }


@router.get("/knowledge/ingestion-capabilities")
async def knowledge_capabilities(user: dict = Depends(_get_optional_user())):
    try:
        import pypdf  # noqa: F401

        pdf_status = "available"
    except Exception:
        pdf_status = "requires_config"
    return {
        "status": "available",
        "accepted_inputs": ["document_text", "url_record", "base64_text_file", "base64_pdf"],
        "extractors": [
            {"name": "plain_text", "status": "available", "mime_types": ["text/plain", "text/markdown", "application/json", "text/csv"]},
            {"name": "pdf_text", "status": pdf_status, "mime_types": ["application/pdf"], "required_package": "pypdf"},
        ],
        "persistence": ["knowledge_sources", "knowledge_documents"],
        "skill_agent_usage": "The dynamic Skill Agent can reference ingested knowledge and can create new reusable instruction skills when a capability gap is detected.",
    }


@router.get("/knowledge/sources")
async def list_sources(user: dict = Depends(_get_auth())):
    db = await _db()
    uid = _uid(user)
    docs = await db.knowledge_sources.find({"user_id": uid}).to_list(200)
    docs.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return {"sources": docs, "count": len(docs)}


@router.post("/knowledge/ingest")
async def ingest_knowledge(body: KnowledgeIngestBody, user: dict = Depends(_get_auth())):
    text = (body.content or "").strip()
    warnings: List[str] = []
    extracted_from_file = False
    if not text and body.file_base64:
        text, warnings = _extract_text_from_base64(body.file_base64, body.mime_type, body.file_name)
        extracted_from_file = bool(text)
    source_type = (body.source_type or "document").strip().lower()
    if source_type not in {"document", "url", "file"}:
        raise HTTPException(status_code=400, detail="source_type must be document, url, or file")
    if source_type == "url" and not body.url:
        raise HTTPException(status_code=400, detail="url is required for URL knowledge")
    if source_type != "url" and not text:
        detail = "content or file_base64 with extractable text is required"
        if warnings:
            detail = f"{detail}; {'; '.join(warnings)}"
        raise HTTPException(status_code=400, detail=detail)

    now = _now()
    uid = _uid(user)
    title = (body.title or body.file_name or body.url or "Untitled knowledge").strip()[:240]
    source_id = f"ks_{uuid.uuid4().hex}"
    chunk_rows = _chunks(text)
    source_doc = {
        "id": source_id,
        "user_id": uid,
        "source_type": source_type,
        "title": title,
        "type": body.type or "Custom",
        "url": body.url,
        "file_name": body.file_name,
        "mime_type": body.mime_type,
        "status": "indexed" if chunk_rows or source_type == "url" else "pending",
        "ingestion_status": "indexed" if chunk_rows or source_type == "url" else "metadata_only",
        "chunk_count": len(chunk_rows),
        "content_hash": _hash(text or body.url or title),
        "metadata": {
            **(body.metadata or {}),
            "warnings": warnings,
            "extracted_from_file": extracted_from_file,
            "text_length": len(text),
        },
        "created_at": now,
        "updated_at": now,
    }
    db = await _db()
    await db.knowledge_sources.insert_one(source_doc)
    for chunk in chunk_rows:
        await db.knowledge_documents.insert_one(
            {
                "id": f"kd_{uuid.uuid4().hex}",
                "source_id": source_id,
                "user_id": uid,
                "title": title,
                "source_type": source_type,
                "text": chunk["text"],
                "chunk_index": chunk["index"],
                "char_start": chunk["char_start"],
                "char_end": chunk["char_end"],
                "created_at": now,
            }
        )
    return {
        "status": source_doc["ingestion_status"],
        "source": source_doc,
        "chunks_created": len(chunk_rows),
        "warnings": warnings,
        "persisted": True,
    }


@router.get("/knowledge/sources/{source_id}/chunks")
async def source_chunks(source_id: str, user: dict = Depends(_get_auth())):
    db = await _db()
    uid = _uid(user)
    source = await db.knowledge_sources.find_one({"id": source_id, "user_id": uid})
    if not source:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    chunks = await db.knowledge_documents.find({"source_id": source_id, "user_id": uid}).to_list(500)
    chunks.sort(key=lambda row: row.get("chunk_index") or 0)
    return {"source": source, "chunks": chunks, "count": len(chunks)}


@router.post("/knowledge/search")
async def search_knowledge(body: KnowledgeSearchBody, user: dict = Depends(_get_auth())):
    db = await _db()
    uid = _uid(user)
    query = body.query.strip().lower()
    terms = [t for t in re.split(r"\W+", query) if len(t) > 1]
    chunks = await db.knowledge_documents.find({"user_id": uid}).to_list(1000)
    results = []
    for row in chunks:
        text = str(row.get("text") or "")
        low = text.lower()
        score = sum(low.count(term) for term in terms)
        if query in low:
            score += 5
        if score <= 0:
            continue
        results.append(
            {
                "source_id": row.get("source_id"),
                "title": row.get("title"),
                "chunk_index": row.get("chunk_index"),
                "excerpt": text[:500],
                "score": min(1.0, score / max(5, len(terms) * 3)),
            }
        )
    results.sort(key=lambda row: row["score"], reverse=True)
    return {"results": results[: body.limit], "count": min(len(results), body.limit)}


@router.delete("/knowledge/sources/{source_id}")
async def delete_source(source_id: str, user: dict = Depends(_get_auth())):
    db = await _db()
    uid = _uid(user)
    source = await db.knowledge_sources.find_one({"id": source_id, "user_id": uid})
    if not source:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    await db.knowledge_sources.delete_one({"id": source_id, "user_id": uid})
    await db.knowledge_documents.delete_many({"source_id": source_id, "user_id": uid})
    return {"status": "deleted", "source_id": source_id}

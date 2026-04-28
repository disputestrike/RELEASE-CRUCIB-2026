"""RAG memory REST surface — WS-D."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Path

from ..services.rag.store import get_store

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("")
async def stats():
    return {"stats": get_store().stats()}


@router.post("/upsert")
async def upsert(body: dict = Body(...)):
    collection = body.get("collection")
    docs = body.get("docs")
    if not collection or not isinstance(docs, list):
        raise HTTPException(status_code=400, detail="collection and docs (list) required")
    for d in docs:
        if "id" not in d or "text" not in d:
            raise HTTPException(status_code=400, detail="each doc must have id and text")
    return await get_store().upsert(collection, docs)


@router.post("/query")
async def query(body: dict = Body(...)):
    collection = body.get("collection")
    q = body.get("query")
    k = int(body.get("k", 5))
    where = body.get("where")
    if not collection or not q:
        raise HTTPException(status_code=400, detail="collection and query required")
    hits = await get_store().query(collection, q, k=k, where=where)
    return {"hits": hits, "count": len(hits)}


@router.delete("/{collection}/{doc_id}")
async def forget(
    collection: str = Path(...),
    doc_id: str = Path(...),
):
    return await get_store().forget(collection, [doc_id])

from fastapi import APIRouter, Depends, HTTPException, Body, Path
from typing import Dict, Any, Optional
from backend.app.schemas.retrieval import QueryRequest, RetrievalResponse, StatsResponse
from backend.app.core.rbac import RequireViewer
from backend.app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])
_service = RetrievalService()

@router.post("/search", response_model=RetrievalResponse)
def search(req: QueryRequest, role=RequireViewer):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query is empty")
    hits = _service.search(
        req.query,
        k=req.k,
        bm25_weight=req.bm25_weight,
        faiss_weight=req.faiss_weight,
        filters=req.filters or {},
    )
    return RetrievalResponse(query=req.query, hits=hits)

@router.get("/stats", response_model=StatsResponse)
def stats(role=RequireViewer):
    return _service.stats()

# ---- Saved Queries ----
@router.get("/saved_queries", response_model=Dict[str, Any])
def list_saved_queries(role=RequireViewer):
    return {"saved_queries": _service.saved_queries()}

@router.post("/saved_queries", response_model=Dict[str, Any])
def save_query(name: str = Body(..., embed=True), request: QueryRequest = Body(...)):
    _service.save_query(name, request.model_dump())
    return {"ok": True, "name": name}

@router.delete("/saved_queries/{name}", response_model=Dict[str, Any])
def delete_query(name: str = Path(...)):
    _service.delete_query(name)
    return {"ok": True, "name": name}

# ---- Watchlists ----
@router.get("/watchlists", response_model=Dict[str, Any])
def list_watchlists(role=RequireViewer):
    return {"watchlists": _service.watchlists()}

@router.post("/watchlists", response_model=Dict[str, Any])
def save_watchlist(name: str = Body(..., embed=True), doc_ids: list[str] = Body(default=[], embed=True)):
    _service.save_watchlist(name, doc_ids)
    return {"ok": True, "name": name, "size": len(doc_ids)}

@router.delete("/watchlists/{name}", response_model=Dict[str, Any])
def delete_watchlist(name: str = Path(...)):
    _service.delete_watchlist(name)
    return {"ok": True, "name": name}

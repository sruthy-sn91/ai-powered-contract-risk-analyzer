from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, List, Dict, Any
from backend.app.schemas.extraction import ExtractionResult, EntityGraph, GraphQueryResult, ClauseSegment
from backend.app.services.extraction_service import ExtractionService

router = APIRouter(prefix="/extraction", tags=["extraction"])
_service = ExtractionService()

@router.post("/extract", response_model=ExtractionResult)
def extract_from_text(
    text: str = Body(..., embed=True, description="Normalized contract text"),
    clauses: Optional[List[ClauseSegment]] = Body(default=None),
):
    return _service.extract(text=text, clauses=clauses or [])

@router.post("/entity_graph/build", response_model=EntityGraph)
def build_graph(
    text: str = Body(..., embed=True),
    clauses: Optional[List[ClauseSegment]] = Body(default=None),
):
    return _service.build_graph(text=text, clauses=clauses or [])

@router.get("/entity_graph/query", response_model=GraphQueryResult)
def query_graph(
    days: int = Query(90, ge=1, le=3650),
    service_credits_lt: Optional[float] = Query(None),
):
    if not _service.has_graph():
        raise HTTPException(status_code=400, detail="No graph built. Call /entity_graph/build first.")
    return _service.sample_query_auto_renewals(days=days, service_credits_lt=service_credits_lt)

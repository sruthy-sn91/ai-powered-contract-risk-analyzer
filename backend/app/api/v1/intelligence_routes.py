from fastapi import APIRouter, Body
from typing import List, Dict, Any
from backend.app.services.intelligence_service import IntelligenceService
from backend.app.schemas.intelligence import UnusualClauseResult, CounterfactualRewriteResponse, PlaybookItem, Trigger

router = APIRouter(prefix="/intelligence", tags=["intelligence"])
svc = IntelligenceService()

@router.post("/enrich_obligations", response_model=Dict[str, Any])
def enrich_obligations(text: str = Body(..., embed=True)):
    return svc.enrich_obligations(text)

@router.post("/triggers", response_model=List[Trigger])
def triggers(text: str = Body(..., embed=True)):
    return svc.find_triggers(text)

@router.get("/playbooks", response_model=List[PlaybookItem])
def playbooks():
    return svc.playbooks()

@router.post("/unusual", response_model=List[UnusualClauseResult])
def unusual(clauses: List[str] = Body(..., embed=True)):
    return svc.unusual_clauses(clauses)

@router.post("/counterfactual", response_model=CounterfactualRewriteResponse)
def counterfactual(text: str = Body(..., embed=True)):
    return svc.counterfactual(text)

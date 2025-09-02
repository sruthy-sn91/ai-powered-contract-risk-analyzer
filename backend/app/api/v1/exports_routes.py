from fastapi import APIRouter, Body
from typing import List, Dict, Any
from backend.app.services.exports_service import ExportsService

router = APIRouter(prefix="/exports", tags=["exports"])
svc = ExportsService()

@router.post("/executive_brief", response_model=dict)
def executive_brief(risk: Dict[str, Any] = Body(...)):
    return svc.exec_brief(risk)

@router.post("/star_schema", response_model=dict)
def star_schema(rows: List[Dict[str, Any]] = Body(...)):
    return svc.star_schema(rows)

@router.post("/redline", response_model=dict)
def redline(original: str = Body(..., embed=True), revised: str = Body(..., embed=True), title: str = Body("Redline", embed=True)):
    return svc.redline(original, revised, title)

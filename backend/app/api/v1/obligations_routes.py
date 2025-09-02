from fastapi import APIRouter, Body
from typing import List, Dict, Any
from backend.app.services.obligations_service import ObligationsService, AAOCT

router = APIRouter(prefix="/obligations", tags=["obligations"])
_service = ObligationsService()

@router.post("/extract", response_model=Dict[str, List[AAOCT]])
def extract_obligations(text: str = Body(..., embed=True)):
    return {"obligations": _service.extract(text)}

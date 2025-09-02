from fastapi import APIRouter, Body
from typing import List, Dict, Any
from backend.app.services.summarize_service import SummarizeService

router = APIRouter(prefix="/summarize", tags=["summaries"])
_service = SummarizeService()

@router.post("", response_model=dict)
def summarize(text: str = Body(..., embed=True), max_sentences: int = Body(3, embed=True)):
    res = _service.summarize(text=text, max_sentences=max_sentences)
    return res

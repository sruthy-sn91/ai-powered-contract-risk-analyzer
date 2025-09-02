from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Trigger(BaseModel):
    kind: str
    span: Optional[List[int]] = None
    text: Optional[str] = None

class PlaybookItem(BaseModel):
    topic: str
    red_flags: List[str]
    fallbacks: List[str]
    preferred: List[str]
    variance_band: str
    counter_proposals: List[str]

class UnusualClauseResult(BaseModel):
    text: str
    score: float
    neighbors: List[int] = []

class CounterfactualRewriteResponse(BaseModel):
    original: str
    suggestion: str
    diff_text: str
    tag: str = "suggested — not legal advice"

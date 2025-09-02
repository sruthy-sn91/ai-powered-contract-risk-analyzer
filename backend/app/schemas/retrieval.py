from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class QueryRequest(BaseModel):
    query: str
    k: int = 10
    bm25_weight: float = 0.5
    faiss_weight: float = 0.5
    filters: Optional[Dict[str, str]] = None

class RetrievalHit(BaseModel):
    doc_id: str
    score: float
    title: Optional[str] = None
    snippet: Optional[str] = None
    path: Optional[str] = None
    clause_start: Optional[int] = None
    clause_end: Optional[int] = None
    source: Optional[str] = Field(default="acord", description="acord|cuad|demo")

class RetrievalResponse(BaseModel):
    query: str
    hits: List[RetrievalHit]

class StatsResponse(BaseModel):
    bm25_docs: int
    faiss_docs: int
    last_build: Optional[str] = None
    model_name: Optional[str] = None

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class RationaleSpan(BaseModel):
    start: int
    end: int
    text: Optional[str] = None

class ClassifyRequest(BaseModel):
    text: str = Field(..., description="Raw or normalized clause text to classify")

class ClassifyResponse(BaseModel):
    label: str
    prob: float
    rationale_spans: List[RationaleSpan] = []

class TrainLoraRequest(BaseModel):
    subset_size: int = Field(200, ge=10, le=5000)
    csv_path: Optional[str] = None
    base_model: str = "distilbert-base-uncased"
    epochs: int = Field(1, ge=1, le=5)
    batch_size: int = Field(8, ge=2, le=32)

class TrainLoraResponse(BaseModel):
    macro_f1: float
    auprc: float
    num_labels: int
    artifact_path: str

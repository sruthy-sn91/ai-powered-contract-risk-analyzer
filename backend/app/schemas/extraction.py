from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

# -------- Parsing / OCR --------

class ParsedPage(BaseModel):
    page_number: int
    text: str
    ocr_used: bool = False
    rotation: int = 0
    has_tables: bool = False
    watermarks: List[str] = []
    quality_score: float = 0.0  # 0..1

class ClauseSegment(BaseModel):
    id: str
    title: Optional[str] = None
    heading: Optional[str] = None
    start: int
    end: int

class DetectedMeta(BaseModel):
    governing_law: List[str] = []
    jurisdiction: List[str] = []
    languages: List[str] = []
    currencies: List[str] = []

class ParsingResult(BaseModel):
    pages: List[ParsedPage]
    normalized_text: str
    clauses: List[ClauseSegment]
    meta: DetectedMeta

# -------- Extraction --------

class MoneyAmount(BaseModel):
    raw: str
    value: Optional[float] = None
    currency: Optional[str] = None
    normalized: Optional[str] = None

class Percentage(BaseModel):
    raw: str
    value: Optional[float] = None  # 0-100

class DateFound(BaseModel):
    raw: str
    iso: Optional[str] = None

class Thresholds(BaseModel):
    caps: List[MoneyAmount] = []
    baskets: List[MoneyAmount] = []
    de_minimis: List[MoneyAmount] = []
    aggregates: List[MoneyAmount] = []

class ExtractionResult(BaseModel):
    dates: List[DateFound] = []
    amounts: List[MoneyAmount] = []
    percentages: List[Percentage] = []
    thresholds: Thresholds = Field(default_factory=Thresholds)
    fx_snapshot_date: Optional[str] = None  # stub field, e.g., "2025-08-27"

# -------- Graph --------

class GraphNode(BaseModel):
    id: str
    label: str
    type: Literal["party", "affiliate", "clause", "obligation", "event", "notice"]
    attrs: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    source: str = Field(alias="from")
    target: str = Field(alias="to")
    label: Optional[str] = None
    attrs: Dict[str, Any] = Field(default_factory=dict)

class EntityGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    render_path: Optional[str] = None  # PNG/SVG saved under /exports/graphs

class GraphQueryResult(BaseModel):
    query: str
    matches: List[str] = []   # list of node ids / clause ids

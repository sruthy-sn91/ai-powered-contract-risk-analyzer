from __future__ import annotations
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class RiskLensScores(BaseModel):
    legal: float
    operational: float
    regulatory: float
    counterparty: float
    financial: float

class RiskScoreRequest(BaseModel):
    text: str
    business_unit: Optional[str] = Field(default=None, description="e.g., 'default' if not provided")

class RiskScoreResponse(BaseModel):
    lens: RiskLensScores
    composite: float
    weights: Dict[str, float]

class ScenarioParams(BaseModel):
    # simple what-if sliders
    probability_of_breach: float = Field(0.1, ge=0.0, le=1.0)
    penalty_per_breach: float = 100000.0
    liability_cap: float = 250000.0
    credit_uplift_pct: float = 0.0  # service credits as mitigation (- reduces exposure)
    num_events_lambda: float = 0.5  # Poisson rate

    simulations: int = Field(2000, ge=200, le=20000)

class StressTestResult(BaseModel):
    mean_exposure: float
    p95_exposure: float
    p99_exposure: float
    parameters: ScenarioParams

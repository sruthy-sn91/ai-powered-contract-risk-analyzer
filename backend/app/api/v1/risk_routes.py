from fastapi import APIRouter, Body
from backend.app.schemas.risk import RiskScoreRequest, RiskScoreResponse, ScenarioParams, StressTestResult
from backend.app.services.risk_service import RiskService

router = APIRouter(prefix="/risk", tags=["risk"])
_service = RiskService()

@router.post("/score", response_model=RiskScoreResponse)
def score(req: RiskScoreRequest):
    return _service.score(text=req.text, bu=req.business_unit)

@router.post("/stress", response_model=StressTestResult)
def stress(params: ScenarioParams = Body(...)):
    return _service.stress_test(params)

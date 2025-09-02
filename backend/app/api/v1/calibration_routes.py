from fastapi import APIRouter, Body
from typing import List
from backend.app.services.calibration_service import CalibrationService

router = APIRouter(prefix="/calibration", tags=["calibration"])
svc = CalibrationService()

@router.post("/fit", response_model=dict)
def fit(y_true: List[float] = Body(..., embed=True), y_pred: List[float] = Body(..., embed=True)):
    return svc.fit(y_true, y_pred)

@router.post("/score", response_model=dict)
def score(y_pred: float = Body(..., embed=True), alpha: float = Body(0.1, embed=True)):
    lo, hi = svc.interval(y_pred, alpha=alpha)
    return {"pred": y_pred, "lower": lo, "upper": hi, "alpha": alpha}

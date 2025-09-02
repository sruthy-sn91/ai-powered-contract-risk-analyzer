from fastapi import APIRouter, HTTPException, Body
from backend.app.schemas.classify import (
    ClassifyRequest,
    ClassifyResponse,
    TrainLoraRequest,
    TrainLoraResponse,
)
from backend.app.services.lora_classifier_service import LoraClassifierService

router = APIRouter(prefix="/lora", tags=["classification"])
_service = LoraClassifierService()

@router.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text is empty")
    return _service.classify(req.text)

@router.post("/train/lora", response_model=TrainLoraResponse)
def train_lora(req: TrainLoraRequest = Body(...)):
    return _service.train_lora(
        subset_size=req.subset_size,
        csv_path=req.csv_path,
        base_model=req.base_model,
        epochs=req.epochs,
        batch_size=req.batch_size,
    )

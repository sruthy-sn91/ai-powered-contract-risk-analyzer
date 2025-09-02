from __future__ import annotations
from pathlib import Path
from typing import Optional, List

from backend.app.schemas.classify import (
    ClassifyResponse,
    TrainLoraResponse,
)
from models.inference import LoraClassifier, ART_DIR
from models.lora_finetune_cuad import train_lora as lora_train
from backend.app.core.config import settings

class LoraClassifierService:
    def __init__(self):
        self._clf = LoraClassifier()

    def _reload(self):
        # re-instantiate to pick up new adapters after training
        self._clf = LoraClassifier()

    def classify(self, text: str) -> ClassifyResponse:
        label, prob, spans = self._clf.predict(text)
        return ClassifyResponse(
            label=label,
            prob=float(prob),
            rationale_spans=[
                {"start": s, "end": e, "text": text[s:e]} for s, e in spans[:3]
            ],
        )

    def train_lora(
        self,
        subset_size: int = 200,
        csv_path: Optional[str] = None,
        base_model: str = "distilbert-base-uncased",
        epochs: int = 1,
        batch_size: int = 8,
    ) -> TrainLoraResponse:
        if csv_path:
            csv_p = Path(csv_path)
        else:
            csv_p = Path(settings.CUAD_DIR) / "master_clauses.csv"
        out_dir = ART_DIR
        res = lora_train(
            csv_path=csv_p,
            subset_size=subset_size,
            base_model=base_model,
            out_dir=out_dir,
            epochs=epochs,
            batch_size=batch_size,
        )
        # refresh in-memory model
        self._reload()
        return TrainLoraResponse(
            macro_f1=float(res["macro_f1"]),
            auprc=float(res["auprc"]),
            num_labels=int(res["num_labels"]),
            artifact_path=str(res["artifact_path"]),
        )

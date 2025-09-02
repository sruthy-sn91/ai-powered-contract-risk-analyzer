"""
Tiny LoRA demo on CUAD 'master_clauses.csv'.

- Reads CUAD_DIR from .env via backend.app.core.config
- Detects text and label columns robustly
- Trains a small classifier with LoRA adapters (few epochs)
- Saves to models/artifacts/lora_cuad/

Usage:
  python -m models.lora_finetune_cuad --subset_size 200 --csv_path /path/to/master_clauses.csv
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Tuple, List

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score, average_precision_score
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model

from backend.app.core.config import settings


TEXT_CANDIDATES = ["clause_text", "text", "Text", "segment_text", "clause", "Sentence", "content", "raw_text"]
LABEL_CANDIDATES = ["label", "Label", "clause_type", "category", "clause_category"]

DEFAULT_OUT = Path("models/artifacts/lora_cuad")


def _detect_cols(df: pd.DataFrame) -> Tuple[str, str]:
    text_col = next((c for c in TEXT_CANDIDATES if c in df.columns), None)
    label_col = next((c for c in LABEL_CANDIDATES if c in df.columns), None)
    if text_col is None or label_col is None:
        raise ValueError(f"Could not find text/label columns. Have: {df.columns.tolist()}")
    return text_col, label_col


class CuadDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item


def _load_df(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    return df


def train_lora(
    csv_path: Path,
    subset_size: int = 200,
    base_model: str = "distilbert-base-uncased",
    out_dir: Path = DEFAULT_OUT,
    epochs: int = 1,
    batch_size: int = 8,
):
    device = "cpu"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = _load_df(csv_path)
    text_col, label_col = _detect_cols(df)
    df = df[[text_col, label_col]].dropna()
    if subset_size and len(df) > subset_size:
        df = df.sample(n=subset_size, random_state=42)

    le = LabelEncoder()
    y = le.fit_transform(df[label_col].astype(str).values)
    X_train, X_val, y_train, y_val = train_test_split(
        df[text_col].astype(str).values, y, test_size=0.2, random_state=42, stratify=y
    )

    tok = AutoTokenizer.from_pretrained(base_model)
    enc_train = tok(list(X_train), truncation=True, padding=True, max_length=256)
    enc_val = tok(list(X_val), truncation=True, padding=True, max_length=256)

    train_ds = CuadDataset(enc_train, y_train)
    val_ds = CuadDataset(enc_val, y_val)

    model = AutoModelForSequenceClassification.from_pretrained(base_model, num_labels=len(le.classes_))
    lora_cfg = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_lin", "v_lin", "query", "value"],  # covers DistilBERT/BERT
        bias="none",
        task_type="SEQ_CLS",
    )
    model = get_peft_model(model, lora_cfg)

    args = TrainingArguments(
        output_dir=str(out_dir / "hf_out"),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=3e-4,
        logging_steps=20,
        evaluation_strategy="epoch",
        save_strategy="no",
        report_to=[],  # no wandb/etc
    )

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        probs = torch.tensor(logits).softmax(dim=1).numpy()
        preds = probs.argmax(axis=1)
        macro_f1 = f1_score(labels, preds, average="macro")
        # AUPRC (macro)
        from sklearn.preprocessing import label_binarize

        y_true_bin = label_binarize(labels, classes=list(range(len(le.classes_))))
        auprc = average_precision_score(y_true_bin, probs, average="macro")
        return {"macro_f1": float(macro_f1), "auprc": float(auprc)}

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tok,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    metrics = trainer.evaluate()

    # Save adapters and label mappings
    model.save_pretrained(str(out_dir))
    tok.save_pretrained(str(out_dir))
    (out_dir / "labels.json").write_text(
        json.dumps({"labels": le.classes_.tolist()}, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "meta.json").write_text(
        json.dumps(
            {
                "base_model": base_model,
                "subset_size": int(subset_size),
                "epochs": int(epochs),
                "metrics": metrics,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "macro_f1": float(metrics.get("eval_macro_f1", 0.0)),
        "auprc": float(metrics.get("eval_auprc", 0.0)),
        "num_labels": int(len(le.classes_)),
        "artifact_path": str(out_dir.resolve()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset_size", type=int, default=200)
    ap.add_argument("--csv_path", type=str, default=None)
    ap.add_argument("--base_model", type=str, default="distilbert-base-uncased")
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch_size", type=int, default=8)
    args = ap.parse_args()

    csv_path = Path(args.csv_path) if args.csv_path else Path(settings.CUAD_DIR) / "master_clauses.csv"
    out = DEFAULT_OUT

    res = train_lora(
        csv_path=csv_path,
        subset_size=args.subset_size,
        base_model=args.base_model,
        out_dir=out,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

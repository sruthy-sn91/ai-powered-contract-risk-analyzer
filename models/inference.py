from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel

ART_DIR = Path("models/artifacts/lora_cuad")

# Label-specific cues to produce rationale spans if available
LABEL_PATTERNS: Dict[str, List[re.Pattern]] = {
    "Governing Law": [
        re.compile(r"(?i)\bgoverned by the laws? of [A-Za-z ,.-]+"),
        re.compile(r"(?i)\bgoverning law\b.*"),
    ],
    "Limitation of Liability": [
        re.compile(r"(?i)\blimitation of liability\b.*"),
        re.compile(r"(?i)\bneither party shall be liable\b.*"),
    ],
    "Term and Termination": [
        re.compile(r"(?i)\bterm(?:ination)?\b.*"),
        re.compile(r"(?i)\bauto(?:matic)?\s*renew(al|s)?\b.*"),
    ],
    "Confidentiality": [
        re.compile(r"(?i)\bconfidential(?: information)?\b.*"),
    ],
}

FALLBACK_LABELS = ["Other", "Governing Law", "Limitation of Liability", "Term and Termination", "Confidentiality"]


class LoraClassifier:
    def __init__(self, artifact_dir: Path = ART_DIR):
        self.art_dir = artifact_dir
        self.labels = FALLBACK_LABELS
        self.tok = None
        self.model = None
        self.rule_only = True
        self._load()

    def _load(self):
        if not self.art_dir.exists():
            return
        labels_p = self.art_dir / "labels.json"
        base_model = "distilbert-base-uncased"
        meta_p = self.art_dir / "meta.json"
        if labels_p.exists():
            try:
                self.labels = json.loads(labels_p.read_text(encoding="utf-8")).get("labels", FALLBACK_LABELS)
            except Exception:
                pass
        if meta_p.exists():
            try:
                base_model = json.loads(meta_p.read_text()).get("base_model", base_model)
            except Exception:
                pass
        try:
            self.tok = AutoTokenizer.from_pretrained(str(self.art_dir))
            base = AutoModelForSequenceClassification.from_pretrained(base_model, num_labels=len(self.labels))
            self.model = PeftModel.from_pretrained(base, str(self.art_dir))
            self.model.eval()
            self.rule_only = False
        except Exception:
            # Fall back to rule-based
            self.tok = AutoTokenizer.from_pretrained(base_model)
            self.model = None
            self.rule_only = True

    def _predict_model(self, text: str) -> Tuple[str, float]:
        # returns (label, prob)
        enc = self.tok([text], truncation=True, padding=True, max_length=256, return_tensors="pt")
        with torch.no_grad():
            logits = self.model(**enc).logits
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
        idx = int(probs.argmax())
        return self.labels[idx], float(probs[idx])

    def _heuristic_label(self, text: str) -> Tuple[str, float]:
        for label, pats in LABEL_PATTERNS.items():
            for p in pats:
                if p.search(text):
                    return label, 0.90
        if "shall" in text.lower():
            return "Obligations", 0.60
        return "Other", 0.50

    def _rationales_for_label(self, text: str, label: str) -> List[Tuple[int, int]]:
        spans: List[Tuple[int, int]] = []
        for p in LABEL_PATTERNS.get(label, []):
            m = p.search(text)
            if m:
                spans.append((m.start(), m.end()))
        if not spans:
            # naive fallback: first sentence
            m = re.search(r".+?[\.!\?](\s|$)", text, re.S)
            if m:
                spans.append((m.start(), m.end()))
        return spans

    def predict(self, text: str):
        if text is None or not text.strip():
            return "Other", 0.0, []
        if not self.rule_only:
            try:
                label, prob = self._predict_model(text)
            except Exception:
                label, prob = self._heuristic_label(text)
        else:
            label, prob = self._heuristic_label(text)
        spans = self._rationales_for_label(text, label)
        return label, prob, spans

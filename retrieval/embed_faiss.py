import json
from pathlib import Path
from typing import List, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

def _normalize(x: np.ndarray) -> np.ndarray:
    x = x.astype("float32")
    faiss.normalize_L2(x)
    return x

class EmbedFAISS:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.doc_ids: List[str] = []

    def build(self, items: List[Tuple[str, str]]):
        self.doc_ids = [i[0] for i in items]
        texts = [i[1] for i in items]
        emb = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        emb = _normalize(emb)
        self.index = faiss.IndexFlatIP(emb.shape[1])
        self.index.add(emb)

    def query(self, q: str, k: int = 10) -> List[Tuple[str, float]]:
        if self.index is None:
            return []
        qv = self.model.encode([q], convert_to_numpy=True)
        qv = _normalize(qv)
        D, I = self.index.search(qv, k)
        res = []
        for idx, score in zip(I[0], D[0]):
            if idx == -1:
                continue
            res.append((self.doc_ids[idx], float(score)))
        return res

    def save(self, dir_path: str):
        p = Path(dir_path)
        p.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(p / "index.faiss"))
        (p / "doc_ids.json").write_text(json.dumps(self.doc_ids, ensure_ascii=False))

    def load(self, dir_path: str):
        p = Path(dir_path)
        self.index = faiss.read_index(str(p / "index.faiss"))
        self.doc_ids = json.loads((p / "doc_ids.json").read_text())

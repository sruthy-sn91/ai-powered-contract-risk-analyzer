import pickle
from typing import List, Tuple
from rank_bm25 import BM25Okapi

class BM25Local:
    def __init__(self):
        self.bm25 = None
        self.doc_ids: List[str] = []
        self.tokenized_corpus: List[List[str]] = []

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return text.lower().split()

    def build(self, items: List[Tuple[str, str]]):
        """items: List of (doc_id, text)"""
        self.doc_ids = [i[0] for i in items]
        self.tokenized_corpus = [self._tokenize(i[1]) for i in items]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def query(self, q: str, k: int = 10) -> List[Tuple[str, float]]:
        if not self.bm25:
            return []
        toks = self._tokenize(q)
        scores = self.bm25.get_scores(toks)
        ranked = sorted(zip(self.doc_ids, scores), key=lambda x: x[1], reverse=True)[:k]
        return ranked

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump({"doc_ids": self.doc_ids, "bm25": self.bm25}, f)

    def load(self, path: str):
        with open(path, "rb") as f:
            obj = pickle.load(f)
        self.doc_ids = obj["doc_ids"]
        self.bm25 = obj["bm25"]

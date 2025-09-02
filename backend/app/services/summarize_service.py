from __future__ import annotations
import re
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

KEYWORDS = [
    "term", "termination", "renewal", "payment", "fees", "liability", "indemn", "governing law",
    "jurisdiction", "confidential", "data", "privacy", "notice", "service level", "credit",
]

class SummarizeService:
    def _split_sentences(self, text: str) -> List[str]:
        # simple deterministic splitter
        parts = re.split(r"(?<=[\.\?!])\s+", text.strip())
        return [p.strip() for p in parts if p.strip()]

    def summarize(self, text: str, max_sentences: int = 3) -> Dict:
        sents = self._split_sentences(text)
        if not sents:
            return {"executive_summary": "", "key_takeaways": []}

        # TF-IDF scoring plus keyword boost (deterministic)
        tfidf = TfidfVectorizer(max_features=1000, ngram_range=(1,2))
        X = tfidf.fit_transform(sents)
        base_scores = np.asarray(X.sum(axis=1)).ravel()

        boosts = np.zeros_like(base_scores)
        for i, s in enumerate(sents):
            lw = s.lower()
            boosts[i] = sum(1 for k in KEYWORDS if k in lw)

        scores = base_scores + 0.2 * boosts
        idxs = list(np.argsort(-scores))[:max_sentences]
        idxs.sort()  # deterministic order by appearance

        summary = " ".join(sents[i] for i in idxs)

        # Key takeaways = top 5 keyworded sentences (short)
        kt_idxs = [i for i, s in enumerate(sents) if any(k in s.lower() for k in KEYWORDS)]
        kt_idxs = kt_idxs[:5]
        takeaways = [sents[i] for i in kt_idxs]

        return {"executive_summary": summary, "key_takeaways": takeaways}

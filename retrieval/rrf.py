from collections import defaultdict
from typing import List, Tuple, Dict

def rrf_fuse(rankings: List[List[Tuple[str, float]]], k: int = 10, k_rrf: int = 60) -> List[Tuple[str, float]]:
    """
    rankings: list of ranked lists [(doc_id, score), ...] in descending quality order
    Returns fused list limited to k.
    """
    pos_map: List[Dict[str, int]] = []
    for r in rankings:
        m = {}
        for i, (doc_id, _) in enumerate(r):
            m[doc_id] = i + 1  # 1-based
        pos_map.append(m)

    scores = defaultdict(float)
    for m in pos_map:
        for doc_id, rank in m.items():
            scores[doc_id] += 1.0 / (k_rrf + rank)

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
    return fused

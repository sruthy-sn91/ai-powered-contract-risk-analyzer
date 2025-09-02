import argparse
import json
from pathlib import Path
from typing import Dict, Tuple, List
import numpy as np
import pandas as pd

def load_corpus(acord_dir: Path) -> Dict[str, str]:
    corpus_p = acord_dir / "corpus.jsonl"
    if not corpus_p.exists():
        return {}
    data = {}
    for line in corpus_p.read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        _id = obj.get("_id") or obj.get("id")
        txt = " ".join([obj.get("title") or "", obj.get("text") or ""]).strip()
        data[str(_id)] = txt
    return data

def load_queries(acord_dir: Path) -> Dict[str, str]:
    qp = acord_dir / "queries.jsonl"
    if not qp.exists():
        return {}
    data = {}
    for line in qp.read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        data[str(obj.get("_id") or obj.get("id"))] = obj.get("text") or ""
    return data

def load_qrels(acord_dir: Path) -> Dict[str, Dict[str, int]]:
    """
    Supports both:
      - BEIR qrels (3-col):   query-id \t corpus-id \t score
      - TREC qrels (4-col):   qid Q0 docid rel
    Also tolerates optional headers: ["query-id","corpus-id","score"].

    Returns: {qid: {docid: rel_int}}
    """
    import pandas as pd
    qrels_dir = acord_dir / "qrels"
    files = sorted(qrels_dir.glob("*.tsv"))
    if not files:
        raise FileNotFoundError(f"No qrels found in {qrels_dir}")

    out: Dict[str, Dict[str, int]] = {}
    for fp in files:
        # Try to read with header inference; if that fails, use header=None
        try:
            df = pd.read_csv(fp, sep="\t", dtype=str)
        except Exception:
            df = pd.read_csv(fp, sep="\t", header=None, dtype=str)

        cols = [c.lower() for c in df.columns.astype(str).tolist()]

        # Named BEIR columns
        if set(["query-id", "corpus-id", "score"]).issubset(set(cols)):
            q_col = cols.index("query-id")
            d_col = cols.index("corpus-id")
            s_col = cols.index("score")
            for _, row in df.iterrows():
                qid = str(row.iloc[q_col])
                did = str(row.iloc[d_col])
                try:
                    rel = int(float(row.iloc[s_col]))
                except Exception:
                    rel = 1
                out.setdefault(qid, {})[did] = rel
            continue

        # No headers: handle 3 or 4 columns by position
        if df.shape[1] >= 4:
            # TREC: qid Q0 docid rel
            for _, row in df.iterrows():
                qid = str(row.iloc[0])
                did = str(row.iloc[2])
                try:
                    rel = int(float(row.iloc[3]))
                except Exception:
                    rel = 1
                out.setdefault(qid, {})[did] = rel
        elif df.shape[1] == 3:
            # BEIR: query-id corpus-id score
            for _, row in df.iterrows():
                qid = str(row.iloc[0])
                did = str(row.iloc[1])
                try:
                    rel = int(float(row.iloc[2]))
                except Exception:
                    rel = 1
                out.setdefault(qid, {})[did] = rel
        else:
            raise ValueError(f"Unexpected qrels shape in {fp}: {df.shape}")

    return out

def mrr_at_k(ranked: List[str], relevant: Dict[str, int], k: int) -> float:
    for i, did in enumerate(ranked[:k], start=1):
        if did in relevant and relevant[did] > 0:
            return 1.0 / i
    return 0.0

def ndcg_at_k(ranked: List[str], relevant: Dict[str, int], k: int) -> float:
    dcg = 0.0
    for i, did in enumerate(ranked[:k], start=1):
        rel = relevant.get(did, 0)
        if rel > 0:
            dcg += (2**rel - 1) / np.log2(i + 1)
    # Ideal DCG
    ideal = sorted(relevant.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal, start=1):
        idcg += (2**rel - 1) / np.log2(i + 1)
    return dcg / idcg if idcg > 0 else 0.0

def evaluate(topk_map: Dict[str, List[Tuple[str, float]]], qrels: Dict[str, Dict[str, int]], k: int = 10):
    mrrs, ndcgs = [], []
    for qid, ranked in topk_map.items():
        relevant = qrels.get(qid, {})
        ranked_ids = [d for d, _ in ranked]
        mrrs.append(mrr_at_k(ranked_ids, relevant, k))
        ndcgs.append(ndcg_at_k(ranked_ids, relevant, k))
    return float(np.mean(mrrs) if mrrs else 0.0), float(np.mean(ndcgs) if ndcgs else 0.0)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--acord_dir", type=str, required=True)
    ap.add_argument("--results_json", type=str, required=True, help="Map of qid -> [(doc_id, score), ...]")
    ap.add_argument("--k", type=int, default=10)
    args = ap.parse_args()

    acord = Path(args.acord_dir)
    qrels = load_qrels(acord)
    if not qrels:
        print("No qrels found. Skipping eval.")
        raise SystemExit(0)

    topk_map = json.loads(Path(args.results_json).read_text())
    mrr, ndcg = evaluate(topk_map, qrels, k=args.k)
    print(json.dumps({"MRR@k": mrr, "nDCG@k": ndcg, "k": args.k}, indent=2))

import json
from pathlib import Path
from datetime import datetime
from backend.app.core.config import settings
from backend.app.core.path_resolver import index_dir, acord_dir
from retrieval.bm25_local import BM25Local
from retrieval.embed_faiss import EmbedFAISS
from retrieval.beir_acord_loader import load_corpus, load_queries, evaluate, load_qrels

def main():
    idx = index_dir()
    bm25_path = idx / "bm25.pkl"
    faiss_dir = idx / "faiss"
    meta_path = idx / "meta.json"
    results_path = idx / "last_results.json"

    acord = acord_dir()
    corpus = load_corpus(acord)

    if not corpus:
        print("No ACORD corpus.jsonl found. Seed demo first: `make seed`")
        return

    items = list(corpus.items())

    # BM25
    bm25 = BM25Local()
    bm25.build(items)
    bm25.save(str(bm25_path))

    # FAISS
    faiss_dir.mkdir(parents=True, exist_ok=True)
    faissi = EmbedFAISS(settings.MODEL_NAME)
    faissi.build(items)
    faissi.save(str(faiss_dir))

    # Optional BEIR-style eval
    queries = load_queries(acord)
    qrels = load_qrels(acord)
    topk_map = {}
    if queries:
        for qid, qtext in list(queries.items())[:200]:  # limit for speed
            b = bm25.query(qtext, k=10)
            f = faissi.query(qtext, k=10)
            # simple combine by score sum
            sc = {}
            for d, s in b:
                sc[d] = sc.get(d, 0.0) + float(s)
            for d, s in f:
                sc[d] = sc.get(d, 0.0) + float(s)
            ranked = sorted(sc.items(), key=lambda x: x[1], reverse=True)[:10]
            topk_map[qid] = ranked

    metrics = {"MRR@10": 0.0, "nDCG@10": 0.0}
    if qrels and topk_map:
        mrr, ndcg = evaluate(topk_map, qrels, k=10)
        metrics = {"MRR@10": mrr, "nDCG@10": ndcg}

    results_path.write_text(json.dumps({"metrics": metrics}, indent=2))
    meta = {"last_build": datetime.utcnow().isoformat() + "Z", "docs": len(items)}
    meta_path.write_text(json.dumps(meta, indent=2))

    print("=== Build complete ===")
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    main()

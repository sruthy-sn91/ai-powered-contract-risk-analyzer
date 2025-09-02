import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from backend.app.core.config import settings
from backend.app.core.path_resolver import index_dir
from backend.app.schemas.retrieval import RetrievalHit, StatsResponse
from retrieval.bm25_local import BM25Local
from retrieval.embed_faiss import EmbedFAISS
from retrieval.rrf import rrf_fuse

class RetrievalService:
    def __init__(self):
        idx = index_dir()
        self.bm25_path = idx / "bm25.pkl"
        self.faiss_dir = idx / "faiss"
        self.meta_path = idx / "meta.json"
        self.meta = {}
        self._bm25 = BM25Local()
        self._faiss = EmbedFAISS(settings.MODEL_NAME)
        self._loaded = False

        # optional metadata for filtering (doc_id -> fields)
        self.docs_meta_path = idx / "docs_meta.json"
        self._docs_meta: Dict[str, Dict[str, str]] = {}

        # saved queries & watchlists
        self.saved_store_path = idx / "saved_store.json"

    def load(self):
        if self.bm25_path.exists():
            self._bm25.load(str(self.bm25_path))
        if (self.faiss_dir / "index.faiss").exists():
            self._faiss.load(str(self.faiss_dir))
        if self.meta_path.exists():
            self.meta = json.loads(self.meta_path.read_text())
        if self.docs_meta_path.exists():
            try:
                self._docs_meta = json.loads(self.docs_meta_path.read_text())
            except Exception:
                self._docs_meta = {}
        self._ensure_saved_store()
        self._loaded = True

    def _ensure_saved_store(self):
        if not self.saved_store_path.exists():
            self.saved_store_path.write_text(json.dumps({"saved_queries": {}, "watchlists": {}}, indent=2))

    def _read_saved(self) -> Dict[str, Dict]:
        try:
            return json.loads(self.saved_store_path.read_text())
        except Exception:
            return {"saved_queries": {}, "watchlists": {}}

    def _write_saved(self, data: Dict[str, Dict]):
        self.saved_store_path.write_text(json.dumps(data, indent=2))

    # ---- public saved queries/watchlists API ----
    def saved_queries(self) -> Dict[str, Dict]:
        if not self._loaded:
            self.load()
        return self._read_saved().get("saved_queries", {})

    def save_query(self, name: str, payload: Dict):
        if not self._loaded:
            self.load()
        data = self._read_saved()
        data.setdefault("saved_queries", {})[name] = payload
        self._write_saved(data)

    def delete_query(self, name: str):
        if not self._loaded:
            self.load()
        data = self._read_saved()
        data.get("saved_queries", {}).pop(name, None)
        self._write_saved(data)

    def watchlists(self) -> Dict[str, List[str]]:
        if not self._loaded:
            self.load()
        return self._read_saved().get("watchlists", {})

    def save_watchlist(self, name: str, doc_ids: List[str]):
        if not self._loaded:
            self.load()
        data = self._read_saved()
        data.setdefault("watchlists", {})[name] = list(dict.fromkeys(doc_ids))
        self._write_saved(data)

    def delete_watchlist(self, name: str):
        if not self._loaded:
            self.load()
        data = self._read_saved()
        data.get("watchlists", {}).pop(name, None)
        self._write_saved(data)

    # ---- search ----
    def search(
        self,
        query: str,
        k: int,
        bm25_weight: float,
        faiss_weight: float,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[RetrievalHit]:
        if not self._loaded:
            self.load()

        bm25_res = self._bm25.query(query, k=max(k, 50)) if self._bm25.bm25 else []
        faiss_res = self._faiss.query(query, k=max(k, 50)) if self._faiss.index else []

        def normalize(res: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
            if not res:
                return []
            scores = [s for _, s in res]
            mn, mx = min(scores), max(scores)
            rng = (mx - mn) or 1.0
            return [(d, (s - mn) / rng) for d, s in res]

        nb = normalize(bm25_res)
        nf = normalize(faiss_res)

        score_map: Dict[str, float] = {}
        for d, s in nb:
            score_map[d] = score_map.get(d, 0.0) + bm25_weight * s
        for d, s in nf:
            score_map[d] = score_map.get(d, 0.0) + faiss_weight * s
        merged_sorted = sorted(score_map.items(), key=lambda x: x[1], reverse=True)

        # optional filtering by docs_meta
        if filters:
            merged_sorted = [item for item in merged_sorted if self._passes_filter(item[0], filters)]

        merged_sorted = merged_sorted[:k]

        rrf = rrf_fuse([bm25_res, faiss_res], k=k)
        rank_pos = {d: i for i, (d, _) in enumerate(rrf)}
        final = sorted(merged_sorted, key=lambda x: (rank_pos.get(x[0], 1e6), -x[1]))[:k]

        hits = []
        for d, s in final:
            meta = self._docs_meta.get(d, {})
            hits.append(
                RetrievalHit(
                    doc_id=d,
                    score=float(s),
                    title=meta.get("title"),
                    snippet=meta.get("snippet"),
                    path=meta.get("path"),
                    source=meta.get("source", "acord"),
                    clause_start=None,
                    clause_end=None,
                )
            )
        return hits

    def _passes_filter(self, doc_id: str, filters: Dict[str, str]) -> bool:
        meta = self._docs_meta.get(doc_id, {})
        if not meta:
            return True  # if no metadata, don't exclude
        # exact-match filters
        for key in ["type", "BU", "jurisdiction", "counterparty"]:
            if key in filters and filters[key]:
                if str(meta.get(key)) != str(filters[key]):
                    return False
        # date range
        if "date_from" in filters or "date_to" in filters:
            d = meta.get("date")
            if d:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(d[:10])
                    if filters.get("date_from"):
                        if dt < datetime.fromisoformat(filters["date_from"][:10]):
                            return False
                    if filters.get("date_to"):
                        if dt > datetime.fromisoformat(filters["date_to"][:10]):
                            return False
                except Exception:
                    pass
        return True

    def stats(self) -> StatsResponse:
        if not self._loaded:
            self.load()
        bm25_docs = len(self._bm25.doc_ids)
        faiss_docs = len(self._faiss.doc_ids)
        last_build = self.meta.get("last_build")
        return StatsResponse(
            bm25_docs=bm25_docs,
            faiss_docs=faiss_docs,
            last_build=last_build,
            model_name=settings.MODEL_NAME,
        )

from __future__ import annotations
import re
from typing import List, Dict, Any
from dataclasses import dataclass
from backend.app.services.obligations_service import ObligationsService, AAOCT
from backend.app.schemas.intelligence import Trigger, PlaybookItem, UnusualClauseResult, CounterfactualRewriteResponse
from sklearn.neighbors import LocalOutlierFactor
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

TRIGGER_PATS = {
    "early_termination": re.compile(r"(?i)\btermination for convenience\b"),
    "mac": re.compile(r"(?i)\bmaterial adverse change\b|\bMAC\b"),
    "force_majeure_carveout": re.compile(r"(?i)\bforce[-\s]?majeure\b.*\b(exclud|carve|exception)\b"),
    "cross_default": re.compile(r"(?i)\bcross[-\s]?default\b"),
    "step_in_rights": re.compile(r"(?i)\bstep[-\s]?in rights?\b"),
}

PLAYBOOKS = [
    PlaybookItem(
        topic="liability",
        red_flags=["unlimited liability", "exclusion of indirect damages carve-in"],
        fallbacks=["cap at 12 months fees", "exclude indirect/consequential damages"],
        preferred=["cap at 6-12 months fees; mutual", "exclude indirect & special damages"],
        variance_band="±20% of ACV",
        counter_proposals=["Introduce cap tied to annual fees", "Mutual carve-outs only for IP infringement & breach of confidentiality"],
    ),
    PlaybookItem(
        topic="indemnity",
        red_flags=["broad indemnity w/o fault", "defense cost uncapped"],
        fallbacks=["limit to third-party claims", "require prompt notice & control of defense"],
        preferred=["mutual indemnity limited to third-party IP and bodily injury"],
        variance_band="n/a",
        counter_proposals=["Add obligation to mitigate; cap defense costs"],
    ),
    PlaybookItem(
        topic="termination",
        red_flags=["termination for convenience by counterparty only"],
        fallbacks=["mutual convenience with notice", "early termination fee"],
        preferred=["mutual termination rights with 30-day notice"],
        variance_band="30–60 days notice",
        counter_proposals=["Add cure period before termination for cause"],
    ),
    PlaybookItem(
        topic="confidentiality",
        red_flags=["perpetual confidentiality obligations", "no residual knowledge"],
        fallbacks=["3–5 year term", "allow residuals"],
        preferred=["3-year term; standard exclusions; residuals allowed"],
        variance_band="36 months",
        counter_proposals=["Limit survival to 3 years; add standard exclusions"],
    ),
    PlaybookItem(
        topic="SLA",
        red_flags=["no service credits", "uptime below 99.5%"],
        fallbacks=["tiered service credits", "monthly uptime report"],
        preferred=["99.9% uptime; service credits tiered"],
        variance_band="99.5–99.9%",
        counter_proposals=["Add service credit multipliers for repeated breaches"],
    ),
]

class IntelligenceService:
    def __init__(self):
        self._obl = ObligationsService()

    def enrich_obligations(self, text: str) -> Dict[str, Any]:
        base: List[AAOCT] = self._obl.extract(text)
        # simple enrichment: detect responsible team and KPI hints
        enriched = []
        for o in base:
            team = "Legal" if "notice" in o.sentence.lower() else ("Finance" if "fees" in o.sentence.lower() or "pay" in o.sentence.lower() else "Operations")
            kpi = "On-time delivery" if "within" in (o.time or "").lower() else None
            enriched.append({**o.dict(), "responsible_team": team, "kpi_hint": kpi})
        return {"obligations": enriched}

    def find_triggers(self, text: str) -> List[Trigger]:
        out: List[Trigger] = []
        for kind, pat in TRIGGER_PATS.items():
            m = pat.search(text)
            if m:
                out.append(Trigger(kind=kind, span=[m.start(), m.end()], text=m.group(0)[:200]))
        return out

    def playbooks(self) -> List[PlaybookItem]:
        return PLAYBOOKS

    def unusual_clauses(self, clauses: List[str]) -> List[UnusualClauseResult]:
        # fallback to TF-IDF embeddings + LOF
        vec = TfidfVectorizer(max_features=2048, ngram_range=(1,2))
        X = vec.fit_transform([c or "" for c in clauses]).toarray()
        if len(clauses) <= 5:
            model = IsolationForest(contamination=0.2, random_state=42)
            scores = -model.fit_predict(X)  # 2 for outlier? we want higher score = more unusual
            decision = -model.decision_function(X)
            norm = (decision - decision.min()) / (decision.ptp() + 1e-9)
            s = norm.tolist()
        else:
            lof = LocalOutlierFactor(n_neighbors=max(2, min(10, len(clauses)-1)), novelty=False)
            vals = -lof.fit_predict(X)  # 1 inlier, -1 outlier
            scores_raw = -lof.negative_outlier_factor_  # higher = more outlier
            s = ((scores_raw - scores_raw.min()) / (scores_raw.ptp() + 1e-9)).tolist()
        # nearest neighbors (cosine on TFIDF)
        from sklearn.metrics.pairwise import cosine_similarity
        sims = cosine_similarity(X)
        results: List[UnusualClauseResult] = []
        for i, c in enumerate(clauses):
            nn = np.argsort(-sims[i])[1:4].tolist()
            results.append(UnusualClauseResult(text=c, score=float(s[i]), neighbors=nn))
        return results

    def counterfactual(self, text: str) -> CounterfactualRewriteResponse:
        # very lightweight: apply a few policy-compliant rewrites
        suggestion = text
        suggestion = re.sub(r"(?i)unlimited liability", "liability capped at 12 months of fees", suggestion)
        suggestion = re.sub(r"(?i)termination for convenience\b(?! by both parties)", "termination for convenience by either party with 30 days' notice", suggestion)
        # produce inline diff
        import difflib
        diff = difflib.ndiff(text.split(), suggestion.split())
        diff_text = " ".join(diff)
        return CounterfactualRewriteResponse(original=text, suggestion=suggestion, diff_text=diff_text)

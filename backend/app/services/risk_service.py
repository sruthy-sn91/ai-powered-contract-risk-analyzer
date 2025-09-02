from __future__ import annotations
import re
import numpy as np
from typing import Dict
from backend.app.core.config import settings
from backend.app.schemas.risk import RiskLensScores, RiskScoreResponse, ScenarioParams, StressTestResult

FLAG_PATTERNS = {
    "legal": [
        re.compile(r"(?i)\bunlimited liability\b"),
        re.compile(r"(?i)\bindemnif(y|ication)\b.*\bunlimited\b"),
        re.compile(r"(?i)\bgoverned by the laws of [A-Za-z ,.-]+"),
    ],
    "operational": [
        re.compile(r"(?i)\bservice level\b"),
        re.compile(r"(?i)\bsla\b"),
        re.compile(r"(?i)\bdisaster recovery\b"),
    ],
    "regulatory": [
        re.compile(r"(?i)\bdata protection\b"),
        re.compile(r"(?i)\bGDPR\b|\bCCPA\b|\bHIPAA\b"),
        re.compile(r"(?i)\boutsourcing\b|\bcloud\b|\bSaaS\b"),
    ],
    "counterparty": [
        re.compile(r"(?i)\bcreditworthiness\b|\binsolvenc(y|e)\b"),
        re.compile(r"(?i)\bsanctions?\b|\bOFAC\b"),
    ],
    "financial": [
        re.compile(r"(?i)\btermination for convenience\b"),
        re.compile(r"(?i)\bprice increase\b|\bfees?\b"),
        re.compile(r"(?i)\bservice credits?\b"),
    ],
}

def _lens_score(text: str, pats) -> float:
    score = 0.0
    for p in pats:
        m = p.search(text)
        if m:
            score += 0.34
    return float(min(score, 1.0))

class RiskService:
    def score(self, text: str, bu: str | None) -> RiskScoreResponse:
        lens = RiskLensScores(
            legal=_lens_score(text, FLAG_PATTERNS["legal"]),
            operational=_lens_score(text, FLAG_PATTERNS["operational"]),
            regulatory=_lens_score(text, FLAG_PATTERNS["regulatory"]),
            counterparty=_lens_score(text, FLAG_PATTERNS["counterparty"]),
            financial=_lens_score(text, FLAG_PATTERNS["financial"]),
        )
        w = settings.risk_weights(bu)
        comp = (
            lens.legal * w.get("legal", .3) +
            lens.operational * w.get("operational", .2) +
            lens.regulatory * w.get("regulatory", .2) +
            lens.counterparty * w.get("counterparty", .15) +
            lens.financial * w.get("financial", .15)
        )
        return RiskScoreResponse(lens=lens, composite=float(round(comp, 4)), weights=w)

    def stress_test(self, params: ScenarioParams) -> StressTestResult:
        # Monte Carlo of penalty exposure with capping and mitigation
        n = params.simulations
        # number of events per year ~ Poisson
        events = np.random.poisson(lam=params.num_events_lambda, size=n)
        breaches = np.random.binomial(events, params.probability_of_breach)
        penalties = breaches * params.penalty_per_breach
        # apply mitigation via service credits uplift (reduce penalties)
        penalties = penalties * (1.0 - max(-0.5, min(0.5, params.credit_uplift_pct)) )
        # apply liability cap
        exposure = np.minimum(penalties, params.liability_cap)
        mean = float(np.mean(exposure))
        p95 = float(np.percentile(exposure, 95))
        p99 = float(np.percentile(exposure, 99))
        return StressTestResult(mean_exposure=mean, p95_exposure=p95, p99_exposure=p99, parameters=params)

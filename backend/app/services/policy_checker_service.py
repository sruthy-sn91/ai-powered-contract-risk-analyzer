from __future__ import annotations
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
from backend.app.core.config import settings
from backend.app.schemas.policy import PolicyCheckRequest, PolicyCheckResponse, PolicyRuleHit

def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))

JURIS_OVERLAYS = {
    "EU": [{"topic":"data protection","link":"https://example.com/gdpr","summary":"GDPR obligations on processing, transfers."}],
    "US-NY": [{"topic":"outsourcing","link":"https://example.com/nydfs","summary":"NYDFS guidance for third-party risk management."}],
    "IN": [{"topic":"data protection","link":"https://example.com/dpdp","summary":"DPDP Act personal data handling."}],
}

SANCTIONS_KYC_REFS = [
    "OFAC SDN list (stub reference)",
    "UN Consolidated Sanctions list (stub reference)",
    "Internal KYC registry (read-only stub)",
]

class PolicyCheckerService:
    def check(self, req: PolicyCheckRequest) -> PolicyCheckResponse:
        policy_p = Path(req.policy_path) if req.policy_path else Path(settings.POLICIES_DIR) / "policy.example.yaml"
        pol = _load_yaml(policy_p)
        rules = pol.get("rules", [])
        text = req.text or ""
        hits: List[PolicyRuleHit] = []

        for r in rules:
            pats = r.get("pattern")
            if isinstance(pats, str):
                pats = [pats]
            if not pats:
                continue
            for pat in pats:
                try:
                    p = re.compile(pat)
                except Exception:
                    continue
                m = p.search(text)
                if m:
                    hits.append(PolicyRuleHit(
                        rule_id=r.get("id",""),
                        description=r.get("description",""),
                        severity=r.get("severity","medium"),
                        tags=r.get("tags",[]),
                        matched_text=m.group(0)[:200],
                        start=m.start(),
                        end=m.end(),
                        regulatory_trace=self._trace_for_tags(r.get("tags", []), req.jurisdiction)
                    ))
                    break

        return PolicyCheckResponse(hits=hits, sanctions_kyc_refs=SANCTIONS_KYC_REFS)

    def _trace_for_tags(self, tags: List[str], juris: Optional[str]) -> Optional[Dict[str, str]]:
        if not tags:
            return None
        overlays = JURIS_OVERLAYS.get(juris or "", [])
        for ov in overlays:
            # crude: map 'data protection' tag to overlay
            if any(t.lower() in ov["topic"] for t in tags):
                return {"link": ov["link"], "summary": ov["summary"]}
        # fallback generic entry
        return {"link": "https://example.com/regulatory-guidance", "summary": "Consider applicable sector guidance."}

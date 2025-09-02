from pathlib import Path
from backend.app.services.policy_checker_service import PolicyCheckerService
from backend.app.services.risk_service import RiskService
from backend.app.services.intelligence_service import IntelligenceService
from backend.app.services.exports_service import ExportsService

SAMPLE_TEXT = (
    "This Agreement shall be governed by the laws of New York. "
    "Supplier shall provide the Services within 30 days, subject to Customer acceptance. "
    "Termination for convenience by the Customer is allowed. "
    "In the event of a material adverse change (MAC), either party may terminate. "
    "Service credits will apply."
)

def test_policy_validation_hits():
    svc = PolicyCheckerService()
    res = svc.check(type("obj", (), {"text": SAMPLE_TEXT, "policy_path": None, "jurisdiction":"US-NY"}) )
    assert hasattr(res, "hits")
    assert any(h.rule_id for h in res.hits)

def test_risk_scores_and_composite():
    rsvc = RiskService()
    out = rsvc.score(SAMPLE_TEXT, bu=None)
    assert out.lens.legal >= 0.0
    assert 0.0 <= out.composite <= 1.0

def test_intelligence_routes_like():
    isvc = IntelligenceService()
    trg = isvc.find_triggers(SAMPLE_TEXT)
    assert isinstance(trg, list)
    assert any(t.kind for t in trg)

def test_exports_files_created(tmp_path):
    ex = ExportsService()
    risk_obj = {
        "lens": {"legal":0.6,"operational":0.3,"regulatory":0.2,"counterparty":0.1,"financial":0.4},
        "composite":0.39,
        "top_issues":["Unlimited liability", "Termination for convenience (one-sided)"],
        "renewals":[{"contract":"C-101","date":"2026-01-01"}]
    }
    p = ex.exec_brief(risk_obj)
    assert Path(p["pdf_path"]).exists()

    rows = [{"contract_id":"C-1","counterparty":"Acme","bu":"default","lens":risk_obj["lens"],"composite":risk_obj["composite"]}]
    out = ex.star_schema(rows)
    assert Path(out["csv"]).exists()
    assert Path(out["parquet"]).exists()

    rl = ex.redline("Unlimited liability applies.", "Liability capped at 12 months of fees applies.", "Sample Redline")
    assert Path(rl["docx"]).exists()
    assert Path(rl["pdf"]).exists()

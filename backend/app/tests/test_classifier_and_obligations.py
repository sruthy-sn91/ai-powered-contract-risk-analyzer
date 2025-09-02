from backend.app.services.lora_classifier_service import LoraClassifierService
from backend.app.services.obligations_service import ObligationsService

def test_classify_smoke():
    svc = LoraClassifierService()
    text = "This Agreement shall be governed by the laws of New York."
    res = svc.classify(text)
    assert hasattr(res, "label")
    assert res.prob >= 0.0
    assert isinstance(res.rationale_spans, list)

def test_obligations_aaoct():
    svc = ObligationsService()
    sample = (
        "Supplier shall provide the Services within 30 days subject to Customer acceptance. "
        "Licensee shall pay all fees by March 1, 2026. "
        "The Borrower shall deliver financial statements if requested by the Lender."
    )
    res = svc.extract(sample)
    assert isinstance(res, list)
    assert len(res) >= 2
    assert any(o.actor and o.action for o in res)

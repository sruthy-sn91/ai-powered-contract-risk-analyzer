import os
from pathlib import Path
from backend.app.services.parsing_ocr_service import ParsingOCRService
from backend.app.services.extraction_service import ExtractionService

def _pick_sample_file() -> Path:
    """Pick 1–2 CUAD files if present; prefer .pdf, else any .txt."""
    env = os.getenv("CUAD_DIR", "./data/cuad")
    base = Path(env)
    if not base.exists():
        return None
    # look for PDFs first
    pdfs = list(base.rglob("*.pdf"))
    if pdfs:
        return pdfs[0]
    txts = list(base.rglob("*.txt"))
    if txts:
        return txts[0]
    return None

def test_parsing_and_extraction_smoke():
    sample = _pick_sample_file()
    if not sample:
        # nothing to test; skip gracefully
        return

    svc = ParsingOCRService()
    # simulate path mode (no upload)
    res = __import__("asyncio").get_event_loop().run_until_complete(svc.parse(file=None, path=str(sample)))
    assert res.normalized_text is not None
    assert isinstance(res.pages, list) and len(res.pages) >= 1
    assert isinstance(res.clauses, list)
    # meta fields present
    assert hasattr(res.meta, "languages")
    assert hasattr(res.meta, "currencies")

    es = ExtractionService()
    ext = es.extract(text=res.normalized_text, clauses=res.clauses)
    assert ext is not None
    assert hasattr(ext, "dates")
    assert hasattr(ext, "amounts")
    # Build graph and run sample query
    g = es.build_graph(text=res.normalized_text, clauses=res.clauses)
    assert g.nodes and g.edges  # at least something
    qr = es.sample_query_auto_renewals(days=90, service_credits_lt=100000.0)
    assert hasattr(qr, "matches")

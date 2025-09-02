from fastapi import FastAPI
from backend.app.core.logging import configure_logging
from backend.app.core.config import settings
from backend.app.api.v1.retrieval_routes import router as retrieval_router
from backend.app.api.v1.parsing_ocr_routes import router as parsing_router
from backend.app.api.v1.extraction_routes import router as extraction_router
from backend.app.api.v1.lora_classifier_routes import router as lora_router
from backend.app.api.v1.summarize_routes import router as summarize_router
from backend.app.api.v1.obligations_routes import router as obligations_router
from backend.app.api.v1.risk_routes import router as risk_router
from backend.app.api.v1.policy_checker_routes import router as policy_router
from backend.app.api.v1.intelligence_routes import router as intel_router
from backend.app.api.v1.calibration_routes import router as calib_router
from backend.app.api.v1.governance_audit_routes import router as gov_router
from backend.app.api.v1.exports_routes import router as exports_router
from backend.app.api.v1.auth_routes import router as auth_router

configure_logging()
app = FastAPI(title="Contract Risk Analyzer (Local)")

@app.get("/health")
def health():
    return {
        "status": "ok",
        "acord_dir": settings.ACORD_DIR,
        "cuad_dir": settings.CUAD_DIR,
        "policies_dir": settings.POLICIES_DIR,
    }

app.include_router(retrieval_router, prefix="/api/v1")
app.include_router(parsing_router, prefix="/api/v1")
app.include_router(extraction_router, prefix="/api/v1")
app.include_router(lora_router, prefix="/api/v1")
app.include_router(summarize_router, prefix="/api/v1")
app.include_router(obligations_router, prefix="/api/v1")
app.include_router(risk_router, prefix="/api/v1")
app.include_router(policy_router, prefix="/api/v1")
app.include_router(intel_router, prefix="/api/v1")
app.include_router(calib_router, prefix="/api/v1")
app.include_router(gov_router, prefix="/api/v1")
app.include_router(exports_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

from fastapi import APIRouter, Body
from backend.app.schemas.policy import PolicyCheckRequest, PolicyCheckResponse
from backend.app.services.policy_checker_service import PolicyCheckerService

router = APIRouter(prefix="/policy", tags=["policy"])
_service = PolicyCheckerService()

@router.post("/check", response_model=PolicyCheckResponse)
def check(req: PolicyCheckRequest = Body(...)):
    return _service.check(req)

from fastapi import APIRouter, Body
from typing import List, Dict, Any
from backend.app.services.governance_audit_service import GovernanceAuditService

router = APIRouter(prefix="/governance", tags=["governance"])
svc = GovernanceAuditService()

@router.post("/review/create", response_model=dict)
def create(review: dict = Body(...)):
    return svc.create(review)

@router.post("/review/comment", response_model=dict)
def comment(review_id: str = Body(..., embed=True), comment: str = Body(..., embed=True), author: str = Body("anon", embed=True)):
    return svc.comment(review_id, comment, author)

@router.post("/review/disposition", response_model=dict)
def disposition(review_id: str = Body(..., embed=True), decision: str = Body(..., embed=True), justification: str = Body("", embed=True), approver: str = Body("anon", embed=True)):
    return svc.disposition(review_id, decision, justification, approver)

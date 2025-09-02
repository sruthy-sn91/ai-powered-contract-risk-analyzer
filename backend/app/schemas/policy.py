from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PolicyCheckRequest(BaseModel):
    text: str
    policy_path: Optional[str] = None  # defaults to ./policies/policy.example.yaml
    jurisdiction: Optional[str] = None  # e.g., "US-NY", "EU", "IN"

class PolicyRuleHit(BaseModel):
    rule_id: str
    description: str
    severity: str
    tags: List[str] = []
    matched_text: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None
    regulatory_trace: Optional[Dict[str, str]] = None  # {"link": "...", "summary": "..."}

class PolicyCheckResponse(BaseModel):
    hits: List[PolicyRuleHit]
    sanctions_kyc_refs: List[str] = []

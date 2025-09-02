from __future__ import annotations
import json, time
from pathlib import Path
from typing import Dict, Any
from backend.app.core.config import settings

AUDIT_LOG = Path(settings.EXPORTS_DIR) / "audit.log"
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

class GovernanceAuditService:
    def __init__(self):
        self._mem: Dict[str, Dict[str, Any]] = {}

    def _append_log(self, event: Dict[str, Any]):
        event["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def create(self, review: Dict[str, Any]) -> Dict[str, Any]:
        rid = review.get("id") or f"rev-{int(time.time())}"
        review["id"] = rid
        review["status"] = "open"
        review["comments"] = []
        self._mem[rid] = review
        self._append_log({"type": "review_create", "id": rid, "payload": review})
        return {"id": rid, "status": "open"}

    def comment(self, review_id: str, comment: str, author: str):
        rv = self._mem.get(review_id) or {"id": review_id, "status":"unknown", "comments":[]}
        rv.setdefault("comments", []).append({"author": author, "text": comment})
        self._mem[review_id] = rv
        self._append_log({"type": "review_comment", "id": review_id, "author": author, "comment": comment})
        return {"ok": True, "id": review_id}

    def disposition(self, review_id: str, decision: str, justification: str, approver: str):
        # decision: accept | risk-accept | renegotiate | decline
        rv = self._mem.get(review_id) or {"id": review_id}
        rv["status"] = "closed"
        rv["decision"] = decision
        rv["justification"] = justification
        rv["approver"] = approver
        self._mem[review_id] = rv
        self._append_log({"type": "review_disposition", "id": review_id, "decision": decision, "justification": justification, "approver": approver})
        return {"id": review_id, "decision": decision, "status": "closed"}

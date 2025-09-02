from __future__ import annotations
import re
from typing import List, Optional
from pydantic import BaseModel

# AAOCT: Actor, Action, Object, Condition, Time

ACTOR_PAT = re.compile(
    r'(?i)\b(?P<actor>(?:the\s+)?(?:Company|Supplier|Customer|Licensee|Licensor|Lender|Borrower|Service Provider|Party\s+[AB]|[A-Z][A-Za-z0-9&\-\s]{2,20}))\s+(?:shall|must|will)\b'
)
ACTION_PAT = re.compile(r'(?i)\b(?:shall|must|will)\s+(?P<action>[^.;:]+)')
COND_PAT = re.compile(r'(?i)\b(if|subject to|provided that|unless)\b(?P<cond>[^.;:]+)')
TIME_PAT = re.compile(r'(?i)\b(within\s+\d{1,3}\s+days?|no later than\s+[^.;:,]+|by\s+\w{3,}\.?\s+\d{1,2},?\s+\d{4}|on or before\s+[^.;:,]+)')

class AAOCT(BaseModel):
    actor: Optional[str] = None
    action: Optional[str] = None
    object: Optional[str] = None
    condition: Optional[str] = None
    time: Optional[str] = None
    sentence: str

class ObligationsService:
    def _sentences(self, text: str) -> List[str]:
        parts = re.split(r"(?<=[\.\?!])\s+", text.strip())
        return [p.strip() for p in parts if p.strip()]

    def _object_from_action(self, action: str) -> Optional[str]:
        # crude: take the noun phrase after action verb (first 8 words or until stop word)
        tokens = action.split()
        if not tokens:
            return None
        # skip first verb
        rest = tokens[1:] if len(tokens) > 1 else []
        stops = {"within", "by", "no", "if", "unless", "subject", "provided", "on"}
        obj_tokens = []
        for w in rest:
            if w.lower() in stops:
                break
            obj_tokens.append(w)
            if len(obj_tokens) >= 8:
                break
        return " ".join(obj_tokens).strip() or None

    def extract(self, text: str) -> List[AAOCT]:
        out: List[AAOCT] = []
        for sent in self._sentences(text):
            actor = None
            action = None
            condition = None
            time = None

            am = ACTOR_PAT.search(sent)
            if am:
                actor = am.group("actor").strip()

            acm = ACTION_PAT.search(sent)
            if acm:
                action = acm.group("action").strip()
            cm = COND_PAT.search(sent)
            if cm:
                condition = cm.group("cond").strip()
            tm = TIME_PAT.search(sent)
            if tm:
                time = tm.group(0).strip()

            if actor or action:
                obj = self._object_from_action(action or "")
                out.append(AAOCT(actor=actor, action=action, object=obj, condition=condition, time=time, sentence=sent))
        return out

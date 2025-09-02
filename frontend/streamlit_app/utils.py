from __future__ import annotations
import os, json, re, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
EXPORTS_DIR = Path("./exports")

# ---------- Session & Auth ----------

def init_session():
    st.session_state.setdefault("jwt", None)
    st.session_state.setdefault("role", "viewer")
    st.session_state.setdefault("username", "anon")
    st.session_state.setdefault("pii_redact", True)
    st.session_state.setdefault("last_parsing", None)

def login(username: str, password: str, role: str = "viewer") -> bool:
    url = f"{API_URL}/api/v1/auth/login"
    r = requests.post(url, json={"username": username, "password": password, "role": role})
    if r.ok:
        data = r.json()
        st.session_state["jwt"] = data.get("access_token")
        st.session_state["role"] = role
        st.session_state["username"] = username
        return True
    return False

def headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if st.session_state.get("jwt"):
        h["Authorization"] = f"Bearer {st.session_state['jwt']}"
    # role passthrough for simple RBAC
    if st.session_state.get("role"):
        h["X-User-Role"] = st.session_state["role"]
    return h

def role_badge():
    role = st.session_state.get("role", "viewer")
    color = {"admin":"red","legal":"green","risk":"orange","viewer":"blue"}.get(role,"blue")
    st.markdown(f"<span style='background-color:{color};color:white;padding:4px 8px;border-radius:6px;'>Role: {role}</span>", unsafe_allow_html=True)

# ---------- API helpers ----------

def api_post(path: str, payload: dict) -> dict:
    r = requests.post(f"{API_URL}{path}", headers=headers(), json=payload)
    if not r.ok:
        st.error(f"API error {r.status_code}: {r.text}")
        return {}
    return r.json()

def api_get(path: str) -> dict:
    r = requests.get(f"{API_URL}{path}", headers=headers())
    if not r.ok:
        st.error(f"API error {r.status_code}: {r.text}")
        return {}
    return r.json()

def api_delete(path: str) -> dict:
    r = requests.delete(f"{API_URL}{path}", headers=headers())
    if not r.ok:
        st.error(f"API error {r.status_code}: {r.text}")
        return {}
    return r.json()

# ---------- PII Redaction ----------

PII_PATS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b"),  # SSN-like
    re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}\b"),  # phone
    re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),  # credit card-ish
]

def mask_pii(text: str, enable: bool = True) -> str:
    if not enable:
        return text
    masked = text
    for p in PII_PATS:
        masked = p.sub("[REDACTED]", masked)
    return masked

def can_unmask() -> bool:
    return st.session_state.get("role") == "legal"

# ---------- Clustering / near-duplicates ----------

def cluster_similar(texts: List[str], threshold: float = 0.8) -> List[List[int]]:
    if not texts:
        return []
    vec = TfidfVectorizer(max_features=4096, ngram_range=(1,2))
    X = vec.fit_transform(texts)
    sims = cosine_similarity(X)
    n = len(texts)
    visited = set()
    clusters = []
    for i in range(n):
        if i in visited:
            continue
        group = [i]
        visited.add(i)
        for j in range(i+1, n):
            if j in visited:
                continue
            if sims[i, j] >= threshold:
                group.append(j)
                visited.add(j)
        clusters.append(group)
    return clusters

# ---------- File helpers ----------

def save_artifact(path: Path, bytes_data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes_data)

def timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")

# ---------- Convenience ----------

def code_block(label: str, payload: Any):
    import json as _json
    st.caption(label)
    st.code(_json.dumps(payload, indent=2, ensure_ascii=False))

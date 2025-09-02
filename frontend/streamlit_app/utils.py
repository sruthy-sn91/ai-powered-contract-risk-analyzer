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
    """
    Default JSON headers for simple GET/POST calls.
    NOTE: For multipart/form-data uploads, do NOT reuse this as-is;
    use the specialized helpers (they strip Content-Type).
    """
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
    st.markdown(
        f"<span style='background-color:{color};color:white;padding:4px 8px;border-radius:6px;'>Role: {role}</span>",
        unsafe_allow_html=True,
    )

# ---------- API helpers (generic) ----------

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

def api_post_list_with_params(path: str, items: list, params: dict | None = None) -> dict:
    """
    POST a JSON *array* body with optional query params.
    Example: api_post_list_with_params('/api/v1/exports/star_schema', contracts, {'save_csv': True, 'save_parquet': True})
    """
    url = f"{API_URL}{path}"
    h = headers()
    # ensure JSON content-type; headers() already has it
    r = requests.post(url, headers=h, json=items, params=params or {})
    if not r.ok:
        st.error(f"API error {r.status_code}: {r.text}")
        return {}
    return r.json()

# ---------- Parsing-specific helpers (fix 400/415) ----------

def _auth_header_only() -> Dict[str, str]:
    """Authorization + role only; no Content-Type (requests will set it)."""
    h = {}
    if st.session_state.get("jwt"):
        h["Authorization"] = f"Bearer {st.session_state['jwt']}"
    if st.session_state.get("role"):
        h["X-User-Role"] = st.session_state["role"]
    return h

def post_parsing(file=None, path: Optional[str] = None) -> dict:
    """
    Calls /api/v1/parsing-ocr/parse using the correct encoding:
      - if file is provided -> multipart/form-data
      - elif path is provided -> form field 'path'
    """
    url = f"{API_URL}/api/v1/parsing-ocr/parse"
    # IMPORTANT: do NOT set Content-Type manually for multipart/form-data or form data
    base_headers = _auth_header_only()

    if file is not None:
        # streamlit UploadedFile has .name, .type, .getbuffer()
        fname = getattr(file, "name", "upload")
        ftype = getattr(file, "type", None) or "application/octet-stream"
        files = {"file": (fname, file.getbuffer(), ftype)}
        r = requests.post(url, headers=base_headers, files=files, timeout=120)
        if not r.ok:
            st.error(f"API error {r.status_code}: {r.text}")
            return {}
        return r.json()

    if path:
        data = {"path": path}
        r = requests.post(url, headers=base_headers, data=data, timeout=60)
        if not r.ok:
            st.error(f"API error {r.status_code}: {r.text}")
            return {}
        return r.json()

    st.error("Provide either an uploaded file or a filesystem path.")
    return {}

def post_parsing_json_path(path: str) -> dict:
    """
    Calls /api/v1/parsing-ocr/parse_json with a JSON body {"path": "..."}.
    """
    url = f"{API_URL}/api/v1/parsing-ocr/parse_json"
    h = {"Content-Type": "application/json", **_auth_header_only()}
    r = requests.post(url, headers=h, json={"path": path}, timeout=60)
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

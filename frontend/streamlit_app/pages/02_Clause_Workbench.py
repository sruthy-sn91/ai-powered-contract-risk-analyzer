from __future__ import annotations
import streamlit as st
from frontend.streamlit_app.utils import api_post, role_badge, init_session, mask_pii, can_unmask, code_block

st.set_page_config(page_title="Clause Workbench", layout="wide")
init_session()
role_badge()
st.title("🧱 Clause Workbench")

src = st.radio("Source", ["From last parse", "Paste text"], horizontal=True)
text = ""
clauses = []

if src == "From last parse" and st.session_state.get("last_parsing"):
    text = st.session_state["last_parsing"]["normalized_text"]
    clauses = st.session_state["last_parsing"]["clauses"]
elif src == "Paste text":
    text = st.text_area("Contract text", height=200)

colA, colB = st.columns(2)

with colA:
    if st.button("Classify"):
        res = api_post("/api/v1/lora/classify", {"text": text[:2000]})
        if res:
            st.success(f"Label: **{res['label']}**  •  p={res['prob']:.2f}")
            for r in res.get("rationale_spans", []):
                st.write(f"- Rationale: `{r.get('text','')}`")

with colB:
    if st.button("Extract"):
        ext = api_post("/api/v1/extraction/extract", {"text": text, "clauses": clauses})
        if ext:
            st.json(ext)

st.divider()
st.subheader("PII Redaction")
redact = st.toggle("Redact PII (non-legal roles)", value=True)
st.text_area("Preview", value=mask_pii(text, redact and not can_unmask()), height=200)

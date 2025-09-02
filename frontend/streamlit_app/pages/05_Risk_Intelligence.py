from __future__ import annotations
import streamlit as st
from frontend.streamlit_app.utils import api_post, api_get, role_badge, init_session, code_block

st.set_page_config(page_title="Risk & Intelligence", layout="wide")
init_session()
role_badge()

st.title("🧠 Risk Intelligence")

text = st.text_area("Text", height=180, value="Termination for convenience by Customer. Unlimited liability applies. Service credits apply.")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Find Triggers"):
        t = api_post("/api/v1/intelligence/triggers", {"text": text})
        if t: st.json(t)

with col2:
    if st.button("Unusual Clauses"):
        clauses = [s.strip() for s in text.split(".") if s.strip()]
        u = api_post("/api/v1/intelligence/unusual", {"clauses": clauses})
        if u: st.json(u)

with col3:
    if st.button("Counterfactual Rewrite"):
        c = api_post("/api/v1/intelligence/counterfactual", {"text": text})
        if c: st.json(c)

st.divider()
st.subheader("Policy Simulator")
jur = st.selectbox("Jurisdiction", ["US-NY","EU","IN",""], index=0)
if st.button("Run Policy Check"):
    out = api_post("/api/v1/policy/check", {"text": text, "jurisdiction": jur})
    if out: st.json(out)

from __future__ import annotations
from pathlib import Path
import streamlit as st
from frontend.streamlit_app.utils import api_post, role_badge, init_session

st.set_page_config(page_title="Audit Activity", layout="wide")
init_session()
role_badge()

st.title("📜 Audit Activity")

col = st.columns(3)
with col[0]:
    rid = st.text_input("Review ID", value="R-1001")
with col[1]:
    assignee = st.text_input("Assignee", value="analyst1")
with col[2]:
    checklist = st.text_input("Checklist (comma-separated)", value="Liability,Governing Law")

if st.button("Create Review"):
    payload = {"id": rid, "assignee": assignee, "checklist": [c.strip() for c in checklist.split(",") if c.strip()]}
    st.json(api_post("/api/v1/governance/review/create", payload))

st.subheader("Comment")
c_author = st.text_input("Author", value="analyst1")
c_text = st.text_input("Comment", value="Flag unlimited liability")
if st.button("Add Comment"):
    st.json(api_post("/api/v1/governance/review/comment", {"review_id": rid, "author": c_author, "comment": c_text}))

st.subheader("Disposition")
decision = st.selectbox("Decision", ["accept","risk-accept","renegotiate","decline"], index=2)
just = st.text_input("Justification", value="Cap at 12 months fees")
approver = st.text_input("Approver", value="legal-head")
if st.button("Submit Disposition"):
    st.json(api_post("/api/v1/governance/review/disposition", {"review_id": rid, "decision": decision, "justification": just, "approver": approver}))

st.divider()
st.subheader("Audit Log")
log_path = Path("exports/audit.log")
if log_path.exists():
    lines = log_path.read_text(encoding="utf-8").splitlines()[-200:]
    st.text_area("audit.log (tail)", value="\n".join(lines), height=300)
else:
    st.info("No audit log yet. Perform some actions above.")

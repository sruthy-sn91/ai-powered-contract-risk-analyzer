from __future__ import annotations
import streamlit as st
from frontend.streamlit_app.utils import init_session, login, role_badge, API_URL

st.set_page_config(page_title="Contract Risk Analyzer", layout="wide")
init_session()

st.title("🧭 Contract Risk Analyzer — Home")

col1, col2 = st.columns([2,1])

with col1:
    st.markdown("Welcome! This is a local-only demo UI wired to the FastAPI backend.")
    st.markdown(f"- **API URL**: `{API_URL}`")
    st.markdown("- Use the sidebar to navigate 8 pages.")
    st.markdown("- Paths with spaces are supported (quote them).")

with col2:
    st.subheader("Login")
    username = st.text_input("Username", value=st.session_state.get("username",""))
    password = st.text_input("Password", type="password", value="")
    role = st.selectbox("Role", ["viewer","legal","risk","admin"], index=0)
    if st.button("Login / Refresh Token"):
        ok = login(username, password, role)
        if ok:
            st.success("Logged in.")
        else:
            st.error("Login failed.")
    role_badge()

st.divider()
st.subheader("Quick Links")
st.markdown("""
- 📄 **Upload & Analyze** → parse with OCR, segment clauses, detect meta
- 🧱 **Clause Workbench** → classify, extract, rationales
- 🔎 **Search & Compare** → filters, near-duplicates, saved queries & watchlists
- 💬 **Chat Assistant** → risk 'what-if' sliders
- 🧠 **Risk & Intelligence** → anomalies, rewrites, policy simulator
- 📊 **Portfolio Risk** → exports (CSV/Parquet), charts
- 🧰 **Policy Studio** → YAML edit + validate
- 📜 **Audit Activity** → review workbench & audit log
""")

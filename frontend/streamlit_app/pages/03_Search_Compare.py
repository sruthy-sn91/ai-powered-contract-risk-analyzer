from __future__ import annotations
import streamlit as st
from typing import List
from frontend.streamlit_app.utils import api_post, api_get, api_delete, role_badge, init_session, cluster_similar, code_block

st.set_page_config(page_title="Search & Compare", layout="wide")
init_session()
role_badge()

st.title("🔎 Search & Compare")

with st.form("search_form"):
    q = st.text_input("Query", value="Governing Law New York")
    k = st.slider("Top K", 5, 50, 10)
    colf = st.columns(5)
    with colf[0]:
        f_type = st.text_input("Type (e.g., MSA)")
    with colf[1]:
        f_bu = st.text_input("Business Unit")
    with colf[2]:
        f_jur = st.text_input("Jurisdiction")
    with colf[3]:
        f_date_from = st.text_input("Date From (YYYY-MM-DD)")
    with colf[4]:
        f_counterparty = st.text_input("Counterparty")
    submitted = st.form_submit_button("Search")

if submitted:
    filters = {k:v for k,v in {
        "type": f_type, "BU": f_bu, "jurisdiction": f_jur,
        "date_from": f_date_from, "counterparty": f_counterparty
    }.items() if v}
    res = api_post("/api/v1/retrieval/search", {"query": q, "k": k, "filters": filters})
    st.session_state["last_search"] = res

# Saved queries
st.divider()
col1, col2 = st.columns([2,1])
with col1:
    st.subheader("Saved Queries")
    sv = api_get("/api/v1/retrieval/saved_queries").get("saved_queries", {})
    if sv:
        st.json(sv)
with col2:
    name = st.text_input("Save as", value="")
    if st.button("Save Query"):
        payload = {"query": q, "k": k, "filters": filters}
        api_post("/api/v1/retrieval/saved_queries", {"name": name, **payload})
        st.experimental_rerun()

st.divider()
st.subheader("Results")
if st.session_state.get("last_search"):
    hits = st.session_state["last_search"]["hits"]
    st.write(f"{len(hits)} hits")
    st.dataframe(hits, use_container_width=True)

    texts = [h.get("snippet") or h.get("title") or h["doc_id"] for h in hits]
    clusters = cluster_similar(texts, threshold=0.75)
    with st.expander("Near-duplicate / Version Clusters"):
        for c in clusters:
            st.write("• " + ", ".join(hits[i]["doc_id"] for i in c))

    # Watchlists
    st.subheader("Watchlists")
    wdict = api_get("/api/v1/retrieval/watchlists").get("watchlists", {})
    st.json(wdict)
    wname = st.text_input("Create/Update Watchlist", value="")
    if st.button("Add all results to watchlist"):
        api_post("/api/v1/retrieval/watchlists", {"name": wname, "doc_ids": [h["doc_id"] for h in hits]})
        st.success("Saved.")
else:
    st.info("Run a search to see results.")

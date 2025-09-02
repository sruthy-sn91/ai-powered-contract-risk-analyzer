from __future__ import annotations
import streamlit as st
import pandas as pd
from frontend.streamlit_app.utils import api_post, role_badge, init_session

st.set_page_config(page_title="Portfolio Risk", layout="wide")
init_session()
role_badge()

st.title("📊 Portfolio Risk & Exports")

st.markdown("_Power BI placeholder_: Export star schema and connect your BI tool to the Parquet/CSV files under `./exports/`.")

sample = [{
    "contract_id":"C-1","counterparty":"Acme","bu":"default",
    "lens":{"legal":0.6,"operational":0.3,"regulatory":0.2,"counterparty":0.1,"financial":0.4},
    "composite":0.39
}]
if st.button("Export Star Schema (CSV/Parquet)"):
    res = api_post("/api/v1/exports/star_schema", {"rows": sample})
    if res:
        st.success(res)

# Simple chart
df = pd.DataFrame([{"lens":"legal","score":0.6},{"lens":"financial","score":0.4},{"lens":"operational","score":0.3},{"lens":"regulatory","score":0.2},{"lens":"counterparty","score":0.1}])
st.bar_chart(df.set_index("lens"))

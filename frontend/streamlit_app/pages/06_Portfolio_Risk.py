from __future__ import annotations
import streamlit as st
import pandas as pd

from frontend.streamlit_app.utils import (
    role_badge,
    init_session,
    api_post_list_with_params,  # new helper for list-body + query params
)

st.set_page_config(page_title="Portfolio Risk", layout="wide")
init_session()
role_badge()

st.title("📊 Portfolio Risk & Exports")
st.markdown(
    "_Power BI placeholder_: export a star schema and connect your BI tool to the "
    "Parquet/CSV files under `./exports/`."
)

# --------- Seed a small editable grid ----------
st.caption("Edit the rows below (add/remove as needed). Composite is optional.")
default_rows = [
    {
        "contract_id": "DEMO-001",
        "counterparty": "Acme Corp",
        "jurisdiction": "US-NY",
        "business_unit": "Default",
        "legal": 0.34,
        "operational": 0.10,
        "regulatory": 0.15,
        "counterparty_score": 0.08,
        "financial": 0.12,
        "composite": 0.18,
        "renewal_date": "2025-12-31",
    },
    {
        "contract_id": "DEMO-002",
        "counterparty": "Globex LLC",
        "jurisdiction": "UK",
        "business_unit": "Cloud",
        "legal": 0.22,
        "operational": 0.20,
        "regulatory": 0.10,
        "counterparty_score": 0.12,
        "financial": 0.18,
        "composite": 0.164,
        "renewal_date": "2026-03-31",
    },
]
df = st.data_editor(
    pd.DataFrame(default_rows),
    use_container_width=True,
    num_rows="dynamic",
    key="portfolio_grid",
)

colA, colB, colC = st.columns([1, 1, 2])

with colA:
    if st.button("Compute Composite = mean(lenses)"):
        # Compute simple mean across the 5 lenses
        if not df.empty:
            lens_cols = ["legal", "operational", "regulatory", "counterparty_score", "financial"]
            df["composite"] = df[lens_cols].mean(axis=1).round(3)
            st.session_state["portfolio_grid"] = df
            st.success("Composite recomputed.")

with colB:
    export_clicked = st.button("Export Star Schema (CSV & Parquet)")
    save_csv = True
    save_parquet = True

# --------- Build payload for API ---------
def build_contracts_payload(frame: pd.DataFrame) -> list[dict]:
    contracts: list[dict] = []
    if frame.empty:
        return contracts
    required_cols = {
        "contract_id",
        "counterparty",
        "jurisdiction",
        "business_unit",
        "legal",
        "operational",
        "regulatory",
        "counterparty_score",
        "financial",
        "renewal_date",
    }
    missing = required_cols - set(frame.columns)
    if missing:
        st.error(f"Missing required columns in table: {sorted(missing)}")
        return []

    for _, row in frame.iterrows():
        try:
            contracts.append(
                {
                    "contract_id": str(row["contract_id"]).strip(),
                    "counterparty": str(row["counterparty"]).strip(),
                    "jurisdiction": str(row["jurisdiction"]).strip(),
                    "business_unit": str(row["business_unit"]).strip(),
                    "risk_scores": {
                        "legal": float(row["legal"]),
                        "operational": float(row["operational"]),
                        "regulatory": float(row["regulatory"]),
                        "counterparty": float(row["counterparty_score"]),
                        "financial": float(row["financial"]),
                    },
                    # composite is optional; if NaN or empty, omit and let backend compute/ignore
                    **(
                        {"composite": float(row["composite"])}
                        if "composite" in row and pd.notna(row["composite"])
                        else {}
                    ),
                    "renewal_date": str(row["renewal_date"]).strip(),  # YYYY-MM-DD
                }
            )
        except Exception as e:
            st.error(f"Row build failed: {e}")
            return []
    return contracts

contracts = build_contracts_payload(df)

# --------- Call export API with proper shape ---------
if export_clicked:
    if not contracts:
        st.warning("Nothing to export — please add at least one valid row.")
    else:
        res = api_post_list_with_params(
            "/api/v1/exports/star_schema",
            items=contracts,  # <-- JSON array body
            params={"save_csv": save_csv, "save_parquet": save_parquet},  # <-- query params
        )
        if res:
            st.success("Exported star schema successfully.")
            st.json(res)

st.divider()
st.subheader("Lens Snapshot")
if not df.empty:
    # Aggregate by simple sum/mean for a quick view
    plot_df = pd.DataFrame(
        {
            "lens": ["legal", "financial", "operational", "regulatory", "counterparty"],
            "score": [
                df["legal"].mean() if "legal" in df else 0.0,
                df["financial"].mean() if "financial" in df else 0.0,
                df["operational"].mean() if "operational" in df else 0.0,
                df["regulatory"].mean() if "regulatory" in df else 0.0,
                df["counterparty_score"].mean() if "counterparty_score" in df else 0.0,
            ],
        }
    )
    st.bar_chart(plot_df.set_index("lens"))
else:
    st.info("Add rows above to see a chart.")

from __future__ import annotations
import streamlit as st
from frontend.streamlit_app.utils import api_post, role_badge, init_session

st.set_page_config(page_title="Chat Assistant", layout="wide")
init_session()
role_badge()

st.title("💬 Chat Assistant — What-if Risk")

st.subheader("Risk Score")
txt = st.text_area("Paste clause/contract text", height=150, value="This Agreement shall be governed by the laws of New York.")
if st.button("Score Risk"):
    out = api_post("/api/v1/risk/score", {"text": txt, "business_unit":"default"})
    if out:
        st.json(out)

st.subheader("Stress Test — Monte Carlo")
col = st.columns(3)
p_breach = col[0].slider("Probability of breach", 0.0, 1.0, 0.1, 0.01)
penalty = col[1].number_input("Penalty per breach", 1000.0, 10_000_000.0, 100000.0, 1000.0)
cap = col[2].number_input("Liability cap", 1000.0, 10_000_000.0, 250000.0, 1000.0)
col2 = st.columns(3)
uplift = col2[0].slider("Service credit uplift (-0.5..0.5)", -0.5, 0.5, 0.1, 0.05)
lam = col2[1].slider("Events λ", 0.0, 5.0, 0.5, 0.1)
sims = col2[2].slider("Simulations", 200, 10000, 2000, 200)
if st.button("Run Stress Test"):
    res = api_post("/api/v1/risk/stress", {
        "probability_of_breach": p_breach, "penalty_per_breach": penalty, "liability_cap": cap,
        "credit_uplift_pct": uplift, "num_events_lambda": lam, "simulations": sims
    })
    if res:
        st.json(res)

from __future__ import annotations
import subprocess, sys
from pathlib import Path
import streamlit as st
from frontend.streamlit_app.utils import role_badge, init_session

st.set_page_config(page_title="Policy Studio", layout="wide")
init_session()
role_badge()

st.title("🧰 Policy Studio")

policy_path = Path("policies/policy.example.yaml")
schema_path = Path("policies/schema.yaml")

text = ""
if policy_path.exists():
    text = policy_path.read_text(encoding="utf-8")

txt = st.text_area("Edit Policy YAML", value=text, height=300)
if st.button("Save Policy"):
    policy_path.write_text(txt, encoding="utf-8")
    st.success(f"Saved to {policy_path}")

if st.button("Validate Policy"):
    cmd = [sys.executable, "scripts/policy_validate.py", "--policy", str(policy_path), "--schema", str(schema_path)]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        st.success(out.strip())
    except subprocess.CalledProcessError as e:
        st.error(e.output)

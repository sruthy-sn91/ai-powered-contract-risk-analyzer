from __future__ import annotations
import io
import streamlit as st
from frontend.streamlit_app.utils import api_post, mask_pii, role_badge, init_session

st.set_page_config(page_title="Upload & Analyze", layout="wide")
init_session()
role_badge()

st.title("📄 Upload & Analyze")

tab1, tab2 = st.tabs(["Upload File", "Filesystem Path"])

with tab1:
    up = st.file_uploader("Upload PDF or DOCX", type=["pdf","docx"])
    if up and st.button("Parse"):
        resp = api_post("/api/v1/parsing-ocr/parse", {})
        # multipart not supported via simple helper; use requests directly:
        import requests
        url = st.secrets.get("API_URL", None) or "http://127.0.0.1:8000"
        r = requests.post(f"{url}/api/v1/parsing-ocr/parse", files={"file": up.getvalue()})
        if r.ok:
            data = r.json()
            st.session_state["last_parsing"] = data
        else:
            st.error(r.text)

with tab2:
    p = st.text_input("Filesystem path", value="")
    if st.button("Parse from Path"):
        data = api_post("/api/v1/parsing-ocr/parse", {"path": p})
        if data:
            st.session_state["last_parsing"] = data

st.divider()
if st.session_state.get("last_parsing"):
    data = st.session_state["last_parsing"]
    st.subheader("Detected Metadata")
    st.json(data.get("meta", {}))

    redact = st.toggle("Redact PII (viewer/risk). Legal can unmask.", value=st.session_state.get("pii_redact", True))
    st.session_state["pii_redact"] = redact
    st.caption("Per-page quality, OCR flag, rotation, tables & watermarks")

    for pg in data.get("pages", []):
        with st.expander(f"Page {pg['page_number']}  •  quality={pg['quality_score']}  •  OCR={pg['ocr_used']}  •  tables={pg['has_tables']}"):
            text = pg.get("text","")
            if redact and st.session_state.get("role") != "legal":
                text = mask_pii(text, True)
            st.text_area("Text", value=text, height=200, key=f"p{pg['page_number']}_text")

    st.subheader("Clause Segmentation")
    st.dataframe(data.get("clauses", []), use_container_width=True)
else:
    st.info("Upload a file or provide a path, then click Parse.")

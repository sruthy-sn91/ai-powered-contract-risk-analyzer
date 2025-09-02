from __future__ import annotations
import streamlit as st

from frontend.streamlit_app.utils import (
    init_session,
    role_badge,
    mask_pii,
    post_parsing,
    post_parsing_json_path,
)

st.set_page_config(page_title="Upload & Analyze", layout="wide")
init_session()
role_badge()

st.title("📄 Upload & Analyze")

tab1, tab2, tab3 = st.tabs(["Upload File", "Filesystem Path (form)", "Filesystem Path (JSON)"])

with tab1:
    up = st.file_uploader("Upload PDF, DOCX, or TXT", type=["pdf", "docx", "txt"])
    if st.button("Parse", key="parse_upload"):
        if up is None:
            st.warning("Please choose a file.")
        else:
            data = post_parsing(file=up)
            if data:
                st.session_state["last_parsing"] = data
                st.success("Parsed via multipart upload.")

with tab2:
    p_form = st.text_input("Absolute filesystem path (form-data)", value="")
    if st.button("Parse from Path (Form)", key="parse_form_path"):
        if not p_form.strip():
            st.warning("Please provide an absolute path.")
        else:
            data = post_parsing(path=p_form.strip())
            if data:
                st.session_state["last_parsing"] = data
                st.success("Parsed via form path.")

with tab3:
    p_json = st.text_input("Absolute filesystem path (JSON body)", value="")
    if st.button("Parse from Path (JSON)", key="parse_json_path"):
        if not p_json.strip():
            st.warning("Please provide an absolute path.")
        else:
            data = post_parsing_json_path(p_json.strip())
            if data:
                st.session_state["last_parsing"] = data
                st.success("Parsed via JSON path.")

st.divider()
if st.session_state.get("last_parsing"):
    data = st.session_state["last_parsing"]
    st.subheader("Detected Metadata")
    st.json(data.get("meta", {}))

    redact = st.toggle(
        "Redact PII (viewer/risk). Legal can unmask.",
        value=st.session_state.get("pii_redact", True),
    )
    st.session_state["pii_redact"] = redact
    st.caption("Per-page quality, OCR flag, rotation, tables & watermarks")

    for pg in data.get("pages", []):
        with st.expander(
            f"Page {pg['page_number']}  •  quality={pg['quality_score']}  •  OCR={pg['ocr_used']}  •  tables={pg['has_tables']}"
        ):
            text = pg.get("text", "")
            if redact and st.session_state.get("role") != "legal":
                text = mask_pii(text, True)
            st.text_area("Text", value=text, height=200, key=f"p{pg['page_number']}_text")

    st.subheader("Clause Segmentation")
    st.dataframe(data.get("clauses", []), use_container_width=True)
else:
    st.info("Upload a file or provide a path, then click Parse.")

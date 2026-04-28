"""DocBot — Local Intelligent Document Query POC."""

import streamlit as st

from ui.sidebar import render_sidebar
from ui.upload import get_ocr_reader, get_vectorstore, render_sample_loader, render_upload_ui

st.set_page_config(
    page_title="DocBot",
    page_icon="📄",
    layout="wide",
)

st.title("📄 DocBot")
st.caption("Local Intelligent Document Query")

vectorstore = get_vectorstore()
ocr_reader = get_ocr_reader()

render_sidebar(vectorstore)
render_upload_ui(vectorstore, ocr_reader)
render_sample_loader(vectorstore, ocr_reader)

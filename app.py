"""DocBot — Local Intelligent Document Query POC."""

import streamlit as st

from ui.chat import render_chat
from ui.graph_view import render_graph_view
from ui.sidebar import render_sidebar
from ui.summary_view import render_summary_view
from ui.upload import get_nim_client, get_ocr_reader, get_vectorstore, render_sample_loader, render_upload_ui

st.set_page_config(
    page_title="DocBot",
    page_icon="📄",
    layout="wide",
)

st.title("📄 DocBot")
st.caption("Local Intelligent Document Query")

vectorstore = get_vectorstore()
ocr_reader = get_ocr_reader()
nim_client = get_nim_client()

render_sidebar(vectorstore)
render_upload_ui(vectorstore, ocr_reader)
render_sample_loader(vectorstore, ocr_reader)

chat_tab, summary_tab, graph_tab = st.tabs(["💬 Chat", "📝 Summary", "🕸️ Graph"])

with chat_tab:
    render_chat(vectorstore, nim_client)

with summary_tab:
    render_summary_view(vectorstore, nim_client)

with graph_tab:
    render_graph_view(vectorstore, nim_client)

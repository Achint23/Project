"""Sidebar with document list and delete functionality."""

from __future__ import annotations

import streamlit as st

from pipelines.ingest import delete_document


def _init_documents():
    """Ensure session_state.documents list exists."""
    if "documents" not in st.session_state:
        st.session_state.documents = []


def render_sidebar(vectorstore):
    """Render sidebar with indexed document list and delete buttons."""
    _init_documents()

    with st.sidebar:
        st.header("📑 Documents")

        if not st.session_state.documents:
            st.info("No documents indexed yet.")
            return

        for doc in st.session_state.documents:
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{doc['filename']}**")
            col1.caption(f"{doc['chunk_count']} chunks")
            if col2.button("🗑️", key=f"del_{doc['doc_id']}"):
                delete_document(doc["doc_id"], vectorstore)
                st.session_state.documents = [
                    d for d in st.session_state.documents if d["doc_id"] != doc["doc_id"]
                ]
                st.rerun()

"""Sidebar with document list, delete functionality, and model routing toggle."""

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

        st.divider()
        st.subheader("🔀 Model Routing")
        st.radio(
            "Model selection",
            options=["auto", "small (route)", "large (direct)"],
            index=0,
            key="model_routing_mode",
            help="**auto**: router picks model by task type and doc size. "
            "**small**: always use the faster route model. "
            "**large**: always use the large direct model.",
        )

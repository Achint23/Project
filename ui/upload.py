"""Upload UI and cached resource singletons for Streamlit."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from pipelines.ingest import (
    compute_content_hash,
    ingest_document,
    save_upload,
)


@st.cache_resource
def get_nim_client():
    """Return a cached NIMClient singleton."""
    from core.config import get_settings
    from core.llm_client import NIMClient

    return NIMClient(get_settings())


@st.cache_resource
def get_ocr_reader():
    """Return a cached OCRReader singleton."""
    from core.ocr import OCRReader

    return OCRReader(languages=["en"])


@st.cache_resource
def get_vectorstore():
    """Return a cached VectorStore singleton with model validation."""
    from core.embedder import Embedder
    from core.vectorstore import VectorStore

    embedder = Embedder(nim_client=get_nim_client())
    vs = VectorStore(persist_path="data/chroma", embedder=embedder)
    vs.validate_model()
    return vs


def _init_documents():
    """Ensure session_state.documents list exists, restoring from ChromaDB if needed."""
    if "documents" not in st.session_state:
        st.session_state.documents = []


def _restore_documents_from_store(vectorstore):
    """On first run, scan ChromaDB for previously indexed documents."""
    if st.session_state.get("_docs_restored"):
        return
    if not st.session_state.documents:
        existing = vectorstore.list_documents()
        if existing:
            st.session_state.documents = existing
    st.session_state._docs_restored = True


def render_upload_ui(vectorstore, ocr_reader):
    """Render the PDF upload widget with progress tracking."""
    _init_documents()
    _restore_documents_from_store(vectorstore)

    uploaded = st.file_uploader("Upload a PDF document", type=["pdf"], key="doc_upload")
    if uploaded is None:
        return

    file_bytes = uploaded.getvalue()
    doc_id = compute_content_hash(file_bytes)

    # Check session-level dedupe
    known_ids = {d["doc_id"] for d in st.session_state.documents}
    if doc_id in known_ids:
        st.info(f"**{uploaded.name}** is already indexed.")
        return

    # Save and ingest with progress
    with st.status("Processing document...", expanded=True) as status:
        st.write("💾 Saving upload...")
        file_path = save_upload(file_bytes, doc_id)

        st.write("📄 Extracting text and tables...")
        st.write("🔪 Chunking content...")
        st.write("📊 Embedding and indexing...")

        result = ingest_document(file_path, doc_id, uploaded.name, vectorstore, ocr_reader)

        if result.error:
            status.update(label="Error!", state="error")
            st.error(result.error)
            return

        if result.already_indexed:
            status.update(label="Already indexed", state="complete")
            st.info(f"**{uploaded.name}** was already indexed.")
            st.session_state.documents.append(
                {"doc_id": doc_id, "filename": uploaded.name, "chunk_count": 0}
            )
            return

        status.update(label="Done!", state="complete")

    st.success(
        f"**{uploaded.name}** indexed: {result.page_count} pages, {result.chunk_count} chunks."
    )
    st.session_state.documents.append(
        {"doc_id": doc_id, "filename": uploaded.name, "chunk_count": result.chunk_count}
    )
    st.rerun()


def render_sample_loader(vectorstore, ocr_reader):
    """Render one-click loader for bundled sample PDFs."""
    _init_documents()

    samples_dir = Path("data/samples")
    if not samples_dir.exists():
        return

    pdf_files = sorted(samples_dir.glob("*.pdf"))
    if not pdf_files:
        return

    st.subheader("📚 Sample Documents")
    known_ids = {d["doc_id"] for d in st.session_state.documents}

    for pdf_path in pdf_files:
        col1, col2 = st.columns([3, 1])
        col1.write(pdf_path.name)
        if col2.button("Load", key=f"sample_{pdf_path.name}"):
            file_bytes = pdf_path.read_bytes()
            doc_id = compute_content_hash(file_bytes)

            if doc_id in known_ids:
                st.info(f"**{pdf_path.name}** is already indexed.")
                continue

            with st.status(f"Loading {pdf_path.name}...", expanded=True) as status:
                st.write("📄 Extracting text and tables...")
                st.write("🔪 Chunking content...")
                st.write("📊 Embedding and indexing...")

                file_on_disk = save_upload(file_bytes, doc_id)
                result = ingest_document(
                    file_on_disk, doc_id, pdf_path.name, vectorstore, ocr_reader
                )

                if result.error:
                    status.update(label="Error!", state="error")
                    st.error(result.error)
                    continue

                status.update(label="Done!", state="complete")

            st.success(
                f"**{pdf_path.name}** indexed: {result.page_count} pages, {result.chunk_count} chunks."
            )
            st.session_state.documents.append(
                {
                    "doc_id": doc_id,
                    "filename": pdf_path.name,
                    "chunk_count": result.chunk_count,
                }
            )
            st.rerun()

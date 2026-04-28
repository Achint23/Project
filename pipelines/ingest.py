"""Ingestion pipeline: hash, dedupe, extract, chunk, embed, persist."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from core.chunker import chunk_document
from core.extractor import extract_document

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    """Result of an ingestion operation."""

    doc_id: str
    filename: str
    chunk_count: int
    page_count: int
    already_indexed: bool = False
    error: str | None = None


def compute_content_hash(file_bytes: bytes) -> str:
    """Return SHA-256 hex digest of file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


def save_upload(file_bytes: bytes, doc_id: str, upload_dir: str = "data/uploads") -> Path:
    """Save uploaded file bytes to disk using doc_id as filename.

    Args:
        file_bytes: Raw file content.
        doc_id: Content hash used as filename (hex-safe).
        upload_dir: Directory to save into.

    Returns:
        Path to the saved file.
    """
    dest = Path(upload_dir) / f"{doc_id}.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file_bytes)
    return dest


def is_already_indexed(vectorstore, doc_id: str) -> bool:
    """Check whether a document is already in the vector store."""
    results = vectorstore._collection.get(where={"doc_id": doc_id}, limit=1)
    return len(results["ids"]) > 0


def ingest_document(file_path, doc_id: str, filename: str, vectorstore, ocr_reader=None) -> IngestResult:
    """Run the full ingest pipeline for a single document.

    Args:
        file_path: Path to the PDF on disk.
        doc_id: Content-hash identifier.
        filename: Original filename for display.
        vectorstore: VectorStore instance.
        ocr_reader: Optional OCRReader for scanned pages.

    Returns:
        IngestResult with counts or error.
    """
    try:
        if is_already_indexed(vectorstore, doc_id):
            return IngestResult(
                doc_id=doc_id,
                filename=filename,
                chunk_count=0,
                page_count=0,
                already_indexed=True,
            )

        pages = extract_document(str(file_path), ocr_reader)
        chunks = chunk_document(pages, doc_id)
        vectorstore.add(chunks, doc_id)

        page_count = len({p["page_num"] for p in pages})
        return IngestResult(
            doc_id=doc_id,
            filename=filename,
            chunk_count=len(chunks),
            page_count=page_count,
        )
    except Exception as e:
        logger.exception("Ingest failed for %s", filename)
        return IngestResult(
            doc_id=doc_id,
            filename=filename,
            chunk_count=0,
            page_count=0,
            error=str(e),
        )


def delete_document(doc_id: str, vectorstore, upload_dir: str = "data/uploads") -> None:
    """Remove a document's vectors and uploaded file.

    Args:
        doc_id: Content-hash identifier.
        vectorstore: VectorStore instance.
        upload_dir: Directory where uploads are stored.
    """
    vectorstore.delete_by_doc(doc_id)
    upload_path = Path(upload_dir) / f"{doc_id}.pdf"
    if upload_path.exists():
        upload_path.unlink()

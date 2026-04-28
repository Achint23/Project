"""PDF text extraction with table detection and OCR routing."""

import logging

import pymupdf

logger = logging.getLogger(__name__)


def extract_tables(page) -> list[dict]:
    """Extract tables from a page as markdown chunks."""
    tables = []
    try:
        found = page.find_tables()
        for idx, table in enumerate(found.tables):
            md = table.to_markdown()
            tables.append(
                {
                    "text": md,
                    "chunk_type": "table",
                    "page_num": page.number + 1,
                    "table_index": idx,
                }
            )
    except Exception:
        logger.debug("Table extraction failed on page %d", page.number + 1)
    return tables


def extract_pages(pdf_path: str) -> list[dict]:
    """Extract text and tables from each page of a PDF.

    Returns a list of dicts with keys: page_num, text, needs_ocr, chunk_type.
    Tables are returned as separate items with chunk_type='table'.
    """
    results: list[dict] = []
    doc = pymupdf.open(pdf_path)
    try:
        for page in doc:
            # Extract tables first
            tables = extract_tables(page)
            results.extend(tables)

            # Extract text with reading-order sort
            text = page.get_text("text", sort=True)
            needs_ocr = len(text.strip()) < 50

            results.append(
                {
                    "page_num": page.number + 1,
                    "text": text,
                    "needs_ocr": needs_ocr,
                    "chunk_type": "text",
                }
            )
    finally:
        doc.close()
    return results


def extract_document(pdf_path: str, ocr_reader=None) -> list[dict]:
    """Full extraction pipeline: text + tables + OCR fallback.

    Args:
        pdf_path: Path to the PDF file.
        ocr_reader: Optional OCRReader instance for scanned pages.

    Returns:
        Flat list of content dicts with keys: text, chunk_type, page_num.
    """
    pages = extract_pages(pdf_path)
    if ocr_reader is None:
        # No OCR reader — just warn about pages needing OCR
        for p in pages:
            if p.get("needs_ocr") and p["chunk_type"] == "text":
                logger.warning(
                    "Page %d has <50 chars but no OCR reader provided; skipping OCR",
                    p["page_num"],
                )
        return pages

    # Re-open doc for OCR rendering on pages that need it
    from core.ocr import ocr_page

    doc = pymupdf.open(pdf_path)
    try:
        for item in pages:
            if item.get("needs_ocr") and item["chunk_type"] == "text":
                page_idx = item["page_num"] - 1
                page = doc[page_idx]
                ocr_text = ocr_page(page, ocr_reader)
                if ocr_text.strip():
                    item["text"] = ocr_text
                    item["chunk_type"] = "ocr"
    finally:
        doc.close()

    return pages

"""Unit tests for core/extractor.py."""

from unittest.mock import MagicMock, patch

from core.extractor import extract_document, extract_pages, extract_tables


class TestExtractTables:
    def test_extract_tables_returns_markdown(self):
        """Tables are emitted as markdown with chunk_type='table'."""
        mock_table = MagicMock()
        mock_table.to_markdown.return_value = "| A | B |\n|---|---|\n| 1 | 2 |"

        mock_tables_result = MagicMock()
        mock_tables_result.tables = [mock_table]

        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.find_tables.return_value = mock_tables_result

        result = extract_tables(mock_page)
        assert len(result) == 1
        assert result[0]["chunk_type"] == "table"
        assert result[0]["page_num"] == 1
        assert "| A | B |" in result[0]["text"]


class TestExtractPages:
    @patch("core.extractor.pymupdf")
    def test_digital_pdf_no_ocr_needed(self, mock_pymupdf):
        """Pages with >50 chars have needs_ocr=False."""
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.get_text.return_value = "A" * 100
        mock_page.find_tables.return_value = MagicMock(tables=[])

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_pymupdf.open.return_value = mock_doc

        result = extract_pages("fake.pdf")
        text_pages = [r for r in result if r["chunk_type"] == "text"]
        assert len(text_pages) == 1
        assert text_pages[0]["needs_ocr"] is False

    @patch("core.extractor.pymupdf")
    def test_scanned_pdf_needs_ocr(self, mock_pymupdf):
        """Pages with <50 chars have needs_ocr=True."""
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.get_text.return_value = "short"
        mock_page.find_tables.return_value = MagicMock(tables=[])

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_pymupdf.open.return_value = mock_doc

        result = extract_pages("fake.pdf")
        text_pages = [r for r in result if r["chunk_type"] == "text"]
        assert len(text_pages) == 1
        assert text_pages[0]["needs_ocr"] is True

    @patch("core.extractor.pymupdf")
    def test_extract_pages_includes_tables(self, mock_pymupdf):
        """Tables are returned alongside text content."""
        mock_table = MagicMock()
        mock_table.to_markdown.return_value = "| Col |"

        mock_tables_result = MagicMock()
        mock_tables_result.tables = [mock_table]

        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.get_text.return_value = "Some text content here that is long enough"
        mock_page.find_tables.return_value = mock_tables_result

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_pymupdf.open.return_value = mock_doc

        result = extract_pages("fake.pdf")
        types = [r["chunk_type"] for r in result]
        assert "table" in types
        assert "text" in types


class TestExtractDocument:
    @patch("core.extractor.pymupdf")
    def test_no_ocr_reader_skips_gracefully(self, mock_pymupdf):
        """Without an OCR reader, scanned pages are kept with original text."""
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.get_text.return_value = "x"
        mock_page.find_tables.return_value = MagicMock(tables=[])

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_pymupdf.open.return_value = mock_doc

        result = extract_document("fake.pdf", ocr_reader=None)
        assert len(result) >= 1
        text_pages = [r for r in result if r.get("needs_ocr")]
        assert len(text_pages) == 1
        # chunk_type stays "text" since no OCR was performed
        assert text_pages[0]["chunk_type"] == "text"

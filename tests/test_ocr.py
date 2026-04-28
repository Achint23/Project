"""Unit tests for core/ocr.py."""

from unittest.mock import MagicMock, patch

from core.ocr import OCRReader, ocr_page


class TestOCRReader:
    def test_lazy_init(self):
        """Reader is not instantiated until first access."""
        reader = OCRReader()
        assert reader._reader is None

    @patch("easyocr.Reader")
    def test_reader_creates_on_access(self, mock_reader_cls):
        """Accessing .reader triggers EasyOCR Reader creation."""
        mock_reader_cls.return_value = MagicMock()
        reader = OCRReader(languages=["en"])
        _ = reader.reader
        mock_reader_cls.assert_called_once_with(["en"], gpu=False)
        assert reader._reader is not None


class TestOcrPage:
    def test_ocr_page_calls_readtext(self):
        """ocr_page renders pixmap and calls readtext."""
        mock_pix = MagicMock()
        mock_pix.samples = b"\x00" * (100 * 50 * 3)
        mock_pix.height = 50
        mock_pix.width = 100
        mock_pix.n = 3

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_easyocr_reader = MagicMock()
        mock_easyocr_reader.readtext.return_value = ["Hello", "World"]

        mock_reader = MagicMock(spec=OCRReader)
        mock_reader.reader = mock_easyocr_reader

        result = ocr_page(mock_page, mock_reader)
        mock_page.get_pixmap.assert_called_once_with(dpi=200)
        mock_easyocr_reader.readtext.assert_called_once()
        assert result == "Hello\nWorld"

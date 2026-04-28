"""EasyOCR wrapper with lazy initialization."""

import numpy as np


class OCRReader:
    """Lazy wrapper around EasyOCR Reader."""

    def __init__(self, languages=None):
        self.languages = languages or ["en"]
        self._reader = None

    def _get_reader(self):
        """Lazily create EasyOCR Reader on first access."""
        if self._reader is None:
            import easyocr

            self._reader = easyocr.Reader(self.languages, gpu=False)
        return self._reader

    @property
    def reader(self):
        """Return the underlying EasyOCR Reader instance."""
        return self._get_reader()


def ocr_page(page, reader: OCRReader) -> str:
    """OCR a PyMuPDF page using EasyOCR.

    Args:
        page: A pymupdf page object.
        reader: An OCRReader instance.

    Returns:
        Extracted text as a single string with lines joined by newlines.
    """
    pix = page.get_pixmap(dpi=200)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n
    )
    results = reader.reader.readtext(img, detail=0, paragraph=True)
    return "\n".join(results)

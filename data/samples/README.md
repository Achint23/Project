# Sample Documents

Bundled sample PDFs for one-click demo loading via the DocBot UI.

## Purpose

These files let a demo audience see DocBot in action without needing their own documents. The sample loader in the UI reads `data/samples/*.pdf` and offers a "Load" button for each.

## Expected files

| File | Type | Notes |
|------|------|-------|
| `digital.pdf` | Digital text PDF | Clean text extraction via PyMuPDF |
| `scanned.pdf` | Scanned/image PDF | Triggers OCR fallback (<50 chars heuristic) |
| `tables.pdf` | Table-heavy PDF | Tests atomic table chunk extraction |

## Adding samples

Place any PDF file in this directory. Requirements:
- Keep files small (<5 pages, <2 MB each) for fast demo loading.
- Ensure content is public domain or you have rights to distribute.
- The UI auto-discovers all `*.pdf` files in this directory.

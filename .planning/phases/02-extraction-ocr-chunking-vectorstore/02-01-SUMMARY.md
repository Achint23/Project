---
phase: 02-extraction-ocr-chunking-vectorstore
plan: 01
subsystem: extraction
tags: [pymupdf, easyocr, ocr, pdf, tables]

requires:
  - phase: 01-skeleton-nim-client
    provides: "Project scaffold, pyproject.toml, tasks.ps1, core/config.py"
provides:
  - "PDF text extraction with reading-order sort and table detection"
  - "OCR fallback routing via <50 chars heuristic"
  - "EasyOCR lazy wrapper with pre-download in setup"
affects: [02-02-chunker, 02-03-embedder-vectorstore, 03-ingestion-pipeline]

tech-stack:
  added: [pymupdf, easyocr, chromadb, tiktoken, onnxruntime]
  patterns: [lazy-initialization for heavy resources, OCR threshold routing]

key-files:
  created: [core/extractor.py, core/ocr.py, tests/test_extractor.py, tests/test_ocr.py]
  modified: [pyproject.toml, tasks.ps1]

key-decisions:
  - "Pinned onnxruntime<1.24 for Python 3.10 compatibility (1.24+ dropped cp310 wheels)"
  - "Lazy EasyOCR init via property — avoids 2GB load until first OCR page"
  - "extract_document re-opens PDF for OCR rendering (extract_pages returns text only)"

patterns-established:
  - "Lazy init pattern: OCRReader._reader created on first .reader access"
  - "OCR threshold: <50 chars triggers OCR fallback"
  - "Table extraction: atomic markdown chunks with chunk_type='table'"

requirements-completed: [SETUP-04, INGEST-02, INGEST-03]

duration: 8min
completed: 2026-04-28
---

# Phase 2 Plan 01: Dependencies, PDF Extraction & OCR Summary

**PyMuPDF text+table extraction with EasyOCR fallback routing and all Phase 2 dependencies installed**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-28
- **Completed:** 2026-04-28
- **Tasks:** 3/3
- **Files modified:** 6

## Accomplishments
- All Phase 2 dependencies added (pymupdf, easyocr, chromadb, tiktoken) with onnxruntime pinned for Python 3.10
- PDF extraction module with table detection (find_tables + to_markdown) and reading-order text sort
- OCR threshold routing: pages with <50 chars auto-flag for EasyOCR fallback
- EasyOCR weight pre-download wired into `tasks.ps1 setup`
- 8 unit tests passing (4 extractor + 3 OCR + 1 table test)

## Task Commits

1. **Task 1: Add Phase 2 dependencies and EasyOCR pre-download** - `9497ebd` (feat)
2. **Task 2: Create core/extractor.py** - `db315b8` (feat)
3. **Task 3: Create core/ocr.py and unit tests** - `02d04cb` (feat)

## Files Created/Modified
- `pyproject.toml` - Added pymupdf, easyocr, chromadb, tiktoken, onnxruntime pin
- `tasks.ps1` - EasyOCR weight pre-download in Invoke-Setup
- `core/extractor.py` - extract_tables, extract_pages, extract_document
- `core/ocr.py` - OCRReader (lazy), ocr_page
- `tests/test_extractor.py` - 4 tests (digital/scanned/tables/no-ocr-reader)
- `tests/test_ocr.py` - 3 tests (lazy init, reader creation, readtext call)

## Decisions Made
- Pinned `onnxruntime>=1.17,<1.24` because v1.24.3 dropped Python 3.10 wheel support

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] onnxruntime 1.24.3 incompatible with Python 3.10**
- **Found during:** Task 1 (Add Phase 2 dependencies)
- **Issue:** `uv sync` failed — onnxruntime 1.24.3 has no cp310 wheel
- **Fix:** Added `onnxruntime>=1.17,<1.24` to pyproject.toml dependencies
- **Files modified:** pyproject.toml
- **Verification:** `uv sync` succeeded, all imports OK
- **Committed in:** `9497ebd`

---

**Total deviations:** 1 auto-fixed (Rule 3)
**Impact on plan:** Necessary for installation correctness. No scope creep.

## Issues Encountered
None beyond the onnxruntime pin.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `core/extractor.py` output format (list of dicts with text, chunk_type, page_num) is the input contract for Plan 02-02 (chunker)
- `core/ocr.py` OCRReader is available for lazy injection into extract_document
- All Phase 2 deps installed and importable

## Self-Check: PASSED

---
*Phase: 02-extraction-ocr-chunking-vectorstore*
*Completed: 2026-04-28*

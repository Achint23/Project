---
phase: 03-ingestion-pipeline-upload-ui
plan: 01
subsystem: pipelines
tags: [ingest, sha256, dedupe, extract, chunk, vectorstore]

requires:
  - phase: 02-extraction-ocr-chunking-vectorstore
    provides: extract_document, chunk_document, VectorStore.add/delete_by_doc, OCRReader
provides:
  - "pipelines/ingest.py with ingest_document, delete_document, compute_content_hash, save_upload, is_already_indexed, IngestResult"
affects: [03-02-upload-ui, 04-qa-retrieval]

tech-stack:
  added: []
  patterns: ["Content-hash (SHA-256) as doc_id — never user-supplied filenames in paths", "IngestResult dataclass for pipeline return values with error field"]

key-files:
  created: [pipelines/__init__.py, pipelines/ingest.py, tests/test_ingest_pipeline.py]
  modified: []

key-decisions:
  - "SHA-256 content hash as doc_id and on-disk filename to prevent path traversal and ensure idempotent re-uploads"
  - "IngestResult dataclass with error field instead of raising exceptions — callers get structured results"
  - "is_already_indexed uses vectorstore._collection.get for direct ChromaDB check"

patterns-established:
  - "Pipeline pattern: compose core modules via function orchestration, not classes"
  - "Error containment: catch Exception in pipeline, log with logger.exception, return error in result dataclass"

requirements-completed: [INGEST-01, INGEST-05, INGEST-06, IDX-06]

duration: 5min
completed: 2026-04-28
---

# Phase 3 Plan 01: Ingest Pipeline Module Summary

**Content-hash dedupe ingest pipeline composing extract/chunk/persist with structured error handling**

## Performance

- **Tasks:** 2/2
- **Files created:** 3

## Accomplishments

- Created `pipelines/ingest.py` with 6 exported functions/classes: `IngestResult`, `compute_content_hash`, `save_upload`, `is_already_indexed`, `ingest_document`, `delete_document`
- Full unit test coverage: 11 tests covering happy path, dedupe, error handling, and delete flows
- Zero Streamlit imports — pure Python module, fully unit-testable

## Task Commits

1. **Task 1: Create pipelines package with ingest module** — `4b3d76f` (feat)
2. **Task 2: Unit tests for ingest pipeline** — `e4d383f` (test)

## Files Created/Modified

- `pipelines/__init__.py` — Package marker
- `pipelines/ingest.py` — Ingest pipeline: hash → dedupe → extract → chunk → persist, plus delete
- `tests/test_ingest_pipeline.py` — 11 unit tests with mocks

## Decisions Made

- Used SHA-256 hex digest as doc_id and disk filename (T-03-01 mitigation)
- Pipeline functions are standalone (not a class) for simplicity and composability

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

---
phase: 03-ingestion-pipeline-upload-ui
plan: 03
subsystem: config
tags: [samples, streamlit-config, idx-05, doc-id-filter]

requires:
  - phase: 02-extraction-ocr-chunking-vectorstore
    provides: VectorStore.query with doc_id filter
provides:
  - "data/samples/ directory with README for bundled demo PDFs"
  - ".streamlit/config.toml with maxUploadSize=50 and telemetry off"
  - "IDX-05 doc_id filter test in test_vectorstore.py"
affects: [03-02-upload-ui, 07-demo-polish]

tech-stack:
  added: []
  patterns: ["Streamlit config.toml for server settings"]

key-files:
  created: [data/samples/README.md, data/samples/.gitkeep, .streamlit/config.toml]
  modified: [tests/test_vectorstore.py]

key-decisions:
  - "maxUploadSize=50 MB — reasonable for POC PDFs, mitigates T-03-07 DoS"
  - "gatherUsageStats=false — disables Streamlit telemetry for local-only POC"
  - "Sample PDFs not generated — README documents expected files, .gitkeep ensures dir is tracked"

patterns-established: []

requirements-completed: [INGEST-04, IDX-05]

duration: 3min
completed: 2026-04-28
---

# Phase 3 Plan 03: Sample Docs, IDX-05 Test & Streamlit Config Summary

**Bundled sample docs directory, Streamlit upload-size config, and doc_id filter test for IDX-05**

## Performance

- **Tasks:** 2/2
- **Files created:** 3
- **Files modified:** 1

## Accomplishments

- Created `data/samples/` directory with README documenting expected sample PDFs and .gitkeep
- Created `.streamlit/config.toml` with 50MB upload limit and telemetry disabled
- Added 2 IDX-05 tests: doc_id filter returns only matching docs, no filter returns mixed results
- Full test suite at 48 tests passing

## Task Commits

1. **Task 1: Create sample documents and Streamlit config** — `153be3d` (chore)
2. **Task 2: Add IDX-05 doc_id filter test** — `d792566` (test)

## Files Created/Modified

- `data/samples/README.md` — Documents expected sample files and how to add them
- `data/samples/.gitkeep` — Ensures empty dir is tracked
- `.streamlit/config.toml` — maxUploadSize=50, gatherUsageStats=false
- `tests/test_vectorstore.py` — Added TestVectorStoreDocIdFilter with 2 tests

## Decisions Made

- README placeholder instead of generating synthetic PDFs — real samples should be sourced with appropriate rights
- maxUploadSize=50 caps upload to prevent DoS (T-03-07)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

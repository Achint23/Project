---
phase: 03-ingestion-pipeline-upload-ui
plan: 02
subsystem: ui
tags: [streamlit, cache_resource, upload, sidebar, singleton]

requires:
  - phase: 03-ingestion-pipeline-upload-ui
    provides: pipelines/ingest.py (ingest_document, delete_document, compute_content_hash, save_upload)
provides:
  - "ui/upload.py with get_nim_client, get_ocr_reader, get_vectorstore singletons and render_upload_ui, render_sample_loader"
  - "ui/sidebar.py with render_sidebar showing document list and delete"
  - "app.py wired as composition root"
affects: [04-qa-retrieval, 05-summarization, 06-routing, 07-demo-polish]

tech-stack:
  added: []
  patterns: ["@st.cache_resource for heavy singletons (NIMClient, OCRReader, VectorStore)", "session_state.documents list for cross-rerun doc tracking", "st.status for multi-stage progress display"]

key-files:
  created: [ui/__init__.py, ui/upload.py, ui/sidebar.py]
  modified: [app.py]

key-decisions:
  - "@st.cache_resource for all heavy resources — survives Streamlit reruns without re-instantiation"
  - "Session-state document list (not persistent manifest) — simple for POC, populated on upload"
  - "Content-hash as doc_id flows from upload through to sidebar delete — never user-supplied filenames"

patterns-established:
  - "Singleton pattern: @st.cache_resource with lazy imports inside factory functions"
  - "Composition root pattern: app.py imports and calls view functions, no business logic"
  - "Progress pattern: st.status with expanded=True for multi-stage operations"

requirements-completed: [INGEST-01, INGEST-04, INGEST-06, UX-03]

duration: 5min
completed: 2026-04-28
---

# Phase 3 Plan 02: Streamlit Upload UI & Sidebar Summary

**Upload UI with @st.cache_resource singletons, st.status progress, sidebar document list with delete**

## Performance

- **Tasks:** 2/2
- **Files created:** 3
- **Files modified:** 1

## Accomplishments

- Created `@st.cache_resource` singletons for NIMClient, OCRReader, and VectorStore — zero re-instantiation on Streamlit reruns
- Upload UI with st.file_uploader, progress tracking via st.status, and session-level dedupe
- Sample loader auto-discovers data/samples/*.pdf with one-click "Load" buttons
- Sidebar renders indexed document list with chunk counts and delete functionality
- app.py wired as thin composition root

## Task Commits

1. **Task 1: Create @st.cache_resource singletons and upload UI** — `56a0ea4` (feat)
2. **Task 2: Create sidebar and wire app.py** — `ce329cd` (feat)

## Files Created/Modified

- `ui/__init__.py` — Package marker
- `ui/upload.py` — Singletons (get_nim_client, get_ocr_reader, get_vectorstore) + render_upload_ui + render_sample_loader
- `ui/sidebar.py` — render_sidebar with document list and delete buttons
- `app.py` — Composition root wiring upload + sidebar + sample loader

## Decisions Made

- Lazy imports inside @st.cache_resource factories to avoid circular imports
- session_state.documents as simple list (not persistent) — acceptable for POC

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

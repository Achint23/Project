---
phase: "05"
plan: "03"
subsystem: ui
tags: [summary-view, graph-view, streamlit-tabs, agraph, mermaid, ui-partials]
dependency_graph:
  requires: [pipelines/summarize, pipelines/graph, ui/chat, ui/upload, streamlit-agraph]
  provides: [ui/summary_view, ui/graph_view]
  affects: [app.py]
tech_stack:
  added: []
  patterns: [streamlit-tabs, streamlit-agraph, mermaid-flowchart, openai-exception-handling]
key_files:
  created: [ui/summary_view.py, ui/graph_view.py, tests/test_summary_view.py, tests/test_graph_view.py]
  modified: [app.py]
decisions:
  - "APITimeoutError handler placed before APIConnectionError (subclass ordering)"
  - "Mermaid flowchart for process steps via native st.markdown rendering"
  - "Type color map for 7 entity types in graph visualization"
metrics:
  duration: ~5min
  completed: 2026-04-28
---

# Phase 05 Plan 03: Summary and Graph View UI Partials Summary

Tab-based Streamlit layout integrating summary view (direct/map-reduce display) and graph view (table, interactive agraph, mermaid process flow) into the main app alongside existing chat.

## Tasks Completed

### Task 1: Summary view and Graph view UI partials
- **ui/summary_view.py**: `render_summary_view()` — document selection, summarize button with `st.status`, method/chunk-count badge, markdown output, full openai exception handling
- **ui/graph_view.py**: `render_graph_view()` — document selection, extract button with status, stats caption; inner tabs for table view (`_render_tables` with 5 category tabs + `st.dataframe`), interactive graph (`_render_agraph` with `streamlit-agraph` nodes/edges/config), and process flow (`_render_process_mermaid` with native mermaid)
- **Commit:** `137713c`

### Task 2: Integrate views into app.py with tab layout
- Added `render_summary_view` and `render_graph_view` imports
- Replaced single `render_chat()` call with `st.tabs(["💬 Chat", "📝 Summary", "🕸️ Graph"])` layout
- Sidebar, upload, and sample loader remain above tabs
- **Commit:** `a328291`

### Task 3: Unit tests
- **tests/test_summary_view.py**: 7 tests — no-documents info, successful summarization, error display, 4 openai exception types
- **tests/test_graph_view.py**: 12 tests — no-documents info, extraction error, 4 openai exceptions, populated/empty tables, agraph empty/populated, mermaid empty/populated
- **Commit:** `24788ff`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed openai exception handler ordering**
- **Found during:** Task 3 (test execution)
- **Issue:** `APITimeoutError` is a subclass of `APIConnectionError` in the openai SDK; the `APIConnectionError` handler was catching timeout errors first
- **Fix:** Reordered except clauses in both `ui/summary_view.py` and `ui/graph_view.py` to place `APITimeoutError` before `APIConnectionError`
- **Files modified:** ui/summary_view.py, ui/graph_view.py
- **Commit:** 24788ff (combined with tests)

## Test Results

```
133 passed in 10.95s
```

All 114 pre-existing tests + 19 new tests pass.

## Self-Check: PASSED
- [x] ui/summary_view.py exists
- [x] ui/graph_view.py exists
- [x] tests/test_summary_view.py exists
- [x] tests/test_graph_view.py exists
- [x] app.py contains render_summary_view and render_graph_view imports
- [x] Commits 137713c, a328291, 24788ff verified in git log

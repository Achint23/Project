---
phase: 06-model-routing
plan: 02
subsystem: ui, pipelines
tags: [routing-ui, comparison, parallel-execution, metadata-display]
dependency_graph:
  requires: [routers/model_router, pipelines/query, pipelines/summarize, pipelines/graph, ui/sidebar, ui/chat, ui/summary_view, ui/graph_view]
  provides: [ui/comparison, pipelines/compare, model-routing-toggle, metadata-display]
  affects: [ui/sidebar, ui/chat, ui/summary_view, ui/graph_view, app.py]
tech_stack:
  added: []
  patterns: [asyncio-gather-threadpool, st-radio-session-state, st-metric-columns, st-caption-metadata]
key_files:
  created: [pipelines/compare.py, ui/comparison.py, tests/test_comparison.py]
  modified: [ui/sidebar.py, ui/chat.py, ui/summary_view.py, ui/graph_view.py, app.py, tests/test_chat.py, tests/test_summary_view.py, tests/test_graph_view.py]
decisions:
  - "st.radio with 3 options stored in session_state.model_routing_mode"
  - "asyncio.run + asyncio.gather + ThreadPoolExecutor(2) for parallel comparison"
  - "Both comparison calls use run_query independently (acceptable for concept demo)"
  - "st.metric for latency/tokens in comparison columns, st.caption for inline metadata"
  - "Concept demo disclaimer via st.info in comparison panel"
  - "No @st.cache_data on comparison function"
  - "_resolve_model helper in chat.py avoids duplicating routing switch logic"
metrics:
  duration: ~10min
  completed: 2026-04-28
---

# Phase 6 Plan 02: UI Integration + Comparison Panel Summary

Sidebar model routing toggle, per-call metadata display across all views, and side-by-side comparison panel with parallel LLM execution — the demo hero moment for Phase 6.

## What Was Built

### Sidebar Routing Toggle (`ui/sidebar.py`)
- `st.radio` with options: auto / small (route) / large (direct)
- Stored in `st.session_state.model_routing_mode`
- Help text explains each mode

### Per-Call Metadata Display
- **Chat**: model used, latency, token count displayed as `st.caption` below each answer; route reason displayed when in auto mode; metadata stored in chat history for replay
- **Summary**: metadata caption after summary text; route reason in auto mode
- **Graph**: metadata caption after extraction results

### Comparison Pipeline (`pipelines/compare.py`)
- `ComparisonResult` dataclass with `result_large` and `result_small`
- `run_comparison()` uses `asyncio.run` → `asyncio.gather` → `ThreadPoolExecutor(2)` to run both models in parallel
- Both calls go through `run_query` with identical inputs, only model differs
- No caching on comparison function

### Comparison UI (`ui/comparison.py`)
- Text input + Compare button
- `st.info` disclaimer: "Concept demo, not benchmark"
- Two-column layout with `st.metric` for latency and tokens, `st.markdown` for answers
- Error handling for individual model failures and all openai exceptions

### App Layout (`app.py`)
- 4 tabs: Chat, Summary, Graph, Compare

## Test Coverage

- **4 comparison tests**: two results, different models, metadata populated, parallel execution
- **All existing tests updated**: get_settings/route patches added to chat, summary_view, graph_view tests
- **Full suite: 153 tests passing**

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 7f98cc6 | Wire model routing into sidebar and all views with metadata display |
| 2 | af169df | Add comparison pipeline and side-by-side UI panel |
| 3 | 57caa4b | Add comparison pipeline tests |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

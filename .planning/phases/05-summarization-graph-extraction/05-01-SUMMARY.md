---
phase: "05"
plan: "01"
subsystem: summarization
tags: [summarization, map-reduce, prompt-templates, vectorstore, graph-extraction-prompts]
dependency_graph:
  requires: [core/llm_client, core/vectorstore, core/embedder]
  provides: [pipelines/summarize, prompts/summary_map, prompts/summary_reduce, prompts/graph_extract, prompts/graph_correct]
  affects: [pyproject.toml]
tech_stack:
  added: [rapidfuzz, streamlit-agraph, tiktoken]
  patterns: [map-reduce summarization, token-budget routing, prompt templating]
key_files:
  created:
    - pipelines/summarize.py
    - prompts/summary_map.txt
    - prompts/summary_reduce.txt
    - prompts/graph_extract.txt
    - prompts/graph_correct.txt
    - tests/test_summarize_pipeline.py
  modified:
    - pyproject.toml
    - core/vectorstore.py
decisions:
  - "TOKEN_BUDGET=6000 for direct vs map-reduce routing — fits ~4 average chunks"
  - "tiktoken cl100k_base for token counting — consistent with Phase 4 pattern"
  - "Map step uses max_tokens=512, reduce step uses max_tokens=1024"
  - "Temperature 0.3 for summarization — grounded output, minimal hallucination"
  - "graph_extract.txt uses doubled braces for str.format escaping"
metrics:
  duration: "~5 min"
  completed: "2026-04-28"
  tasks_completed: 2
  tasks_total: 2
  test_count: 7
---

# Phase 05 Plan 01: Summarization Pipeline Foundation Summary

**One-liner:** Summarization pipeline with token-budget routing (direct ≤6000 tokens, map-reduce otherwise), VectorStore.get_all_by_doc retrieval, and all 4 prompt templates for summary + graph extraction.

## What Was Built

### Task 1: Dependencies, VectorStore Method, and Prompt Templates
- Added `rapidfuzz>=3.14` and `streamlit-agraph>=0.0.45` to pyproject.toml
- Added `VectorStore.get_all_by_doc(doc_id)` method — retrieves all chunks for a document with chunk_id, text, doc_id, page_num, chunk_type fields
- Created 4 prompt templates:
  - `summary_map.txt` — per-chunk summarization (2-3 sentences)
  - `summary_reduce.txt` — combine section summaries into cohesive business-readable output
  - `graph_extract.txt` — mega-prompt with JSON schema, entity types, one-shot example, and extraction rules for all 5 categories
  - `graph_correct.txt` — self-correction prompt for failed JSON validation

### Task 2: Summarization Pipeline and Tests
- Created `pipelines/summarize.py` with:
  - `SummaryResult` dataclass (summary, doc_id, chunk_count, method, error)
  - `_count_tokens()` using tiktoken cl100k_base
  - `_summarize_direct()` for small documents (≤TOKEN_BUDGET tokens)
  - `_map_reduce()` for large documents (per-chunk map + combined reduce)
  - `run_summarize()` entry point with automatic method selection and error handling
- Created `tests/test_summarize_pipeline.py` with 7 tests:
  - Token counting (positive int, empty string, monotonic)
  - No-chunks error path
  - Direct path (under budget, 1 chat call)
  - Map-reduce path (over budget, N+1 chat calls)
  - Exception handling (error field populated)

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | `cfa7820` | feat(05-01): add dependencies, VectorStore.get_all_by_doc, and prompt templates |
| 2 | `f7320db` | feat(05-01): summarization pipeline with direct and map-reduce paths |

## Test Results

- **100 passed**, 2 deselected (integration), 0 failed
- 7 new tests added in test_summarize_pipeline.py
- All existing tests continue to pass (no regressions)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] `pipelines/summarize.py` exists
- [x] `tests/test_summarize_pipeline.py` exists
- [x] `prompts/summary_map.txt` exists
- [x] `prompts/summary_reduce.txt` exists
- [x] `prompts/graph_extract.txt` exists
- [x] `prompts/graph_correct.txt` exists
- [x] Commit `cfa7820` exists
- [x] Commit `f7320db` exists
- [x] `VectorStore.get_all_by_doc` method present
- [x] 100 tests passing

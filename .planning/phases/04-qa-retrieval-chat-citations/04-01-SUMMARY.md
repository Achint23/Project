---
phase: 04-qa-retrieval-chat-citations
plan: 01
subsystem: retrieval
tags: [retriever, reorder, qa-prompt, citations]
dependency_graph:
  requires: [core/vectorstore.py]
  provides: [core/retriever.py, prompts/qa.txt]
  affects: [pipelines/query (future)]
tech_stack:
  added: []
  patterns: [dataclass, anti-lost-in-the-middle reorder]
key_files:
  created:
    - core/retriever.py
    - prompts/qa.txt
    - tests/test_retriever.py
  modified: []
decisions:
  - "RetrievedChunk as a plain dataclass (no Pydantic) — lightweight, sufficient for internal pipeline data"
  - "reorder_chunks duplicates index-0 chunk at end — ChromaDB ascending distance means index 0 is best match"
  - "QA prompt uses str.format() placeholders ({context}, {question}) — no Jinja2 dependency needed"
metrics:
  duration: "2m 22s"
  completed: "2026-04-28T06:01:05Z"
  tasks: 3
  files_created: 3
  files_modified: 0
  tests_added: 12
  tests_total_passing: 58
---

# Phase 04 Plan 01: Retriever Module + QA Prompt Summary

**One-liner:** Top-k retriever with anti-"lost in the middle" reordering wrapping ChromaDB, plus externalized grounded QA prompt template with citation instructions.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Create retriever module with reordering | `a8e8c7f` | core/retriever.py |
| 2 | Create grounded QA prompt template | `0348d52` | prompts/qa.txt |
| 3 | Unit tests for retriever module | `4aef5c7` | tests/test_retriever.py |

## What Was Built

### core/retriever.py
- **`RetrievedChunk`** dataclass: `chunk_id`, `text`, `doc_id`, `page_num`, `chunk_type`, `distance`
- **`reorder_chunks()`**: Duplicates the highest-scored chunk (index 0, lowest cosine distance) at the end of the list. Returns as-is for ≤1 chunks. Combats the "lost in the middle" phenomenon in long-context LLM prompts.
- **`retrieve()`**: Calls `VectorStore.query()`, parses raw ChromaDB dict into `RetrievedChunk` objects, applies reordering. Supports `n_results` and `doc_id` filtering passthrough.

### prompts/qa.txt
- Externalized prompt template with `{context}` and `{question}` placeholders (str.format compatible)
- Grounding rules: answer only from provided context, cite chunk IDs in `[chunk_id]` brackets
- Fallback: "I don't know based on the provided documents."
- Explicit instruction to use EXACT chunk IDs and not make up information

### tests/test_retriever.py (12 tests)
- `TestReorderChunks`: empty list, single chunk (no duplication), multi-chunk (best first AND last), two-chunk edge case
- `TestRetrieve`: empty results (two variants), populated results with reorder, field population, chunk_type preservation, doc_id filter forwarding, n_results forwarding, default args

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **RetrievedChunk as plain dataclass** — No Pydantic needed; it's internal pipeline data, not a validation boundary.
2. **str.format() for prompt template** — Simple placeholders sufficient; avoids Jinja2 dependency.
3. **reorder uses list concatenation** — `chunks + [chunks[0]]` is clear and correct since ChromaDB returns ascending distance order.

## Self-Check: PASSED

- [x] core/retriever.py exists
- [x] prompts/qa.txt exists
- [x] tests/test_retriever.py exists
- [x] Commit a8e8c7f verified
- [x] Commit 0348d52 verified
- [x] Commit 4aef5c7 verified
- [x] All 58 tests passing (12 new + 46 existing)

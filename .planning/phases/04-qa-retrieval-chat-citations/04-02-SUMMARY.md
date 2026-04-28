---
phase: 04-qa-retrieval-chat-citations
plan: 02
subsystem: query-pipeline
tags: [query, citations, hallucination-detection, qa-pipeline]
dependency_graph:
  requires: [core/retriever.py, core/llm_client.py, prompts/qa.txt, core/vectorstore.py]
  provides: [pipelines/query.py, tests/test_query_pipeline.py]
  affects: [ui/chat (future Plan 03)]
tech_stack:
  added: []
  patterns: [dataclass, regex citation parsing, post-hoc validation, empty-retrieval guard]
key_files:
  created:
    - pipelines/query.py
    - tests/test_query_pipeline.py
  modified: []
decisions:
  - "QueryResult as plain dataclass — consistent with RetrievedChunk pattern, lightweight internal data"
  - "Regex-based citation parsing with hex chunk_id filter — prevents markdown links and numeric refs from false-positiving"
  - "Hallucinated ID deduplication preserves first-seen order — cleaner UI display"
  - "Temperature 0.3 for grounded factual Q&A — lower than default 0.7 to reduce hallucination"
  - "Empty retrieval short-circuits without LLM call — saves API quota and provides clear user message"
metrics:
  duration: "4m 02s"
  completed: "2026-04-28T11:38:00Z"
  tasks: 2
  files_created: 2
  files_modified: 0
  tests_added: 22
  tests_total_passing: 77
---

# Phase 04 Plan 02: Query Pipeline with Citation Validation Summary

**One-liner:** Full Q&A pipeline orchestrating retrieve→prompt→LLM→parse→validate with regex-based citation extraction and post-hoc hallucination detection.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Create query pipeline module | `affdc0f` | pipelines/query.py |
| 2 | Unit tests for query pipeline | `113c949` | tests/test_query_pipeline.py |

## What Was Built

### pipelines/query.py
- **`QueryResult`** dataclass: `answer`, `citations` (list of dicts with chunk_id/text/page_num/chunk_type), `hallucinated_ids` (list of chunk IDs cited but not retrieved), `retrieved_chunks`
- **`_load_prompt_template()`**: Reads `prompts/qa.txt` with UTF-8 encoding
- **`_format_context()`**: Formats chunks as `[chunk_id] (page N):\ntext` joined by double newlines
- **`_parse_citations()`**: Extracts bracketed references then filters to valid chunk ID regex `^[a-f0-9]+_chunk_\d+$` — prevents markdown links `[text](url)` and numeric refs `[1]` from being misidentified
- **`_validate_citations()`**: Splits cited IDs into valid (in retrieval set) and hallucinated (not in retrieval set)
- **`run_query()`**: Full orchestration — retrieve → empty check → build prompt → LLM chat (temperature=0.3) → parse citations → validate → build citation details → return QueryResult

### tests/test_query_pipeline.py (22 tests)
- **TestParseCitations** (7 tests): valid chunk IDs, markdown links ignored, numeric brackets ignored, mixed valid/invalid, empty answer, no brackets, duplicate IDs
- **TestValidateCitations** (4 tests): split valid/hallucinated, all valid, all hallucinated, empty cited
- **TestFormatContext** (3 tests): single chunk format, two chunks joined with double newline, empty list
- **TestRunQuery** (8 tests): empty retrieval short-circuit (no LLM call), successful query with valid citations, hallucinated citation detection, citation detail population, LLM call params (temperature=0.3, max_tokens=1024), doc_id forwarding, n_results forwarding, duplicate hallucinated ID deduplication

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test hallucinated chunk IDs to use hex-only prefixes**
- **Found during:** Task 2
- **Issue:** Test fixtures used `fake99_chunk_7` and `fake_chunk_9` as hallucinated IDs, but the letter `k` is not a hex character so they were correctly filtered out by `_parse_citations` regex `^[a-f0-9]+_chunk_\d+$`, making the tests fail
- **Fix:** Changed to hex-valid prefixes: `face99_chunk_7` and `face00_chunk_9`
- **Files modified:** tests/test_query_pipeline.py
- **Commit:** `113c949`

## Decisions Made

1. **QueryResult as plain dataclass** — Consistent with RetrievedChunk (Plan 01 decision); lightweight for internal pipeline data.
2. **Regex citation filter** — `^[a-f0-9]+_chunk_\d+$` prevents false positives from markdown links and numeric references while matching the actual chunk ID format.
3. **Temperature 0.3** — Lower than the 0.7 default for grounded factual answers; reduces hallucination risk.
4. **Empty retrieval guard** — Returns immediately with a clear message, avoiding unnecessary LLM API calls.
5. **Hallucinated ID deduplication** — Preserves first-seen order for clean UI display.

## Self-Check: PASSED

- [x] pipelines/query.py exists
- [x] tests/test_query_pipeline.py exists
- [x] Commit affdc0f verified
- [x] Commit 113c949 verified
- [x] All 77 tests passing (22 new + 55 existing, excluding OCR model-download hang)

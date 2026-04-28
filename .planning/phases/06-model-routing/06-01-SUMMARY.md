---
phase: 06-model-routing
plan: 01
subsystem: routing, pipelines
tags: [router, metadata, model-selection, pure-function]
dependency_graph:
  requires: [core/config, core/llm_client, pipelines/query, pipelines/summarize, pipelines/graph]
  provides: [routers/model_router, pipeline-metadata-fields]
  affects: [pipelines/query, pipelines/summarize, pipelines/graph]
tech_stack:
  added: []
  patterns: [pure-function-router, dataclass-metadata-fields, perf-counter-timing, usage-null-guard]
key_files:
  created: [routers/__init__.py, routers/model_router.py, tests/test_model_router.py]
  modified: [pipelines/query.py, pipelines/summarize.py, pipelines/graph.py, tests/test_query_pipeline.py, tests/test_summarize_pipeline.py, tests/test_graph_pipeline.py]
decisions:
  - "Pure-function router with zero I/O — model names injected via params, never hardcoded"
  - "TaskType enum: QA, SUMMARY, GRAPH_EXTRACT"
  - "RouteDecision dataclass: model + human-readable reason string"
  - "Metadata fields added with default values for full backward compatibility"
  - "response.usage null-guarded everywhere — zero tokens if usage unavailable"
  - "time.perf_counter() for latency measurement in all pipelines"
  - "response.model used for model_used field — actual model name from API response"
metrics:
  duration: ~8min
  completed: 2026-04-28
---

# Phase 6 Plan 01: Router Module + Pipeline Metadata Extension Summary

Pure-function model router with TaskType enum dispatching by task type and document signals, plus metadata extraction (model_used, tokens, latency) across all three pipeline result dataclasses.

## What Was Built

### Router Module (`routers/model_router.py`)
- `TaskType` enum: `QA`, `SUMMARY`, `GRAPH_EXTRACT`
- `RouteDecision` dataclass: `model: str`, `reason: str`
- `route()` pure function — no I/O, no side effects, all config injected:
  - `GRAPH_EXTRACT` → always large model (JSON-mode reliability)
  - `doc_length > 10,000` or `chunk_count > 15` → large model
  - Otherwise → route (smaller) model for faster response
- Human-readable reason string includes the specific signal that triggered the decision

### Pipeline Metadata Extensions
- `QueryResult`, `SummaryResult`, `GraphResult` all gain: `model_used`, `prompt_tokens`, `completion_tokens`, `latency_ms`
- `QueryResult` and `SummaryResult` also gain `route_reason` field
- `run_query()`, `run_summarize()`, `run_graph_extraction()` accept optional `model: str | None` parameter
- `_summarize_direct()`, `_map_reduce()`, `_extract_with_retry()` propagate model parameter and return token counts
- All `response.usage` access null-guarded with `if usage:` pattern
- `time.perf_counter()` wraps LLM calls for latency measurement

## Test Coverage

- **9 router tests**: all TaskType/signal combinations, boundary conditions, param injection verification
- **3 query metadata tests**: metadata populated, explicit model passthrough, missing usage guard
- **2 summarize metadata tests**: metadata populated, explicit model passthrough
- **2 graph metadata tests**: metadata populated, explicit model passthrough
- **41 existing pipeline tests**: all pass unchanged (backward compat via default values)
- **Full suite: 149 tests passing**

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | b0a33d0 | Create pure-function model router with TaskType enum and RouteDecision |
| 2 | 622b3c8 | Extend pipelines with model parameter and metadata extraction |
| 3 | 2e794cf | Add metadata extraction tests for all pipelines |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

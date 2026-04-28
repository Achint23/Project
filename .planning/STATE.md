# Project State: DocBot

**Last updated:** 2026-04-28 (Phase 5 complete)

## Project Reference

- **Project:** DocBot — Local Intelligent Document Query POC
- **Project doc:** `.planning/PROJECT.md`
- **Requirements doc:** `.planning/REQUIREMENTS.md`
- **Roadmap doc:** `.planning/ROADMAP.md`
- **Core value:** A user can drop a document into a local web app, ask questions in natural language, get summaries, and see entities/relationships extracted — with one-command setup.
- **Current focus:** Phase 5 — Summarization + Graph Extraction

## Current Position

- **Milestone:** v1 POC
- **Current phase:** Phase 5 — Summarization + Graph Extraction (COMPLETE)
- **Current plan:** Plan 03 complete; Phase 5 done — ready for Phase 6
- **Status:** Phase 5 complete — all 3 plans done (summarize pipeline, graph pipeline, UI views)
- **Progress:** 5/7 phases complete

```
[█████░░] 5/7 phases complete
```

## Performance Metrics

- Phases completed: 5
- Plans completed: 15
- Requirements validated: 35/42 (SETUP-01, SETUP-02, SETUP-03, SETUP-04, SETUP-05, LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, INGEST-06, IDX-01, IDX-02, IDX-03, IDX-04, IDX-05, IDX-06, UX-03, QA-01, QA-02, QA-03, QA-04, QA-05, UX-02, SUM-01, SUM-02, GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04)
- Requirements invalidated: 0

## Accumulated Context

### Key Decisions

- Python 3.10–3.12 + uv + tasks.ps1 (PowerShell) chosen for the ≤3-command-setup constraint
- LlamaIndex over LangChain (lighter import surface, RAG-native)
- ChromaDB `PersistentClient` (embedded, telemetry off, single collection with `doc_id` metadata)
- EasyOCR (pure-Python, CPU, English-only) with weights pre-downloaded during `.\tasks.ps1 setup`
- PyMuPDF for text+layout extraction (AGPL acceptable for POC)
- `openai` SDK against NIM's OpenAI-compatible endpoint (one client for chat + embeddings)
- Streamlit `^1.40` UI with `@st.cache_resource` for heavy singletons
- Pinned onnxruntime<1.24 for Python 3.10 compatibility (EasyOCR dependency)
- Lazy EasyOCR init via property to avoid 2GB load until first OCR page
- Tiktoken cl100k_base for token counting (close to Llama-3 budget)
- Embedder dim=1024 hardcoded for nv-embedqa-e5-v5
- SHA-256 content hash as doc_id — never user-supplied filenames in file paths
- IngestResult dataclass with error field for structured pipeline returns
- @st.cache_resource for NIMClient, OCRReader, VectorStore singletons
- session_state.documents list for cross-rerun doc tracking in Streamlit
- maxUploadSize=50 in .streamlit/config.toml (T-03-07 DoS mitigation)
- RetrievedChunk as plain dataclass — lightweight, sufficient for internal pipeline data
- reorder_chunks duplicates index-0 chunk at end — ChromaDB ascending distance order
- QA prompt uses str.format() placeholders — no Jinja2 dependency needed
- QueryResult as plain dataclass — consistent with RetrievedChunk pattern
- Regex citation filter `^[a-f0-9]+_chunk_\d+$` prevents false positives from markdown links
- Temperature 0.3 for grounded Q&A — lower than default to reduce hallucination
- Empty retrieval guard short-circuits without LLM call — saves API quota
- TOKEN_BUDGET=6000 for direct vs map-reduce summarization routing
- tiktoken cl100k_base for token counting — consistent across pipelines
- Map step max_tokens=512, reduce step max_tokens=1024
- graph_extract.txt uses doubled braces for str.format escaping
- Chat history in st.session_state.chat_messages — persists across Streamlit reruns
- Error messages via st.error for all 5 openai exception types — no stack traces (T-04-08)
- Pydantic field aliases (populate_by_name=True) bridge prompt template JSON keys to plan model names
- DEDUP_THRESHOLD=85 for entity fuzzy matching via rapidfuzz token_sort_ratio
- Longer entity name kept as canonical during dedup merge
- APITimeoutError except clause before APIConnectionError — subclass ordering in openai SDK
- st.tabs for Chat/Summary/Graph layout — sidebar and upload remain above tabs
- streamlit-agraph for interactive entity-relationship graph with type-based color map
- Native mermaid via st.markdown for process-step flowchart rendering

### Open Todos

(none)

### Blockers

(none)

### Risk Register (carried from research)

- NVIDIA free-tier 504/429 storms — mitigated in phase 1 (retry/backoff, batched embeddings, fallback model env var)
- Embedding-model mismatch silent failure — mitigated in phase 2 (collection metadata + startup assert)
- EasyOCR ~2GB first-run download — mitigated in phase 2 (pre-download in `make setup`)
- Hallucinated citations / lost-in-the-middle — mitigated in phase 4 (post-hoc citation validation, chunk reordering)
- Routing comparison apples-to-oranges — mitigated in phase 6 (caching off, identical inputs, parallel `asyncio.gather`)

## Session Continuity

### Last Session

- **Date:** 2026-04-28
- **Activity:** Executed Phase 5 — Summarization + Graph Extraction. All 3 plans complete: (1) VectorStore.get_all_by_doc, prompt templates, summarization pipeline with direct/map-reduce routing; (2) Graph extraction pipeline with Pydantic validation, entity dedup, self-correction; (3) Summary/Graph view UI partials with tab-based app layout. 133 tests passing.
- **Next:** `/gsd-plan-phase 6` to plan Phase 6 (Model Routing + Side-by-Side Comparison)

### Resume Notes

To resume: run `/gsd-progress` for status, then `/gsd-plan-phase 6` to plan Phase 6. Phase 5 complete with full summarization + graph extraction pipeline and UI.

---
*State initialized: 2026-04-28*

# Project State: DocBot

**Last updated:** 2026-04-28 (Phase 4, plan 01 complete)

## Project Reference

- **Project:** DocBot — Local Intelligent Document Query POC
- **Project doc:** `.planning/PROJECT.md`
- **Requirements doc:** `.planning/REQUIREMENTS.md`
- **Roadmap doc:** `.planning/ROADMAP.md`
- **Core value:** A user can drop a document into a local web app, ask questions in natural language, get summaries, and see entities/relationships extracted — with one-command setup.
- **Current focus:** Phase 4 — Q&A Retrieval + Chat with Citations

## Current Position

- **Milestone:** v1 POC
- **Current phase:** Phase 4 — Q&A Retrieval + Chat with Citations
- **Current plan:** Plan 01 complete; 2 plans remaining
- **Status:** Phase 4 in progress (plan 01 of 03 done)
- **Progress:** 3/7 phases complete (phase 4 in progress)

```
[███▒░░░] 3/7 phases (phase 4: 1/3 plans)
```

## Performance Metrics

- Phases completed: 3
- Plans completed: 10
- Requirements validated: 25/42 (SETUP-01, SETUP-02, SETUP-03, SETUP-04, SETUP-05, LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, INGEST-06, IDX-01, IDX-02, IDX-03, IDX-04, IDX-05, IDX-06, UX-03, QA-02, QA-05)
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
- **Activity:** Executed Phase 4 Plan 01 — created retriever module (RetrievedChunk, reorder_chunks, retrieve), grounded QA prompt template (prompts/qa.txt), and 12 unit tests. 58 tests passing.
- **Next:** Execute Phase 4 Plan 02 (query pipeline with citation parsing)

### Resume Notes

To resume: run `/gsd-execute-phase 4` to continue. Plan 01 (retriever + QA prompt) is done. Next is Plan 02 (query pipeline with citation parsing and post-hoc validation).

---
*State initialized: 2026-04-28*

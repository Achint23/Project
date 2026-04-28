# Project State: DocBot

**Last updated:** 2026-04-28 (Phase 2 complete)

## Project Reference

- **Project:** DocBot — Local Intelligent Document Query POC
- **Project doc:** `.planning/PROJECT.md`
- **Requirements doc:** `.planning/REQUIREMENTS.md`
- **Roadmap doc:** `.planning/ROADMAP.md`
- **Core value:** A user can drop a document into a local web app, ask questions in natural language, get summaries, and see entities/relationships extracted — with one-command setup.
- **Current focus:** Phase 3 — Ingestion Pipeline + Upload UI

## Current Position

- **Milestone:** v1 POC
- **Current phase:** Phase 3 — Ingestion Pipeline + Upload UI
- **Current plan:** none yet (run `/gsd-plan-phase 3`)
- **Status:** Phase 2 complete; awaiting phase 3 planning
- **Progress:** 2/7 phases complete

```
[██░░░░░] 2/7 phases
```

## Performance Metrics

- Phases completed: 2
- Plans completed: 6
- Requirements validated: 16/42 (SETUP-01, SETUP-02, SETUP-03, SETUP-04, SETUP-05, LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, INGEST-02, INGEST-03, IDX-01, IDX-02, IDX-03, IDX-04)
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
- **Activity:** Executed Phase 2 — created PDF extraction (PyMuPDF text + tables + OCR threshold), EasyOCR lazy wrapper, structure-aware chunker (tiktoken, 700/100 tokens), Embedder wrapper, ChromaDB vector store with model-metadata validation. 35 tests passing.
- **Next:** `/gsd-plan-phase 3`

### Resume Notes

To resume: run `/gsd-progress` for a status snapshot, then `/gsd-plan-phase 3` to begin planning Phase 3 (Ingestion Pipeline + Upload UI). Phase 2 is complete with all extraction, chunking, and vectorstore code in place.

---
*State initialized: 2026-04-28*

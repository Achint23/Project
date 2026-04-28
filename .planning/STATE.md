# Project State: DocBot

**Last updated:** 2026-04-28

## Project Reference

- **Project:** DocBot — Local Intelligent Document Query POC
- **Project doc:** `.planning/PROJECT.md`
- **Requirements doc:** `.planning/REQUIREMENTS.md`
- **Roadmap doc:** `.planning/ROADMAP.md`
- **Core value:** A user can drop a document into a local web app, ask questions in natural language, get summaries, and see entities/relationships extracted — with one-command setup.
- **Current focus:** Phase 2 — Extraction, OCR, Chunking & Vector Store

## Current Position

- **Milestone:** v1 POC
- **Current phase:** Phase 2 — Extraction, OCR, Chunking & Vector Store
- **Current plan:** none yet (run `/gsd-plan-phase 2`)
- **Status:** Phase 1 complete; awaiting phase 2 planning
- **Progress:** 1/7 phases complete

```
[█░░░░░░] 1/7 phases
```

## Performance Metrics

- Phases completed: 1
- Plans completed: 3
- Requirements validated: 9/42 (SETUP-01, SETUP-02, SETUP-03, SETUP-05, LLM-01, LLM-02, LLM-03, LLM-04, LLM-05)
- Requirements invalidated: 0

## Accumulated Context

### Key Decisions

- Python 3.10–3.12 + uv + Makefile chosen for the ≤3-command-setup constraint
- LlamaIndex over LangChain (lighter import surface, RAG-native)
- ChromaDB `PersistentClient` (embedded, telemetry off, single collection with `doc_id` metadata)
- EasyOCR (pure-Python, CPU, English-only) with weights pre-downloaded during `make setup`
- PyMuPDF for text+layout extraction (AGPL acceptable for POC)
- `openai` SDK against NIM's OpenAI-compatible endpoint (one client for chat + embeddings)
- Streamlit `^1.40` UI with `@st.cache_resource` for heavy singletons

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
- **Activity:** Executed Phase 1 — created project scaffold (pyproject.toml, Makefile, .env.local.example, app.py), core/config.py (Pydantic settings), core/llm_client.py (NIMClient with retry/JSON-mode/batched-embeddings), smoke tests, and unit tests (9 passing).
- **Next:** `/gsd-plan-phase 2`

### Resume Notes

To resume: run `/gsd-progress` for a status snapshot, then `/gsd-plan-phase 2` to begin planning Phase 2 (Extraction, OCR, Chunking & Vector Store). Phase 1 is complete with all code in place. Integration smoke tests require a valid `.env.local` with NVIDIA_API_KEY.

---
*State initialized: 2026-04-28*

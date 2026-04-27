# Project State: DocBot

**Last updated:** 2026-04-28

## Project Reference

- **Project:** DocBot — Local Intelligent Document Query POC
- **Project doc:** `.planning/PROJECT.md`
- **Requirements doc:** `.planning/REQUIREMENTS.md`
- **Roadmap doc:** `.planning/ROADMAP.md`
- **Core value:** A user can drop a document into a local web app, ask questions in natural language, get summaries, and see entities/relationships extracted — with one-command setup.
- **Current focus:** Phase 1 — Skeleton + NIM Client

## Current Position

- **Milestone:** v1 POC
- **Current phase:** Phase 1 — Skeleton + NIM Client
- **Current plan:** none yet (run `/gsd-plan-phase 1`)
- **Status:** Roadmap approved; awaiting phase 1 planning
- **Progress:** 0/7 phases complete

```
[░░░░░░░] 0/7 phases
```

## Performance Metrics

- Phases completed: 0
- Plans completed: 0
- Requirements validated: 0/42
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
- **Activity:** Project initialization — PROJECT.md, REQUIREMENTS.md (42 v1 reqs), research bundle (STACK/ARCHITECTURE/PITFALLS/FEATURES/SUMMARY), and ROADMAP.md (7 phases) created.
- **Next:** `/gsd-plan-phase 1`

### Resume Notes

To resume: run `/gsd-progress` for a status snapshot, then `/gsd-plan-phase 1` to begin planning Phase 1 (Skeleton + NIM Client). No code yet — repo contains only `test-nvidia.mjs` (NIM auth reference) and `.planning/`.

---
*State initialized: 2026-04-28*

# Roadmap: DocBot — Local Intelligent Document Query POC

**Defined:** 2026-04-28
**Granularity:** standard (5–8 phases)
**Milestone:** v1 POC
**Core Value:** A user can drop a document into a local web app, ask questions in natural language, get summaries, and see entities/relationships extracted — with one-command setup.

## Phases

- [x] **Phase 1: Skeleton + NIM Client** — Project scaffolding, ≤3-command setup, and a resilient NVIDIA NIM client with retry/backoff/JSON-mode/batched embeddings
- [x] **Phase 2: Extraction, OCR, Chunking & Vector Store** — Text-first PDF extraction with OCR fallback, structure-aware chunker, and ChromaDB persistence with embedding-model metadata
- [x] **Phase 3: Ingestion Pipeline + Upload UI** — End-to-end ingest pipeline with content-hash dedupe and a Streamlit upload + document-list UI
- [x] **Phase 4: Q&A Retrieval + Chat with Citations** — Grounded chat over indexed corpus with inline `[chunk_id]` citations and hallucination flagging
- [x] **Phase 5: Summarization + Graph Extraction** — Map-reduce summaries plus prompt-based entity/relationship/process-step extraction with Pydantic validation and node-edge view
- [ ] **Phase 6: Model Routing + Side-by-Side Comparison** — Pure-function router, manual/auto toggle, and parallel direct-vs-routed comparison panel
- [ ] **Phase 7: Demo Polish & End-to-End UX** — Unified single-session demo flow, README quickstart, and demo-readiness checks

## Phase Details

### Phase 1: Skeleton + NIM Client
**Goal**: Developers can clone the repo, run ≤3 setup commands, and the app talks to NVIDIA NIM with production-grade resilience.
**Depends on**: Nothing (foundation)
**Requirements**: SETUP-01, SETUP-02, SETUP-03, SETUP-05, LLM-01, LLM-02, LLM-03, LLM-04, LLM-05
**Success Criteria** (what must be TRUE):
  1. A fresh clone reaches a running app in ≤3 commands on Python 3.10–3.12 with no external system binaries.
  2. `make setup`, `make run`, `make clean`, and `make doctor` targets all execute successfully.
  3. `.env.local.example` is committed and the app reads `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_MODEL`, `NVIDIA_ROUTE_MODEL`, `NVIDIA_EMBED_MODEL` from `.env.local`.
  4. A smoke test makes a JSON-mode chat round-trip against NVIDIA NIM and exits 0.
  5. The LLM client survives an injected 429/504 via exponential-backoff-with-jitter retry within a 60s timeout.
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffolding, packaging, env config, Streamlit skeleton
- [x] 01-02-PLAN.md — NVIDIA NIM LLM client with retry, JSON mode, batched embeddings
- [x] 01-03-PLAN.md — Smoke test, .gitignore, doctor target

**UI hint**: no
**Research during planning**: no (test-nvidia.mjs is the in-repo reference)

### Phase 2: Extraction, OCR, Chunking & Vector Store
**Goal**: Any uploaded PDF — digital, scanned, or table-heavy — becomes faithfully chunked, embedded vectors persisted in ChromaDB, with the embedding model recorded so retrieval can never silently mismatch.
**Depends on**: Phase 1
**Requirements**: SETUP-04, INGEST-02, INGEST-03, IDX-01, IDX-02, IDX-03, IDX-04
**Success Criteria** (what must be TRUE):
  1. EasyOCR weights are pre-downloaded during `make setup` so a user's first run incurs no multi-minute download.
  2. Digital PDFs extract via PyMuPDF preserving paragraphs and basic tables; scanned/image pages auto-route to EasyOCR via a `<50 chars` heuristic.
  3. Chunks land at ~500–800 tokens with ~100–150 overlap and never split across tables, lists, or headings; tables and headings are emitted as atomic chunks tagged with `chunk_type` metadata.
  4. Embedding calls are batched (32–64 chunks/request) and persisted to a ChromaDB `PersistentClient` collection with telemetry off and `doc_id` metadata.
  5. The collection records `embedding_model` and `embedding_dim`; on startup, a model/dim mismatch is detected and reported clearly.
**Plans:** 3 plans
**UI hint**: no
**Research during planning**: no (PITFALLS.md + ARCHITECTURE.md cover the patterns)

Plans:
- [x] 02-01-PLAN.md — Dependencies, PDF extraction & OCR with EasyOCR pre-download
- [x] 02-02-PLAN.md — Structure-aware token-based chunker
- [x] 02-03-PLAN.md — Embedder & ChromaDB vector store with model validation

### Phase 3: Ingestion Pipeline + Upload UI
**Goal**: A user can drag-and-drop a document (or load a sample) and see it processed, indexed, and listed in the UI — re-uploads are idempotent.
**Depends on**: Phase 2
**Requirements**: INGEST-01, INGEST-04, INGEST-05, INGEST-06, IDX-05, IDX-06, UX-03
**Success Criteria** (what must be TRUE):
  1. User can upload PDF, scanned PDF, and image-based files via the Streamlit UI and watch progress via `st.status`.
  2. A bundled sample set (digital, scanned, multi-column, table-heavy) loads with one click from `data/samples/`.
  3. Re-uploading the same file produces no duplicate vectors (content-hash dedupe).
  4. User can delete an indexed document and its vectors + cached files are removed cleanly.
  5. Heavy resources (LLM client, EasyOCR Reader, Chroma client) are wrapped in `@st.cache_resource` and survive Streamlit reruns without re-instantiation.
**Plans:** 3 plans
**UI hint**: yes
**Research during planning**: no (pure composition over phase 1–2)

Plans:
- [x] 03-01-PLAN.md — Ingest pipeline module with content-hash dedupe, extract/chunk/persist orchestration, and delete
- [x] 03-02-PLAN.md — Streamlit upload UI, sidebar document list, sample loader, @st.cache_resource singletons
- [x] 03-03-PLAN.md — Sample documents, IDX-05 doc_id filter test, Streamlit server config

### Phase 4: Q&A Retrieval + Chat with Citations
**Goal**: A user can ask natural-language questions in chat and get grounded, citation-backed answers — with hallucinated citations visibly flagged.
**Depends on**: Phase 3
**Requirements**: QA-01, QA-02, QA-03, QA-04, QA-05, UX-02
**Success Criteria** (what must be TRUE):
  1. User asks a natural-language question and receives an answer grounded only in retrieved context, or "I don't know" when context is insufficient.
  2. Answers render inline `[chunk_id]` citations with expandable source-chunk previews showing page number and original text.
  3. A post-hoc check validates every cited `chunk_id` against the retrieval log and flags hallucinated citations in the UI.
  4. Top-k=3–5 retrieval supports `doc_id` filtering, and chunks are reordered so the highest-scored chunk appears first AND last in the prompt.
  5. NVIDIA API errors (rate limit, 504, auth) surface as readable messages via `st.error` instead of crashing the app.
**Plans:** 3 plans
**UI hint**: yes
**Research during planning**: no (standard grounded-RAG pattern, citation validation documented in PITFALLS #8)

Plans:
- [x] 04-01-PLAN.md — Retriever module with top-k reordering + grounded QA prompt template
- [x] 04-02-PLAN.md — Query pipeline with citation parsing and post-hoc validation
- [x] 04-03-PLAN.md — Streamlit chat UI with expandable citations, hallucination flags, and API error handling

### Phase 5: Summarization + Graph Extraction
**Goal**: From any indexed document a user can produce a business-readable summary AND a validated entity/relationship/process-step JSON rendered as both a table and a node/edge view.
**Depends on**: Phase 4
**Requirements**: SUM-01, SUM-02, GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04
**Success Criteria** (what must be TRUE):
  1. User can request a concise summary of any indexed document; long documents fall back to a map-reduce pattern over chunks.
  2. User can run prompt-based extraction that returns entities, relationships, process steps, decision points, and business rules as structured JSON.
  3. Output is validated against a Pydantic schema; on parse failure the system performs a one-shot self-correction retry.
  4. Extracted graph data is rendered both as a readable table and as a node/edge or mermaid process-flow view in the UI.
  5. Entity duplicates are merged via `rapidfuzz` fuzzy matching with a documented threshold.
**Plans:** 3 plans

Plans:
- [x] 05-01-PLAN.md — Dependencies, VectorStore extension, prompt templates, and summarization pipeline
- [x] 05-02-PLAN.md — Graph extraction pipeline with Pydantic validation, entity dedup, self-correction
- [x] 05-03-PLAN.md — Summary and Graph view UI partials with tab-based app layout

**UI hint**: yes
**Research during planning**: yes — flagged in SUMMARY.md (JSON-mode/few-shot prompt design and fuzzy-merge thresholds need a focused research pass)

### Phase 6: Model Routing + Side-by-Side Comparison
**Goal**: A user can toggle between auto/small/large model selection and run the same question through direct vs routed paths in parallel, seeing model, tokens, latency, and the auto-router's reason.
**Depends on**: Phase 5 (uses graph-extraction call sites as a non-trivial routing target)
**Requirements**: ROUTE-01, ROUTE-02, ROUTE-03, ROUTE-04, ROUTE-05
**Success Criteria** (what must be TRUE):
  1. `routers/model_router.py` exposes a pure function `route(task, signals) → RouteDecision(model, reason)`.
  2. A sidebar toggle lets the user pick `auto`, `small (route)`, or `large (direct)` and every LLM call surfaces the model used, tokens consumed, and latency in the UI.
  3. A side-by-side panel runs the SAME question against direct (large) and routed (small/alternate) paths in parallel via `asyncio.gather`, rendering both answers, latencies, and token counts with a "concept demo, not benchmark" disclaimer.
  4. The auto-router's decision reason renders as plain text in the UI ("routed via X because Y") on every call.
  5. The comparison panel disables caching and uses identical system prompt, user prompt, retrieved chunks, and temperature — only the model differs.
**Plans**: TBD
**UI hint**: yes
**Research during planning**: yes — flagged in SUMMARY.md (small-model selection on NVIDIA catalog and free-tier parallel-call behavior need a quick spike)

### Phase 7: Demo Polish & End-to-End UX
**Goal**: A presenter can walk through load → process → ask → summarize → extract graph → compare routing in a single browser session, guided by a README quickstart, on a fresh machine.
**Depends on**: Phase 6
**Requirements**: UX-01, UX-04
**Success Criteria** (what must be TRUE):
  1. The Streamlit UI exposes upload, document list, chat, summarize, graph view, routing toggle, and routing comparison panel from a single browser session without page reloads.
  2. The README quickstart documents the end-to-end demo flow (load sample → process → ask → summarize → extract graph → compare direct vs routed) and walks a new user from clone to demo unaided.
  3. A demo dry-run on a fresh Windows or macOS machine completes the full flow successfully against the bundled sample set.
**Plans**: TBD
**UI hint**: yes
**Research during planning**: no (Streamlit conventions documented in PITFALLS #11)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Skeleton + NIM Client | 3/3 | Complete | 2026-04-28 |
| 2. Extraction, OCR, Chunking & Vector Store | 3/3 | Complete | 2026-04-28 |
| 3. Ingestion Pipeline + Upload UI | 3/3 | Complete | 2026-04-28 |
| 4. Q&A Retrieval + Chat with Citations | 3/3 | Complete | 2026-04-28 |
| 5. Summarization + Graph Extraction | 3/3 | Complete | 2026-04-28 |
| 6. Model Routing + Side-by-Side Comparison | 0/0 | Not started | - |
| 7. Demo Polish & End-to-End UX | 0/0 | Not started | - |

## Coverage

- **v1 requirements:** 42 (per REQUIREMENTS.md categories: SETUP 5 + LLM 5 + INGEST 6 + IDX 6 + QA 5 + SUM 2 + GRAPH 4 + ROUTE 5 + UX 4)
- **Mapped to phases:** 42
- **Unmapped:** 0
- **Coverage:** 100% ✓

> Note: PROJECT.md scoping summary referenced "39 v1 requirements"; the canonical REQUIREMENTS.md file enumerates 42 distinct REQ-IDs and that count is used here.

---
*Roadmap created: 2026-04-28*
*Last updated: 2026-04-28 after Phase 5 completion*

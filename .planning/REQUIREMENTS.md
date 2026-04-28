# Requirements: DocBot

**Defined:** 2026-04-28
**Core Value:** A user can drop a document into a local web app, ask questions in natural language, get summaries, and see entities/relationships extracted — with one-command setup.

## v1 Requirements

Requirements for the POC release. Each maps to roadmap phases.

### Setup & Packaging

- [ ] **SETUP-01**: Project sets up locally in ≤ 3 commands from a fresh clone (e.g., `uv sync`, configure `.env.local`, `make run`)
- [ ] **SETUP-02**: A `Makefile` (or equivalent task runner) exposes `setup`, `run`, `clean`, and `doctor` targets
- [ ] **SETUP-03**: `.env.local` pattern reads `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_MODEL`, `NVIDIA_ROUTE_MODEL`, `NVIDIA_EMBED_MODEL`; `.env.local.example` is committed
- [x] **SETUP-04**: EasyOCR weights are pre-downloaded during `make setup` so the first user-facing run is instant
- [ ] **SETUP-05**: Project runs on a developer laptop with Python 3.10–3.12 (CPU only) without external system binaries

### LLM Integration

- [ ] **LLM-01**: Python NVIDIA NIM client uses the OpenAI-compatible SDK pattern from `test-nvidia.mjs` (Bearer auth, configurable `base_url`, default model `meta/llama-3.1-70b-instruct`)
- [ ] **LLM-02**: LLM client implements 60s timeout and exponential-backoff-with-jitter retry on HTTP 429 / 504
- [ ] **LLM-03**: LLM client supports JSON mode (`response_format={"type":"json_object"}`) for structured extraction
- [ ] **LLM-04**: LLM client batches embedding calls (32–64 chunks per request) against the configured embedding model
- [ ] **LLM-05**: Smoke test asserts a JSON-mode chat round-trip succeeds against NVIDIA NIM

### Document Ingestion

- [x] **INGEST-01**: User can upload PDF, scanned PDF, and image-based document files via the web UI
- [x] **INGEST-02**: System auto-detects scanned/image pages and routes them to OCR (EasyOCR) while sending text-PDF pages to direct extraction
- [x] **INGEST-03**: Text-PDF extraction uses PyMuPDF and preserves paragraph structure plus basic table content
- [x] **INGEST-04**: A small bundled set of sample documents (digital PDF, scanned PDF, multi-column, table-heavy) ships in `data/samples/` and can be loaded with one click
- [x] **INGEST-05**: Re-uploading the same file is idempotent (content-hash dedupe — no duplicate vectors)
- [x] **INGEST-06**: Upload UI shows progress (`st.status`) and surfaces errors clearly

### Indexing & Retrieval

- [x] **IDX-01**: Documents are chunked with a structure-aware splitter (~500–800 tokens, ~100–150 overlap) that does not split inside tables, lists, or headings
- [x] **IDX-02**: Tables and headings are emitted as atomic chunks with `chunk_type` metadata
- [x] **IDX-03**: Chunks are embedded via NVIDIA NIM and persisted to ChromaDB (`PersistentClient`, telemetry off, single collection with `doc_id` metadata)
- [x] **IDX-04**: ChromaDB collection metadata stores `embedding_model` and `embedding_dim`; mismatch on startup is detected and reported
- [x] **IDX-05**: Semantic top-k retrieval (k=3–5) supports filtering by `doc_id`
- [x] **IDX-06**: A “delete document” / reset capability removes a doc’s vectors and cached files cleanly

### Q&A

- [x] **QA-01**: User can ask natural-language questions against the indexed document corpus through a chat UI
- [x] **QA-02**: Answers are generated using a grounded prompt that instructs the model to answer only from retrieved context and respond "I don't know" otherwise
- [x] **QA-03**: Each answer renders inline citations (`[chunk_id]`) with expandable source-chunk previews showing page number and original text
- [x] **QA-04**: A post-hoc check validates every cited `chunk_id` against the retrieval log and flags hallucinated citations in the UI
- [x] **QA-05**: Retrieved chunks are reordered so the highest-scored chunk appears first AND last in the prompt (anti "lost in the middle")

### Summarization

- [ ] **SUM-01**: User can request a concise, business-readable summary of any indexed document
- [ ] **SUM-02**: Summarization uses a map-reduce pattern over chunked content for documents that exceed the model context window

### Graph-Style Semantic Extraction

- [ ] **GRAPH-01**: User can run prompt-based extraction that produces structured output containing **entities, relationships, process steps, decision points, and business rules**
- [ ] **GRAPH-02**: Output is validated against a Pydantic schema; on parse failure, a one-shot self-correction retry is performed
- [ ] **GRAPH-03**: Extracted graph data is rendered as both a readable table view and a simple node/edge (or mermaid process-flow) view in the UI
- [ ] **GRAPH-04**: Entity deduplication is applied via fuzzy string matching (e.g., `rapidfuzz`) with a documented threshold

### Model Routing

- [ ] **ROUTE-01**: A `routers/model_router.py` module exposes a pure function `route(task, signals) → RouteDecision(model, reason)`
- [ ] **ROUTE-02**: Sidebar toggle lets the user pick `auto`, `small (route)`, or `large (direct)` model selection
- [ ] **ROUTE-03**: Every LLM call surfaces the model used, tokens consumed, and latency in the UI
- [ ] **ROUTE-04**: A side-by-side comparison panel runs the SAME question against the direct path (large model) and the routed path (small/alternate model) in parallel (`asyncio.gather`), showing both answers, latencies, and token counts
- [ ] **ROUTE-05**: The auto-router makes decisions based on task type and document length signals, and renders the decision reason as plain text in the UI

### Demo & UX

- [ ] **UX-01**: Streamlit (or Gradio) web UI exposes upload, document list, chat, summarize, graph view, routing toggle, and routing comparison panel from a single browser session
- [x] **UX-02**: NVIDIA API errors (rate limit, 504 timeout, auth) are surfaced as readable messages via `st.error`
- [x] **UX-03**: Heavy resources (LLM client, EasyOCR Reader, Chroma client) are wrapped in `@st.cache_resource` so Streamlit reruns don’t re-instantiate them
- [ ] **UX-04**: A README quickstart documents the end-to-end demo flow: load sample → process → ask question → summarize → extract graph → compare direct vs routed

## v2 Requirements

Deferred — explicitly out of scope for the POC, tracked for future.

### Local Inference & Storage

- **LOCAL-01**: Fully local LLM inference via Ollama / llama.cpp
- **LOCAL-02**: Real graph database backend (Neo4j or similar)

### Retrieval Quality

- **RETR-01**: Hybrid retrieval (BM25 + vector) with cross-encoder rerank
- **RETR-02**: Cell-level table Q&A (vs current chunk-level)

### Multi-User / Persistence

- **MULTI-01**: User authentication and per-user document isolation
- **MULTI-02**: Persistent cross-session chat history
- **MULTI-03**: Bulk / enterprise-scale ingestion pipelines

### Compliance

- **COMP-01**: PII detection / redaction in extracted text

## Out of Scope

| Feature | Reason |
|---------|--------|
| Production-grade scaling, bulk enterprise ingestion | POC validates feasibility on a small sample set only |
| True graph database backend (Neo4j) | Scope explicitly says graph backend is not required; prompt-based simulation suffices |
| Cloud deployment, multi-tenancy, user auth | Local single-user demo is the target |
| Production-grade routing engine with cost/latency optimization | Concept demo only — not a real router |
| Fine-tuning or training custom models | Use NVIDIA-hosted models as-is |
| Mobile app, desktop installer | Browser-based local web app is sufficient |
| Real-time collaboration / multi-user sharing | Single-user POC |
| Fully offline LLM inference | Defer to v2; NVIDIA API used to keep setup minimal |
| Streaming token output (SSE) | Polish-only — defer if time-pressured |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 1: Skeleton + NIM Client | Pending |
| SETUP-02 | Phase 1: Skeleton + NIM Client | Pending |
| SETUP-03 | Phase 1: Skeleton + NIM Client | Pending |
| SETUP-04 | Phase 2: Extraction, OCR, Chunking & Vector Store | Complete |
| SETUP-05 | Phase 1: Skeleton + NIM Client | Pending |
| LLM-01 | Phase 1: Skeleton + NIM Client | Pending |
| LLM-02 | Phase 1: Skeleton + NIM Client | Pending |
| LLM-03 | Phase 1: Skeleton + NIM Client | Pending |
| LLM-04 | Phase 1: Skeleton + NIM Client | Pending |
| LLM-05 | Phase 1: Skeleton + NIM Client | Pending |
| INGEST-01 | Phase 3: Ingestion Pipeline + Upload UI | Complete |
| INGEST-02 | Phase 2: Extraction, OCR, Chunking & Vector Store | Complete |
| INGEST-03 | Phase 2: Extraction, OCR, Chunking & Vector Store | Complete |
| INGEST-04 | Phase 3: Ingestion Pipeline + Upload UI | Complete |
| INGEST-05 | Phase 3: Ingestion Pipeline + Upload UI | Complete |
| INGEST-06 | Phase 3: Ingestion Pipeline + Upload UI | Complete |
| IDX-01 | Phase 2: Extraction, OCR, Chunking & Vector Store | Complete |
| IDX-02 | Phase 2: Extraction, OCR, Chunking & Vector Store | Complete |
| IDX-03 | Phase 2: Extraction, OCR, Chunking & Vector Store | Complete |
| IDX-04 | Phase 2: Extraction, OCR, Chunking & Vector Store | Complete |
| IDX-05 | Phase 3: Ingestion Pipeline + Upload UI | Complete |
| IDX-06 | Phase 3: Ingestion Pipeline + Upload UI | Complete |
| QA-01 | Phase 4: Q&A Retrieval + Chat with Citations | Pending |
| QA-02 | Phase 4: Q&A Retrieval + Chat with Citations | Complete |
| QA-03 | Phase 4: Q&A Retrieval + Chat with Citations | Pending |
| QA-04 | Phase 4: Q&A Retrieval + Chat with Citations | Complete |
| QA-05 | Phase 4: Q&A Retrieval + Chat with Citations | Complete |
| SUM-01 | Phase 5: Summarization + Graph Extraction | Pending |
| SUM-02 | Phase 5: Summarization + Graph Extraction | Pending |
| GRAPH-01 | Phase 5: Summarization + Graph Extraction | Pending |
| GRAPH-02 | Phase 5: Summarization + Graph Extraction | Pending |
| GRAPH-03 | Phase 5: Summarization + Graph Extraction | Pending |
| GRAPH-04 | Phase 5: Summarization + Graph Extraction | Pending |
| ROUTE-01 | Phase 6: Model Routing + Side-by-Side Comparison | Pending |
| ROUTE-02 | Phase 6: Model Routing + Side-by-Side Comparison | Pending |
| ROUTE-03 | Phase 6: Model Routing + Side-by-Side Comparison | Pending |
| ROUTE-04 | Phase 6: Model Routing + Side-by-Side Comparison | Pending |
| ROUTE-05 | Phase 6: Model Routing + Side-by-Side Comparison | Pending |
| UX-01 | Phase 7: Demo Polish & End-to-End UX | Pending |
| UX-02 | Phase 4: Q&A Retrieval + Chat with Citations | Pending |
| UX-03 | Phase 3: Ingestion Pipeline + Upload UI | Complete |
| UX-04 | Phase 7: Demo Polish & End-to-End UX | Pending |

**Coverage:**
- v1 requirements: 42 total (SETUP 5 + LLM 5 + INGEST 6 + IDX 6 + QA 5 + SUM 2 + GRAPH 4 + ROUTE 5 + UX 4)
- Mapped to phases: 42
- Unmapped: 0
- Coverage: 100% ✓

> Note: The PROJECT.md scoping summary referenced "39 v1 requirements"; the canonical enumeration above is 42. Roadmap uses the canonical count.

---
*Requirements defined: 2026-04-28*
*Last updated: 2026-04-28 after initial definition*

# Project Research Summary

**Project:** DocBot — Local Intelligent Document Query POC
**Domain:** Local-deployable RAG + multimodal-document-understanding demo with model-routing concept
**Researched:** 2026-04-28
**Confidence:** HIGH

## Executive Summary

DocBot is a single-user, locally-runnable RAG demo in a well-trodden product category (ChatPDF / NotebookLM / AnythingLLM-class) with two explicit POC differentiators baked into scope: **prompt-based semantic/graph extraction with visual rendering**, and a **NVIDIA-NIM model-routing comparison** with observable latency/tokens. The category is mature, the patterns are standard, and the locked constraints (Python 3.10+, ChromaDB embedded, EasyOCR, NVIDIA NIM, ≤3 setup commands) leave only a small number of real choices to make.

The recommended approach is a **LlamaIndex + PyMuPDF + EasyOCR + Chroma `PersistentClient` + `openai` SDK (against NIM's OpenAI-compatible endpoint) + Streamlit** stack, packaged with **uv + Makefile** to hit the 3-command setup target. Architecture is the standard `core/` (capabilities) + `pipelines/` (orchestration) + `ui/` (Streamlit partials) + `routers/` (policy) + `prompts/` (externalized templates) split, with one persistent ChromaDB collection and `doc_id` metadata to enable per-doc filtering and clean resets.

The dominant risks are operational, not architectural: NVIDIA free-tier 504/429s during live demos, EasyOCR's silent multi-minute first-run download, embedding-model mismatch between ingest and query producing silent retrieval failures, and Streamlit's "rerun-the-whole-script" model re-instantiating heavy resources on every interaction. Every one of these is preventable with patterns that must be in place from phase 1 (`@st.cache_resource` for heavy clients, batched embeddings with retry/backoff, collection-metadata assertion on startup, fallback-model env var, pre-downloaded OCR weights).

## Key Findings

### Recommended Stack

For a 1-week POC under the locked constraints, the prescriptive stack collapses to a small set of choices that all reinforce the "minimal install" goal. NIM is OpenAI-compatible so a single `openai` client serves both chat and embeddings — no NIM-specific package needed. LlamaIndex wins over LangChain because this is a pure-RAG flow (Document → Node → Index → QueryEngine maps 1:1) and its import surface is smaller. PyMuPDF is the fastest text+layout extractor and exposes `get_text("blocks")` for table-aware reading; the AGPL license is a non-issue for a POC. uv + Makefile makes `uv sync && cp .env.local.example .env.local && make run` a literal 3-command setup.

**Core technologies:**
- **Python 3.10–3.12 + uv + Makefile** — pinned `<3.13` because PyTorch (EasyOCR dep) wheels lag on 3.13; uv gives deterministic lockfile + 10–100× faster installs.
- **LlamaIndex (`llama-index-core ^0.12`)** — RAG-native orchestration; lighter than LangChain; `OpenAILike` LLM/embedding wrappers point straight at NIM.
- **Streamlit `^1.40`** — single-file UI, `st.cache_resource` for heavy singletons, `st.chat_message`/`st.chat_input` stable, native file uploader.
- **ChromaDB `^0.5` `PersistentClient`** — embedded, persists to disk, telemetry off, one collection with `doc_id` metadata.
- **PyMuPDF `^1.24` + pdf2image + EasyOCR `^1.7.2`** — text-first extraction with OCR fallback when a page yields <50 chars; cache the `Reader(['en'], gpu=False)` once per process.
- **`openai ^1.50` SDK against `https://integrate.api.nvidia.com/v1`** — same Bearer-token + `base_url` pattern proven in `test-nvidia.mjs`; one client for `meta/llama-3.1-70b-instruct` chat, `nvidia/nv-embedqa-e5-v5` embeddings, and the smaller routing-target model.
- **Pydantic `^2.7` + `response_format={"type":"json_object"}`** — structured graph extraction with schema validation and one-shot self-correction.

### Expected Features

This is a well-established product category, so users have firm baseline expectations. The two POC differentiators (semantic extraction + routing comparison) are exactly where this demo earns its "oh nice" moments — everything else should match category baseline, not try to out-ChatPDF ChatPDF.

**Must have (table-stakes — top 8):**
- PDF + scanned-PDF + image upload via Streamlit, with auto-detection routing scanned pages to EasyOCR.
- Page-aware text extraction with basic table capture preserved.
- Chunk → embed → persist into ChromaDB with `doc_id` metadata; idempotent on re-upload (content-hashed).
- Semantic top-k retrieval with **inline citations (page + expandable source chunk)** — without these the demo isn't credible.
- One-click document summarization producing business-readable bullets.
- Prompt-based extraction of entities / relationships / process steps / decision points / business rules → validated JSON + readable table view.
- Manual model selector between two NVIDIA-hosted models, with per-call token + latency display.
- Bundled sample documents + one-command setup + API errors surfaced in the UI.

**Should have (differentiators worth doing in this POC — top 4):**
- **Side-by-side routing comparison view** (same Q → Model A vs Model B, both answers + latencies + token cost in one screen) — strongest demo moment.
- **Rule-based auto-router with visible "router decision" reason** (`route(task, signals) → {model, reason}`) — elevates routing from manual switch to intelligent dispatch.
- **Graph view + mermaid process-flow rendering** of extracted entities/relationships/steps from the same JSON payload — direct visual payoff of the semantic-extraction scope.
- **Streaming answers (SSE) + "Why this answer?" panel** showing retrieved chunks, scores, and which model answered — observability as a feature, supports the routing story.

**Defer (v2+ — explicit anti-features for this POC):**
- Local LLM inference (Ollama/llama.cpp), real graph DB (Neo4j), hybrid+rerank retrieval, cell-level table Q&A, multi-user/auth, persistent cross-session chat history, PII redaction, bulk/enterprise ingestion. All explicitly out of scope per PROJECT.md or category-baseline overkill for a 1-week POC.

### Architecture Approach

The standard RAG-POC layout: a thin Streamlit `app.py` composing **`ui/` view partials**, calling **`pipelines/`** (ingest, query, summarize, graph) which orchestrate **`core/`** capabilities (extractor, ocr, chunker, embedder, vectorstore, retriever, llm_client) plus a separate **`routers/`** policy module and externalized **`prompts/`** templates. All mutable state lives under `data/` (uploads hashed by content, Chroma directory, OCR cache, bundled samples) so `make clean` is one command. This separation keeps Streamlit out of the core logic, makes every step unit-testable, and lets the same pipelines be driven from a CLI later.

**Major components:**
1. **`core/` (capabilities)** — `extractor` (PyMuPDF + scanned detection), `ocr` (EasyOCR lazy-loaded), `chunker` (structure-aware ~500–800 token chunks, ~100–150 overlap), `embedder` (NIM via OpenAI-compat), `vectorstore` (Chroma `PersistentClient` façade with `doc_id` filtering + `delete_by_doc`), `retriever`, `llm_client` (retry/backoff, 60s timeout, JSON mode), `config` (pydantic-settings reading `.env.local`).
2. **`pipelines/` (orchestration)** — `ingest` (extract → OCR-fallback → chunk → embed → persist, idempotent on content hash), `query` (route → embed → retrieve → prompt → LLM → cited answer), `summarize` (map-reduce), `graph` (retrieve → JSON-mode LLM → Pydantic validate → render).
3. **`routers/model_router.py`** — pure function `route(task, signals) → RouteDecision(model, reason)`; the `reason` string is the demo's hero.
4. **`ui/` (Streamlit partials)** — `upload`, `chat`, `summary_view`, `graph_view`, `sidebar` (routing toggle, doc list, reset). `app.py` stays a thin composition root.
5. **Persistence under `data/`** — `data/uploads/{sha256}.{ext}`, `data/cache/{sha256}.json` (extracted text + OCR), `data/chroma/`, `data/samples/` (committed). Everything except `samples/` is git-ignored and wiped by `make clean`.

### Critical Pitfalls

These are the design-around items — every one should be addressed by phase 1 patterns, not retrofitted later.

1. **NVIDIA free-tier 504/429 storms during demos** — 70B models routinely take 20–40s; bulk embedding can burn the per-minute quota in seconds. **Mitigate:** 60s+ timeouts, exponential backoff with jitter on 429/504, **batch embeddings (32–64 chunks/call)**, env-configurable fallback model (`llama-3.1-8b-instruct`), and `st.cache_data` on the canned demo questions.
2. **Embedding model mismatch between ingest and query** — silent retrieval failure (nearest neighbors look random) or hard `InvalidDimensionException`. **Mitigate:** single `EMBEDDING_MODEL` constant imported by both paths; **store `embedding_model` + `embedding_dim` in ChromaDB collection metadata and assert on startup**; version collection name when switching models — never reuse an index across models.
3. **EasyOCR + Streamlit re-instantiation + first-run download** — silent 2–5 min download of ~2GB on first use; Reader re-allocates ~1–2GB per Streamlit rerun if not cached. **Mitigate:** `@st.cache_resource` on the Reader; English-only (`['en']`); `gpu=False` explicit; **pre-download weights in `make setup`** so the first user-facing run is instant.
4. **PDF text extraction garbage on scanned/multi-column/tables, then chunking that mid-splits rows** — confidently-cited wrong answers. **Mitigate:** PyMuPDF (not pypdf) for column/layout awareness; per-page `len(text.strip()) < 50` heuristic → fall back to OCR; detect tables and emit each as an **atomic chunk with `chunk_type:"table"` metadata + heading prefix**; structure-aware splitter (`\n\n` → `\n` → sentence → char), never split inside tables/lists/headings.
5. **Hallucinated citations + "lost in the middle"** — fluent answers citing chunks that don't contain the claim. **Mitigate:** system prompt forces "answer only from context, say 'I don't know' otherwise, cite as `[chunk_id]`"; pass chunks as a numbered list with explicit IDs; **validate every cited ID against the retrieval log post-hoc and flag hallucinated IDs in the UI**; keep top-k=3–5; reorder so highest-scored chunk appears first AND last.
6. **Routing comparison apples-to-oranges** — caching, sequential warm-up, or drifted prompts make the comparison meaningless. **Mitigate:** disable caching in the comparison panel; **identical** system prompt / user prompt / retrieved chunks / temperature — only the model differs; run both calls in parallel via `asyncio.gather`; report tokens + latency for both; UI banner: "concept demo, not benchmark."

## Implications for Roadmap

The build order is dictated by integration risk and the fact that every step beyond phase 7 is cuttable. The riskiest integrations (NVIDIA API, OCR, vector persistence) front-load; phase 7 produces a usable end-to-end demo; phases 8–11 are pure value-add on top.

### Phase 1: Skeleton, config, and packaging
**Rationale:** Hits the ≤3-command-setup constraint immediately and establishes the layout every later phase plugs into. Mistakes here (hardcoded paths, no `.env.local.example`, unpinned torch wheel) compound across every later phase.
**Delivers:** `pyproject.toml` (uv), `Makefile` (`setup`/`run`/`clean`/`doctor`), `app.py` hello-world Streamlit page, `core/config.py` reading `.env.local`, `.env.local.example`, `.gitignore`, `data/samples/` with bundled PDFs, README quickstart.
**Addresses:** "One-command setup", "API key from `.env.local`", "Demo-ready end-to-end" prerequisites.
**Avoids:** Pitfall #12 (torch/OS divergence) via CPU-only torch wheel pin + `uv`; lays groundwork for #1 (EasyOCR pre-download in `make setup`).

### Phase 2: NVIDIA NIM client with retry, timeout, and fallback
**Rationale:** Most failure-prone integration. Building the resilient client *before* anything calls it means every later phase inherits backoff, batching, and the fallback-model toggle for free.
**Delivers:** `core/llm_client.py` (port `test-nvidia.mjs` to Python via `openai` SDK with `base_url`); 60s timeout; retry+jitter on 429/504; batch embeddings helper; env-configurable `NVIDIA_MODEL` / `NVIDIA_ROUTE_MODEL` / `NVIDIA_EMBED_MODEL`; smoke test asserting JSON-mode round-trip.
**Uses:** `openai`, `python-dotenv`, NIM OpenAI-compatible endpoint.
**Avoids:** Pitfall #5 (rate limits + 504 storms) — entirely.

### Phase 3: Extractor + OCR with branching ingestion
**Rationale:** Second-riskiest integration; OCR weight download and table/column handling have to be solved before chunking sees the text. Test fixtures (digital + scanned + multi-column + table PDF) gate the rest of the pipeline.
**Delivers:** `core/extractor.py` (PyMuPDF, page-level records, table detection → atomic markdown chunks, `needs_ocr` heuristic), `core/ocr.py` (`@st.cache_resource` EasyOCR, English-only, CPU), per-page extraction-method metadata, content-hash cache in `data/cache/`.
**Implements:** Architecture pattern 2 (text-first, OCR fallback).
**Avoids:** Pitfalls #1 (EasyOCR bloat), #2 (extraction garbage), #3 (tables destroyed).

### Phase 4: Chunker + embedder + ChromaDB vector store
**Rationale:** The retrieval-quality lever. Wrong choices here are invisible until phase 7 produces wrong answers; correct collection metadata (model name + dim) prevents the worst class of silent bug.
**Delivers:** Structure-aware `core/chunker.py` (500–800 tokens, 100–150 overlap, atomic tables/headings, doc-title prefix), `core/embedder.py` (batched NIM calls), `core/vectorstore.py` (Chroma `PersistentClient`, telemetry off, `doc_id`-filtered query, `delete_by_doc`, **collection metadata stores `embedding_model` + `embedding_dim` and asserts on open**).
**Avoids:** Pitfalls #4 (model mismatch), #6 (chunking mistakes), #7 (Chroma telemetry/persistence).

### Phase 5: Ingestion pipeline + Upload UI
**Rationale:** First end-to-end vertical slice — proves phases 1–4 compose. Content-hash dedupe gives idempotent re-uploads, which the demo workflow relies on.
**Delivers:** `pipelines/ingest.py` (hash → cache check → extract → OCR-fallback → chunk → embed → persist), `ui/upload.py` with `st.status` progress, sample-doc quick-load.
**Addresses:** Ingestion + persistence requirements end-to-end.
**Avoids:** Pitfall #11 (Streamlit reruns) via `@st.cache_resource` for clients and content-hash skip-if-exists.

### Phase 6: Retriever + Q&A pipeline + Chat UI with citations
**Rationale:** This phase is the demo. After this lands, the POC is presentable; everything later upgrades the story.
**Delivers:** `core/retriever.py`, `pipelines/query.py` (top-k=5, reorder so best chunk is first AND last), `prompts/qa.txt` (grounding instruction, "I don't know" fallback, `[chunk_id]` citation format), `ui/chat.py` with inline expandable citations, **post-hoc citation-ID validation against retrieval log**, API errors surfaced via `st.error`.
**Avoids:** Pitfall #8 (hallucinated citations + lost-in-the-middle).

### Phase 7: Summarization + Graph extraction (parallelizable)
**Rationale:** Both depend only on phase 6 retrieval and the LLM client. The graph extractor is the second POC differentiator; its Pydantic schema + JSON-mode + one-shot self-correct retry has to be solid before the visual renderers go on top.
**Delivers:** `pipelines/summarize.py` (map-reduce, `prompts/summary.txt`), `pipelines/graph.py` (`response_format={"type":"json_object"}`, Pydantic `Entity`/`Relationship`/`ProcessStep` models, fuzzy-merge entity dedup via `rapidfuzz`, deterministic IDs, one-shot self-correction on parse failure), `ui/summary_view.py`, `ui/graph_view.py` (table + simple node-edge view).
**Addresses:** Summarization + structured graph extraction scope items.
**Avoids:** Pitfall #9 (malformed JSON, entity duplication).

### Phase 8: Model router + manual toggle + token/latency display
**Rationale:** Hooks into every existing pipeline call site. Building it as a pure function with explainable output (`reason` string) makes the routing concept tangible — the demo's hero moment.
**Delivers:** `routers/model_router.py` (`route(task, signals) → RouteDecision(model, reason)`), sidebar toggle (`auto`/`small`/`large`), per-call token/latency badge surfaced everywhere LLM calls happen, "routed via X because Y" rendered in chat.
**Addresses:** "Model routing concept demo" scope item.

### Phase 9: Side-by-side routing comparison + auto-routing rules
**Rationale:** The strongest demo moment. Requires phase 8 (router exists) + parallel-safe LLM client (phase 2). Caching must be disabled in this panel specifically — Pitfall #10 lives or dies here.
**Delivers:** Two-column Streamlit panel, identical inputs to both models via `asyncio.gather`, min/median/max over ≥3 runs, "concept demo, not benchmark" disclaimer, simple rule-based auto-router (`task` + `doc_chars` length signals) with visible decision reason.
**Avoids:** Pitfall #10 (apples-to-oranges comparison).

### Phase 10: Polish — streaming, "Why this answer?", export, demo readiness
**Rationale:** Every item here is cuttable but cheap and high-impact for live demos. Pre-warmed sample docs + Markdown export are the lowest-effort/highest-value picks.
**Delivers:** Streaming answers via `st.write_stream` over NIM SSE, "Why this answer?" panel (chunks + scores + model used), Markdown export of answer + citations, sidebar reset, `make doctor` env-check script, README polish, demo dry-run on a fresh Windows + macOS machine.
**Avoids:** Pitfall #11 residuals (rerun cost, upload size, streaming threading).

### Phase Ordering Rationale

- **Risk-first ordering:** NVIDIA client (phase 2) and OCR/extraction (phase 3) are the two integrations most likely to derail the timeline. Vector store + collection metadata (phase 4) closes off the worst class of silent bug. By phase 5 every risky integration has been touched.
- **Demo-usable by phase 6:** Phases 1–6 deliver the locked-scope core (upload → ask → cited answer). Everything beyond is upgrade-not-blocker, so the schedule has natural stop points.
- **Differentiators sequenced so they reinforce each other:** Phase 7 produces the JSON payload that phase 9's routing comparison can use as a non-trivial routing target ("graph extraction → large model"). Phase 8 wires the router everywhere phase 7 added a call site, so phase 9's parallel-call panel is just composition.
- **Anti-pitfall patterns are phase-1 and phase-2 patterns:** `@st.cache_resource`, batched embeddings with retry, collection metadata, fallback model env var, content-hash dedupe — all locked in before any feature work.

### Research Flags

Phases likely needing deeper research during planning (run `/gsd-research-phase`):

- **Phase 7 (graph extraction)** — JSON-mode + schema-strict prompts on llama-3.1 vary in reliability; the few-shot prompt design and the fuzzy-merge thresholds for entity dedup deserve a focused research pass.
- **Phase 9 (side-by-side routing)** — choosing the smaller routing-target model (8b vs mistral-7b vs mixtral) on the NVIDIA catalog and confirming free-tier behavior under parallel calls is worth a quick research spike.

Phases with standard patterns (skip research-phase):

- **Phase 1 (skeleton)** — uv + Makefile + Streamlit are well-documented; STACK.md already names exact versions.
- **Phase 2 (NIM client)** — `test-nvidia.mjs` is the in-repo reference; OpenAI SDK pattern is one-to-one.
- **Phase 3 (extractor + OCR)** — PyMuPDF + EasyOCR + pdf2image are stable; ARCHITECTURE.md and PITFALLS.md have the patterns.
- **Phase 4 (chunker + Chroma)** — covered in detail in PITFALLS.md and ARCHITECTURE.md.
- **Phase 5 (ingestion + upload UI)** — pure composition.
- **Phase 6 (retriever + chat)** — standard RAG; grounding-prompt + citation-validation patterns documented in PITFALLS #8.
- **Phase 8 (router)** — pure function over an enum; ARCHITECTURE pattern 5 covers it.
- **Phase 10 (polish)** — Streamlit conventions documented in PITFALLS #11.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Constraints lock most choices; LlamaIndex vs LangChain decision is well-justified; only ambiguity is patch-level versions, resolved at `uv lock` time. |
| Features | HIGH | Mature product category (ChatPDF/NotebookLM/AnythingLLM) with well-known table-stakes; differentiators come straight from PROJECT.md. |
| Architecture | HIGH | Standard RAG-POC layout; `core/` + `pipelines/` + `ui/` + `routers/` + `prompts/` split is battle-tested across LlamaIndex/LangChain reference apps. |
| Pitfalls | HIGH | Each of the 12 pitfalls is sourced from official-docs/community-issue-tracker patterns; prevention strategies are concrete and code-level. |

**Overall confidence:** HIGH

### Gaps to Address

- **Exact patch versions (Streamlit 1.40 vs 1.42, Chroma 0.5 vs 0.6, llama-index-core 0.12.x).** Resolve at install time with `uv lock --upgrade`; floor versions in STACK.md are safe.
- **Choice of routing-target small model on NVIDIA's catalog (`meta/llama-3.1-8b-instruct` vs `mistralai/mixtral-8x7b-instruct-v0.1` vs `mistralai/mistral-7b-instruct-v0.3`).** Decide during phase 9 planning based on free-tier availability the day of build; keep the env var configurable.
- **Free-tier daily call budget envelope.** Not formally measured — phase 10 polish should add a "calls today" counter and document the empirical budget for live-demo planning.
- **PyMuPDF AGPL license stance.** Acceptable for a POC; flag for re-evaluation if/when this work moves toward distribution. Drop-in alternative is `pdfplumber` (MIT) at ~3× slowdown on large PDFs.
- **GPU vs CPU for EasyOCR.** Default to CPU per "minimal install" goal; surface as an env flag so a CUDA-equipped demo machine gets 5–10× faster OCR if available.

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` — full stack rationale, version pins, alternatives, NIM integration pattern.
- `.planning/research/FEATURES.md` — table-stakes/differentiator/anti-feature breakdown vs comparable products.
- `.planning/research/ARCHITECTURE.md` — folder structure, component boundaries, build-order, data flows.
- `.planning/research/PITFALLS.md` — 12 critical pitfalls with prevention + recovery + phase mapping.
- `.planning/PROJECT.md` — locked constraints, requirements, decisions.
- `test-nvidia.mjs` (in-repo) — verified NIM auth pattern, base URL, default model, JSON-mode support.
- NVIDIA NIM API docs, Chroma docs, LlamaIndex docs, Streamlit docs, EasyOCR README, PyMuPDF docs, Astral `uv` docs (all linked in STACK.md / PITFALLS.md).

### Secondary (MEDIUM confidence)
- "Lost in the Middle" (Liu et al., 2023) — informs top-k=3–5 + chunk reordering in phase 6.
- LangChain / LlamaIndex `chat-with-your-docs` reference apps — informed feature baseline and architecture layout.
- Community issue trackers (EasyOCR, ChromaDB, Streamlit) — informed pitfalls #1, #7, #11.

### Tertiary (LOW confidence)
- Exact patch versions of Streamlit / ChromaDB / llama-index-core current at build time — resolve via `uv lock --upgrade`.
- Free-tier per-minute / per-day quota numbers for individual NVIDIA models — observed empirically in `test-nvidia.mjs`'s 504 handling; no published SLA.

---
*Research completed: 2026-04-28*
*Ready for roadmap: yes*

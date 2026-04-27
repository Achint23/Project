# Feature Research

**Domain:** Local document intelligence / RAG demo apps with semantic extraction
**Researched:** 2026-04-28
**Confidence:** HIGH (well-established product category — RAG demos, ChatPDF-class apps, LangChain/LlamaIndex sample apps, NotebookLM-style tools)

## Scope Note

This research covers the **demo POC** category specifically (single-user, local, "drop a doc → ask questions → see structure"). It is *not* enterprise document-AI scope. Reference points used: ChatPDF, AnythingLLM, PrivateGPT, LM Studio + RAG, NotebookLM, LangChain/LlamaIndex `chat-with-your-docs` reference apps, Streamlit RAG cookbook examples, and demo apps shipped by NVIDIA NIM, OpenAI, and Anthropic cookbooks.

## Feature Landscape

### Table Stakes (Users Expect These in *Any* Doc-Q&A Demo)

Missing these → the demo "feels broken" even if the model is great.

#### Ingestion

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Single-file upload via web UI (drag-drop or file picker) | Every ChatPDF-class demo opens with this | S | Streamlit `st.file_uploader` covers it natively |
| PDF support (text-based) | Default business doc format | S | `pypdf` / `pdfplumber` / LlamaIndex `PDFReader` |
| Scanned PDF / image PDF support (OCR) | POC scope explicitly requires it; users will test with scans | M | EasyOCR (per constraints) → image per page → OCR text |
| Image file support (PNG/JPG of a doc) | Natural extension once OCR is in | S | Same OCR pipeline |
| Visible upload progress / "processing…" state | Without it the demo feels frozen during embedding | S | Streamlit spinner/status |

#### Document Processing

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Plain text extraction (paragraphs) | Foundational | S | Library default |
| Page-aware extraction (page numbers preserved) | Required for citations later | S | Most PDF libs expose page index |
| Basic table-like content capture | Business docs have tables; losing them looks bad | M | `pdfplumber.extract_tables()` is the standard pragmatic choice; full table understanding is L and out of scope |
| Auto-detect "this PDF is scanned" → route to OCR | Users won't manually pick a pipeline | S | Heuristic: if extracted text length per page < threshold, fall back to OCR |

#### Indexing & Retrieval

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Chunking with overlap | RAG 101 | S | Recursive character splitter, ~500–1000 tokens, 10–15% overlap |
| Embeddings into a local vector store | Core of RAG | S | ChromaDB embedded (per constraints) |
| Semantic top-k retrieval | The whole point | S | Chroma `.query()` |
| Persistence between runs (don't re-embed each restart) | Demo restart pain otherwise | S | Chroma persistent client to disk |
| Per-document namespacing/collection | Required as soon as more than one doc is loaded | S | Chroma collection per doc or metadata filter |

#### Q&A Interaction

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Natural-language question box | Core | S | Streamlit `st.chat_input` |
| Answer rendered in the UI | Core | S | `st.chat_message` |
| Inline source citations (page / chunk reference) | Without this the demo isn't credible — "is it making this up?" | M | Return retrieved chunk metadata alongside answer; render as expandable "Sources" |
| Loading/"thinking" indicator | UX baseline | S | Streamlit status |

#### Summarization

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| One-click "Summarize this document" button | Standard demo feature | S | Map-reduce or stuff-prompt depending on doc size |
| Business-readable output (bullets / sections) | Per project Core Value | S | Prompt template |

#### Semantic / Graph Extraction (POC scope explicitly requires this)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Prompt-based entity extraction (people, orgs, systems, artifacts) | Required by scope | M | Structured-output prompt → JSON |
| Prompt-based relationship extraction (subject–predicate–object triples) | Required by scope | M | Same call or follow-up; constrain with JSON schema |
| Process steps + decision points + business rules extraction | Explicitly named in PROJECT.md requirements | M | Domain-tailored prompt with few-shot example |
| Structured JSON output (validated) | Needed for the "readable view" to render reliably | M | Pydantic model + JSON-mode prompt; retry on parse failure |
| Readable rendering of extracted graph (table or simple node/edge list) | Without rendering, JSON-only feels unfinished | M | `st.dataframe` for entities + edges list; pyvis/streamlit-agraph optional |

#### Model Routing (explicitly in scope)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Toggle / selector to switch between two NVIDIA-hosted models | Core "routing concept" demo | S | Two model IDs in config; UI radio |
| "Direct" vs "Routed" path side-by-side comparability | The whole point of the routing demo | M | Run same prompt through both, show both answers |
| Display which model answered | Trust/clarity | S | Badge on answer |

#### UX

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Conversation history within the session | Chat UX baseline | S | `st.session_state` |
| Show currently loaded document(s) | Users get lost otherwise | S | Sidebar list |
| Clear/reset session | Recover from bad state during a demo | S | Button → clear session_state |
| Sample-document quick-load | Demo readiness — presenter shouldn't fumble for files | S | Bundled samples + dropdown |

#### Ops / Observability (POC-grade)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| API errors surfaced in UI (not just console) | Demos die silently otherwise | S | Try/except → `st.error` |
| Token / latency display per call | Expected on a "routing" demo | S | NVIDIA response includes usage; wall-clock timer around call |

---

### Differentiators (Demo-Worthy, Set This POC Apart)

These are where the POC earns "oh nice" reactions. Pick the ones that align with the Core Value (drop → query → summarize → graph → routing).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Side-by-side **routing comparison view** (same Q → Model A vs Model B answers + latency + token cost) | Makes the routing concept *tangible* in one screen — the strongest demo moment | M | Two columns in Streamlit; one shared question input |
| **Auto-routing heuristic** (e.g., short factual Q → small model, multi-step / summarization → large model) with visible "router decision" reason | Elevates routing from "manual switch" to "intelligent dispatch" — demo storyline | M | Simple rule-based router (length + keyword) returning `{model, reason}`; no ML needed |
| **Graph view** of extracted entities/relationships (interactive nodes + edges) | Visually striking; differentiates from generic ChatPDF clones | M | `streamlit-agraph` or `pyvis`; feeds from extraction JSON |
| **Citations that highlight the source chunk** (expandable card showing the exact text that grounded the answer) | Trust + "wow" factor for business audience | M | Already have chunk + metadata from retrieval — just render |
| **Process-flow rendering** of extracted steps/decision points (mermaid diagram from JSON) | Direct payoff of the semantic-extraction scope; very demo-friendly | M | Prompt → JSON → render mermaid via `st.markdown` |
| **Unified "Document Insights" panel** (summary + key entities + key rules + open questions) generated in one pass | Single screen that proves "the system understood the doc" | M | One structured-output call; cached per doc |
| **Streaming answers** (token-by-token) | Modern chat UX expectation; cheap with NVIDIA NIM streaming | S | NIM supports SSE streaming |
| **Multi-document Q&A** within one session (ask across all loaded docs) | Goes beyond one-PDF demos | M | Query across collections / use metadata filter |
| **One-command setup (`make demo`) that loads sample docs pre-indexed** | Removes the "wait while it embeds" dead time at the start of a demo | S | Ship pre-built Chroma dir or auto-index on first run with progress |
| **Export answer + citations as Markdown** | Concrete artifact a stakeholder can take away | S | Format string → `st.download_button` |
| **"Why this answer?" panel** showing retrieved chunks, scores, and the model used | Observability as a feature — supports the routing story | S | Already have all the data |

---

### Anti-Features (Do **Not** Build for a POC of This Size)

Things people will ask for that would tank the timeline or muddy the demo.

| Feature | Why Requested | Why Problematic for This POC | Alternative |
|---------|---------------|------------------------------|-------------|
| Real graph database backend (Neo4j, etc.) | "It's a graph, so use a graph DB" | Out of scope per PROJECT.md; adds Docker dep, breaks "minimal install" | Prompt-extracted JSON + visual rendering — explicitly the chosen approach |
| Persistent multi-user accounts / auth | Sounds "production-ready" | Single-user demo; auth doubles UI surface and adds storage concerns | Out of scope — local single-user only |
| Cross-session persistent chat history with search | Feels chat-app-y | Adds DB, UX for browsing/threads; not part of Core Value | Session-only history; offer Markdown export |
| Custom embedding model fine-tuning | "Better retrieval" | Days of work, marginal POC payoff, free-tier API limits | Use a strong default embedding (NVIDIA NIM or `all-MiniLM-L6-v2`) and good chunking |
| Re-ranking with a second model on every query | Common RAG advice | Doubles latency + token cost on free tier; wins are small at demo scale | Tune chunk size / top-k first; add re-rank later only if retrieval visibly fails |
| Hybrid keyword + vector (BM25 + dense) | "Best practice in RAG blogs" | Adds an index, tuning surface, and another dependency | Vector-only is sufficient for a handful of sample docs |
| Bulk/batch ingestion of hundreds of docs with workers | "Will it scale?" | Out of scope — POC, small sample set | Document the small-sample assumption clearly |
| Full table understanding (cell-level Q&A, joins) | Business docs have tables | L complexity, fragile, eats most of the budget | `pdfplumber` table-to-text inclusion; don't promise table-cell Q&A |
| Real-time collaborative editing / comments | "Multi-user demo" | Out of scope; massive UX rework | Single user; export to share |
| Local LLM inference (Ollama, llama.cpp) | "Truly local" purity | Explicitly deferred; adds GBs of model download, GPU concerns, breaks "minimal install" | NVIDIA NIM hosted API per constraints |
| Production model-routing engine (cost-aware optimizer, fallback chains, circuit breakers) | "Real routing" | Concept demo only per scope | Two-model toggle + simple rule-based auto-router |
| PII detection / redaction pipeline | "Enterprise-ready" | Adds a model, UX, and false-positive handling | Note as future work |
| Voice input / TTS answers | "Modern AI demo" | Off-scope; dependency-heavy | Text only |
| Browser extension / desktop installer | "Easier to use" | Out of scope per PROJECT.md | Streamlit web UI |
| Vector store migration (Pinecone/Weaviate/Qdrant adapters) | Architectural flexibility | Premature abstraction for a POC | ChromaDB embedded only; isolate in one module if curious |
| Long-term conversation memory across documents | "Like ChatGPT" | Adds memory store, summarization-of-memory loops | Per-session only |

---

## Feature Dependencies

```
Ingestion (upload + format detect)
    └──requires──> Document Processing (text + OCR fallback)
                       └──requires──> Indexing (chunk + embed + Chroma persist)
                                          └──requires──> Retrieval (top-k semantic)
                                                             ├──requires──> Q&A (LLM call w/ retrieved context)
                                                             │                  ├──enhances──> Inline citations
                                                             │                  ├──enhances──> Streaming answers
                                                             │                  └──enhances──> "Why this answer?" panel
                                                             ├──requires──> Summarization (full-doc map-reduce)
                                                             └──requires──> Semantic / Graph Extraction (structured-output prompt)
                                                                                ├──enhances──> Graph view (nodes/edges render)
                                                                                ├──enhances──> Process-flow mermaid render
                                                                                └──enhances──> Unified "Document Insights" panel

Model Routing (model selector)
    ├──enhances──> Q&A
    ├──enhances──> Summarization
    ├──enhances──> Semantic Extraction
    └──requires──> Token/Latency display (to make the comparison meaningful)

Auto-routing heuristic
    └──requires──> Model Routing (manual selector)

Side-by-side routing comparison
    └──requires──> Model Routing + Token/Latency display

Multi-document Q&A
    └──requires──> Per-document namespacing in Chroma

Sample-document quick-load
    └──enhances──> Demo readiness (no dependency on others, but pairs with pre-indexed Chroma)
```

### Dependency Notes

- **OCR fallback depends on text-extraction first** — heuristic is "if text per page is below threshold, OCR." Don't OCR everything (slow on free CPU laptops).
- **Citations depend on retrieval returning chunk metadata** — make sure the retrieval layer always passes `{page, chunk_id, score}` upward; retrofitting later is painful.
- **Graph view, process flow, and Insights panel all share one structured-output extraction call** — design the JSON schema once; renderers are downstream and cheap.
- **Auto-routing requires manual routing first** — manual toggle proves the wiring works; auto layer is a router function over the same call site.
- **Side-by-side comparison requires the call layer to be idempotent and parallelizable** — wrap the LLM call so it can be invoked twice with different model IDs cleanly.
- **Multi-document Q&A conflicts with naive single-collection design** — choose per-document collections OR consistent metadata filtering on day one; switching later means re-embedding.
- **Streaming and side-by-side comparison have a mild UX conflict** — streaming two columns at once works in Streamlit but flickers; acceptable, just be aware.

---

## MVP Definition

### Launch With (v1 — the demo must do these end-to-end)

The non-negotiable Core Value path: **drop doc → ask → summarize → see graph → toggle routing.**

- [ ] PDF + scanned-PDF + image upload via Streamlit — proves ingestion claim
- [ ] Auto-detect scanned vs text PDF; route to EasyOCR when needed — meets "scanned doc" requirement
- [ ] Page-aware text extraction with basic table capture (`pdfplumber`) — meets "tables and structure"
- [ ] Chunk + embed + persist into ChromaDB on disk — meets "local vector store"
- [ ] Semantic top-k retrieval — meets "contextual retrieval"
- [ ] Q&A chat with **inline citations (page + snippet)** — required for credibility
- [ ] One-click document summarization with business-readable output — meets summarization requirement
- [ ] Prompt-based extraction of entities, relationships, process steps, decision points, business rules → validated JSON + readable table view — explicit scope item
- [ ] Manual model selector between two NVIDIA-hosted models — meets "routing concept demo"
- [ ] Per-call token + latency display — needed to make routing comparison meaningful
- [ ] Bundled sample documents loadable from sidebar — demo-readiness requirement
- [ ] One-command setup (`make setup && make run` or `uv sync && streamlit run app.py`) — explicit constraint
- [ ] API errors surfaced in UI — demos die silently otherwise

### Add After v1 Works (v1.x — high-leverage demo upgrades)

Add only after the end-to-end path is solid; each one strengthens the demo story.

- [ ] Side-by-side routing comparison view (same Q → both models, both answers, both latencies) — trigger: v1 demo lands and the routing story needs more punch
- [ ] Simple rule-based auto-routing with visible "router decision" reason — trigger: side-by-side works
- [ ] Graph view (nodes/edges) of extracted entities — trigger: extraction JSON is stable
- [ ] Mermaid process-flow rendering of extracted steps/decisions — trigger: extraction JSON is stable
- [ ] Unified "Document Insights" panel (summary + entities + rules + open questions in one pass) — trigger: extraction prompts are reliable
- [ ] Streaming answers via NIM SSE — trigger: base Q&A works
- [ ] Multi-document Q&A across all loaded docs — trigger: per-doc collections already in place
- [ ] Markdown export of answer + citations — trigger: citations are rendered
- [ ] "Why this answer?" panel (retrieved chunks + scores + model used) — trigger: observability gap surfaced in early demos

### Future Consideration (v2+ — explicitly deferred)

Keep these on a "not now" list to deflect scope creep.

- [ ] Local LLM inference (Ollama / llama.cpp) — defer: explicit Out of Scope
- [ ] Real graph database (Neo4j) — defer: explicit Out of Scope
- [ ] Re-ranking and hybrid (BM25 + vector) retrieval — defer: marginal at demo scale
- [ ] Bulk/enterprise ingestion + worker pool — defer: explicit Out of Scope
- [ ] Multi-user, auth, sharing — defer: explicit Out of Scope
- [ ] Cell-level table Q&A — defer: HIGH cost, low POC payoff
- [ ] PII detection / redaction — defer: separate concern
- [ ] Persistent cross-session chat history with search — defer: not part of Core Value

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| PDF / scanned / image ingestion + OCR fallback | HIGH | MEDIUM | P1 |
| Chunk + embed + Chroma persistence | HIGH | LOW | P1 |
| Semantic Q&A with inline citations | HIGH | MEDIUM | P1 |
| One-click document summarization | HIGH | LOW | P1 |
| Structured semantic/graph extraction (entities, relations, steps, rules) | HIGH | MEDIUM | P1 |
| Manual model selector (routing concept) | HIGH | LOW | P1 |
| Token + latency display per call | MEDIUM | LOW | P1 |
| Bundled sample docs + one-command run | HIGH | LOW | P1 |
| API error surfacing in UI | MEDIUM | LOW | P1 |
| Side-by-side routing comparison | HIGH | MEDIUM | P2 |
| Auto-routing rule-based router with reason | HIGH | MEDIUM | P2 |
| Graph view (nodes/edges) | HIGH | MEDIUM | P2 |
| Mermaid process-flow render | MEDIUM | MEDIUM | P2 |
| Unified Document Insights panel | HIGH | MEDIUM | P2 |
| Streaming answers | MEDIUM | LOW | P2 |
| Multi-document Q&A | MEDIUM | MEDIUM | P2 |
| Markdown export of answer + citations | MEDIUM | LOW | P2 |
| "Why this answer?" panel | MEDIUM | LOW | P2 |
| Local LLM inference | LOW (for POC) | HIGH | P3 |
| Neo4j graph backend | LOW (for POC) | HIGH | P3 |
| Hybrid + re-ranking retrieval | LOW (for POC) | MEDIUM | P3 |
| Cell-level table Q&A | LOW (for POC) | HIGH | P3 |
| Auth / multi-user | LOW (for POC) | HIGH | P3 |

**Priority key:**
- **P1** — Must have for the v1 demo (covers PROJECT.md Active requirements end-to-end)
- **P2** — Should have; add after P1 lands to upgrade the demo story
- **P3** — Future / deferred (matches Out of Scope)

---

## Comparable Product Feature Snapshot

How comparable products handle the key features (informs our approach, not a copy target).

| Feature | ChatPDF / AskYourPDF | NotebookLM | AnythingLLM / PrivateGPT | LangChain `chat-with-your-docs` sample | **DocBot (our approach)** |
|---------|----------------------|------------|--------------------------|-----------------------------------------|---------------------------|
| Ingestion | Single PDF, drag-drop | Multi-source (PDFs, URLs, slides) | Multi-format batch | Single-doc tutorial | PDF + scanned + image; sample docs preloaded |
| OCR | Limited | Yes | Plugin-dependent | Not in base sample | EasyOCR auto-fallback |
| Chunking / embed | Hidden | Hidden | Configurable | Exposed in code | Recursive chunker, Chroma persistent |
| Citations | Page-cite popup | Per-claim citations w/ source panel | Source list | Optional | Inline + expandable source chunk |
| Summarization | One-click | Multi-summary types | One-click | Manual | One-click, business-readable prompt |
| Entity / graph extraction | No | Limited (study guides) | No | No | **Yes — explicit POC differentiator (entities, relations, process steps, rules) + visual render** |
| Model choice | Hidden | Hidden | User-selectable | User-selectable | **Two NVIDIA models, manual + rule-based auto-router** |
| Routing comparison view | No | No | No | No | **Yes — side-by-side comparison is a unique demo moment** |
| Latency / token display | No | No | Sometimes | No | Yes (supports routing story) |
| Local-only deployment | No (SaaS) | No (SaaS) | Yes | Optional | Yes (app local, LLM via NVIDIA API) |

**What this tells us:** The two clearest spaces to differentiate are (1) **explicit semantic/graph extraction with visual rendering** and (2) **the routing comparison story with observable latency/tokens**. Both are already in PROJECT.md scope. Everything else should match category baseline — don't try to out-ChatPDF ChatPDF on basic Q&A.

---

## Sources

- PROJECT.md (DocBot scope, constraints, decisions) — primary input
- ChatPDF, AskYourPDF — category baseline for single-doc Q&A demos
- NotebookLM (Google) — citations + multi-summary patterns
- AnythingLLM, PrivateGPT — local-first RAG feature surface
- LangChain `chat-with-your-data` and LlamaIndex `chat-with-pdfs` reference apps — minimal RAG demo shape
- NVIDIA NIM cookbook examples — model usage + streaming patterns
- Streamlit RAG cookbook — UI patterns for chat + sources
- pdfplumber / pypdf docs — table + page extraction tradeoffs
- ChromaDB docs — persistent client + per-collection patterns
- EasyOCR docs — pure-Python OCR install path

**Confidence:** HIGH for category feature set (well-established product pattern); MEDIUM-HIGH on specific complexity ratings (depend on chosen orchestration lib — LangChain vs LlamaIndex — which is still pending per PROJECT.md Key Decisions).

---
*Feature research for: local document intelligence / RAG demo apps with semantic extraction*
*Researched: 2026-04-28*

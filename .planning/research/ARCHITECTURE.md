# Architecture Research

**Domain:** Local-deployable RAG + document-intelligence POC (Python + Streamlit + ChromaDB + EasyOCR + NVIDIA NIM)
**Researched:** 2026-04-28
**Confidence:** HIGH (standard RAG POC patterns are well-established; folder layout and component boundaries derived from common LangChain/LlamaIndex + Streamlit reference projects)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                      UI LAYER (Streamlit single page)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Upload   │ │ Q&A Chat │ │ Summary  │ │ Graph    │ │ Routing    │ │
│  │ widget   │ │ panel    │ │ panel    │ │ view     │ │ toggle     │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘ │
│       │            │            │            │              │        │
├───────┴────────────┴────────────┴────────────┴──────────────┴────────┤
│                       ORCHESTRATION / PIPELINES                       │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────┐  │
│  │ Ingestion Pipeline  │  │  Query Pipeline     │  │ Graph Pipeline│  │
│  │ extract→chunk→embed │  │ retrieve→prompt→LLM │  │ retrieve→LLM │  │
│  └──────────┬──────────┘  └──────────┬──────────┘  └──────┬───────┘  │
├─────────────┼────────────────────────┼────────────────────┼──────────┤
│             ▼                        ▼                    ▼          │
│                            CORE COMPONENTS                            │
│  ┌──────────┐ ┌──────┐ ┌────────┐ ┌──────────┐ ┌─────────┐ ┌──────┐  │
│  │Extractor │ │ OCR  │ │Chunker │ │ Embedder │ │Retriever│ │Router│  │
│  │(pypdf)   │ │EasyOCR│ │(text)  │ │ (model)  │ │(Chroma) │ │      │  │
│  └────┬─────┘ └──┬───┘ └───┬────┘ └────┬─────┘ └────┬────┘ └──┬───┘  │
│       │          │         │           │            │         │      │
│       │          │         │           │            │         ▼      │
│       │          │         │           │            │   ┌──────────┐ │
│       │          │         │           │            │   │LLM Client│ │
│       │          │         │           │            │   │(NVIDIA)  │ │
│       │          │         │           │            │   └─────┬────┘ │
├───────┴──────────┴─────────┴───────────┴────────────┴─────────┴──────┤
│                          PERSISTENCE LAYER                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│  │ data/uploads/    │  │ data/chroma/     │  │ data/cache/      │    │
│  │ (raw documents)  │  │ (vector store)   │  │ (OCR/extract)    │    │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                       ┌────────────────────┐
                       │  NVIDIA NIM API    │
                       │  (hosted LLMs)     │
                       └────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **UI Layer** | File upload, chat input, summary/graph rendering, routing toggle, session state | `streamlit` widgets in `app.py` (+ `ui/` partials) |
| **Ingestion Pipeline** | Orchestrate extract → OCR-fallback → chunk → embed → persist for one document | `pipelines/ingest.py` |
| **Query Pipeline** | Retrieve top-k chunks → assemble prompt → call LLM → format answer + citations | `pipelines/query.py` |
| **Graph Pipeline** | Retrieve doc context → run extraction prompt → parse JSON → render | `pipelines/graph.py` |
| **Extractor** | Pull text from native PDFs; detect "scanned" pages; emit page-level records | `pypdf` / `pdfplumber` in `core/extractor.py` |
| **OCR Pipeline** | Rasterize PDF page → run EasyOCR → return text per page | `pdf2image` + `easyocr` in `core/ocr.py` |
| **Chunker** | Split extracted text into overlapping chunks with metadata (doc_id, page, source) | RecursiveCharacterTextSplitter in `core/chunker.py` |
| **Embedder** | Convert chunk text → vector (local sentence-transformers OR NVIDIA embed API) | `core/embedder.py` |
| **Vector Store Wrapper** | Thin façade over Chroma: `add()`, `query()`, `delete_by_doc()` | `core/vectorstore.py` (wraps `chromadb.PersistentClient`) |
| **Retriever** | Embed query → vector store query → optional MMR/dedup → return chunks | `core/retriever.py` |
| **Summarizer** | Map-reduce or stuff-style summary prompt over doc chunks | `pipelines/summarize.py` + `prompts/summary.txt` |
| **Graph Extractor** | Prompt LLM to emit entities/relationships JSON; validate schema | `pipelines/graph.py` + `prompts/graph.txt` |
| **Model Router** | Decide which NVIDIA model to call given task + signals; record routing reason | `routers/model_router.py` |
| **LLM Client** | HTTP wrapper around NVIDIA NIM `/chat/completions`; retries, timeout, JSON mode | `core/llm_client.py` |
| **Config / Env** | Load `.env.local`, expose typed settings (`NVIDIA_API_KEY`, paths, model names) | `core/config.py` (pydantic-settings or simple dataclass) |
| **Persistence** | Disk-backed: uploads, Chroma DB, OCR cache | `data/` (git-ignored) |

## Recommended Project Structure

```
docbot/
├── app.py                          # Streamlit entrypoint (single command target)
├── core/                           # Pure, side-effect-light building blocks
│   ├── __init__.py
│   ├── config.py                   # Settings loaded from .env.local
│   ├── extractor.py                # PDF text extraction + scanned-page detection
│   ├── ocr.py                      # EasyOCR wrapper (lazy-loaded reader)
│   ├── chunker.py                  # Text splitting + chunk metadata
│   ├── embedder.py                 # Embedding model interface
│   ├── vectorstore.py              # Chroma wrapper (collection per project, doc_id metadata)
│   ├── retriever.py                # Vector search + MMR/dedup
│   ├── llm_client.py               # NVIDIA NIM HTTP client (retry, timeout, JSON mode)
│   └── logging.py                  # Structured console logging
├── pipelines/                      # End-to-end workflows composed from core
│   ├── __init__.py
│   ├── ingest.py                   # upload → extract → (OCR?) → chunk → embed → persist
│   ├── query.py                    # question → retrieve → prompt → LLM → answer
│   ├── summarize.py                # doc_id → chunks → map-reduce summary
│   └── graph.py                    # doc_id → chunks → extraction prompt → JSON graph
├── routers/                        # Model selection
│   ├── __init__.py
│   └── model_router.py             # route(task, signals) → model_name + reason
├── prompts/                        # Externalized prompt templates (plain .txt or .md)
│   ├── qa.txt
│   ├── summary.txt
│   ├── graph.txt
│   └── system.txt
├── ui/                             # Streamlit view fragments (kept thin)
│   ├── __init__.py
│   ├── upload.py
│   ├── chat.py
│   ├── summary_view.py
│   ├── graph_view.py
│   └── sidebar.py                  # Routing toggle, doc list, settings
├── data/                           # Git-ignored runtime state
│   ├── uploads/                    # Raw uploaded files (named by content hash)
│   ├── chroma/                     # ChromaDB persistent directory
│   ├── cache/                      # Extracted text + OCR results (by content hash)
│   └── samples/                    # Bundled demo docs (committed, small)
├── tests/
│   ├── test_chunker.py
│   ├── test_extractor.py
│   ├── test_router.py
│   └── fixtures/
├── .env.local.example              # Template for NVIDIA_API_KEY etc.
├── .gitignore                      # Excludes data/uploads, data/chroma, data/cache, .env.local
├── pyproject.toml                  # uv / pip deps + tool config
├── Makefile                        # `make setup`, `make run`, `make clean`
└── README.md
```

### Structure Rationale

- **`app.py` at root:** Streamlit's idiomatic entrypoint; enables `streamlit run app.py` as the single run command.
- **`core/` vs `pipelines/`:** Core modules are reusable, testable units with no Streamlit imports. Pipelines compose them into end-to-end workflows. This keeps the LLM/RAG logic decoupled from the UI and makes unit-testing trivial.
- **`routers/` separated from `core/`:** Routing is a *policy* concern (which model to call), not a *capability* concern. Isolating it lets the routing demo evolve (rules → ML-based) without touching the LLM client.
- **`prompts/` as plain text files:** Externalized so non-developers can iterate; loaded at runtime, not embedded in code. Makes A/B-ing prompts during the demo easy.
- **`ui/` for view partials:** Streamlit `app.py` stays a thin composition root; each tab/section lives in its own module. Avoids the common Streamlit anti-pattern of one 1000-line `app.py`.
- **`data/` for everything mutable:** One directory to wipe (`make clean`) for a fresh demo. Git-ignored except `data/samples/`.
- **Single `pyproject.toml` + `Makefile`:** Hits the "≤ 3 commands to setup" constraint (see [Packaging](#packaging-implications--3-command-setup)).

## Architectural Patterns

### Pattern 1: Pipeline = thin orchestrator over `core/` primitives

**What:** Each pipeline function takes inputs (path/doc_id/question), calls core modules in order, returns a structured result. Pipelines own *flow*; core owns *capability*.

**When to use:** Always for this POC. Keeps Streamlit handlers tiny and tests fast.

**Trade-offs:**
- ✅ Each pipeline step is independently testable and swappable.
- ✅ Streamlit can be replaced by a CLI or FastAPI without touching pipeline code.
- ❌ Slight boilerplate for very small flows; acceptable for clarity.

**Example:**
```python
# pipelines/ingest.py
def ingest_document(file_path: Path) -> IngestResult:
    doc_id = hash_file(file_path)
    if vectorstore.has_doc(doc_id):
        return IngestResult(doc_id=doc_id, status="cached")

    pages = extractor.extract(file_path)
    if extractor.is_scanned(pages):
        pages = ocr.run(file_path)

    chunks = chunker.split(pages, doc_id=doc_id)
    vectors = embedder.embed_many([c.text for c in chunks])
    vectorstore.add(chunks, vectors)
    return IngestResult(doc_id=doc_id, status="ingested", n_chunks=len(chunks))
```

### Pattern 2: Branching extractor (text-first, OCR fallback)

**What:** Always try fast native PDF text extraction first; fall back to OCR only when a page yields too little text (heuristic: `< 50 chars` or `< 0.05 chars/pixel`).

**When to use:** Any document pipeline mixing native PDFs and scans. Saves seconds-to-minutes per doc on the demo.

**Trade-offs:**
- ✅ Fast path for clean PDFs; slow path only when needed.
- ❌ Heuristic can mis-classify mixed-quality PDFs; surface the choice in logs.

**Example:**
```python
# core/extractor.py
def extract(path: Path) -> list[Page]:
    pages = [Page(num=i, text=p.extract_text() or "") for i, p in enumerate(PdfReader(path).pages)]
    return pages

def needs_ocr(page: Page) -> bool:
    return len(page.text.strip()) < 50
```

### Pattern 3: Vector store wrapper with `doc_id` metadata

**What:** Wrap Chroma in a small façade. Every chunk carries `{doc_id, page, source}` metadata so retrieval can be scoped to a single doc, and deletion is one call.

**When to use:** Any multi-doc RAG app — including this POC, since the demo loads several samples.

**Trade-offs:**
- ✅ Trivial per-doc reset (`vectorstore.delete_by_doc(doc_id)`).
- ✅ Allows "ask only about this doc" filter in UI.
- ❌ Wrapper adds a layer; worth it for testability (swap to FAISS/Qdrant later).

**Example:**
```python
# core/vectorstore.py
class VectorStore:
    def __init__(self, persist_dir: Path):
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.col = self.client.get_or_create_collection("docbot")

    def add(self, chunks, vectors):
        self.col.add(ids=[c.id for c in chunks], embeddings=vectors,
                     documents=[c.text for c in chunks],
                     metadatas=[c.metadata for c in chunks])

    def query(self, vec, k=5, doc_id: str | None = None):
        where = {"doc_id": doc_id} if doc_id else None
        return self.col.query(query_embeddings=[vec], n_results=k, where=where)
```

### Pattern 4: Externalized prompts loaded at runtime

**What:** Prompts live in `prompts/*.txt` with `{placeholders}`. A tiny loader formats them at call time.

**When to use:** Always. Especially valuable here because the graph-extraction prompt is the heart of the demo.

**Trade-offs:**
- ✅ Edit prompts without restarting (Streamlit auto-reloads).
- ✅ Easy A/B during demo.
- ❌ No type-checking of placeholders — add a smoke test.

### Pattern 5: Model router as a pure function with explainable output

**What:** `route(task, signals) -> RouteDecision(model, reason)`. Returns *both* the chosen model and a human-readable rationale string the UI displays.

**When to use:** Whenever the demo needs to *show* a routing decision (this POC's explicit goal).

**Trade-offs:**
- ✅ The "reason" string is the demo's hero — makes the routing concept tangible.
- ✅ Testable without LLM calls.
- ❌ Rule-based; not a real cost/latency optimizer (explicitly out of scope).

**Example:**
```python
# routers/model_router.py
@dataclass
class RouteDecision:
    model: str
    reason: str

def route(task: str, *, doc_chars: int = 0, manual_override: str | None = None) -> RouteDecision:
    if manual_override:
        return RouteDecision(manual_override, f"manual override → {manual_override}")
    if task == "summarize" and doc_chars > 50_000:
        return RouteDecision(LARGE_MODEL, "long doc summarization → large model")
    if task in {"qa", "graph"}:
        return RouteDecision(LARGE_MODEL, f"{task} benefits from larger context model")
    return RouteDecision(SMALL_MODEL, "default → small/fast model")
```

## Data Flow

### Ingestion Flow (upload → indexed)

```
[User drops PDF/image in Streamlit]
        │
        ▼
[ui/upload.py]  ── save bytes → data/uploads/{sha256}.pdf
        │
        ▼
[pipelines/ingest.py]
        │
        ├─► [core/extractor.py]  pypdf → list[Page]
        │           │
        │           ▼
        │     needs_ocr(page)? ─── no ──► keep text
        │           │ yes
        │           ▼
        │     [core/ocr.py]  pdf2image + EasyOCR → page.text
        │
        ├─► [core/chunker.py]  RecursiveCharacterTextSplitter (e.g., 800 chars / 100 overlap)
        │
        ├─► [core/embedder.py]  embed_many(texts) → list[vector]
        │
        └─► [core/vectorstore.py]  Chroma .add(ids, embeddings, docs, metadata)
                                    persisted → data/chroma/
```

### Query Flow (question → answer)

```
[User types question in chat]
        │
        ▼
[ui/chat.py]  ── question + selected doc_id (optional) + routing toggle
        │
        ▼
[pipelines/query.py]
        │
        ├─► [routers/model_router.py]  route("qa", signals) → (model, reason)
        │
        ├─► [core/embedder.py]  embed(question) → qvec
        │
        ├─► [core/retriever.py]  vectorstore.query(qvec, k=5, doc_id=?) → chunks
        │
        ├─► [prompts/qa.txt]  format(question, context=chunks)
        │
        ├─► [core/llm_client.py]  POST NVIDIA NIM /chat/completions (model)
        │
        └─► return Answer(text, citations=[chunk.metadata], route_reason=reason)
                │
                ▼
        [ui/chat.py]  render answer + expandable citations + "routed via X because Y"
```

### Summary & Graph Flows

```
Summary:  doc_id → retriever.all_chunks_for(doc_id) → chunker.batch
                 → for each batch: LLM(prompts/summary.txt)  (map step)
                 → LLM(prompts/summary.txt, combined_summaries) (reduce step)
                 → markdown summary

Graph:    doc_id → retriever.all_chunks_for(doc_id) (or top-N representative)
                 → LLM(prompts/graph.txt, response_format=json_object)
                 → validate schema {entities:[], relationships:[], rules:[]}
                 → render: JSON view + simple node-edge view (e.g., streamlit-agraph or networkx + pyvis)
```

### Session State (Streamlit)

```
st.session_state
├── current_doc_id        # last uploaded/selected
├── ingested_docs         # [{doc_id, filename, n_chunks}]
├── chat_history          # [{role, text, citations, route_reason}]
├── routing_mode          # "auto" | "small" | "large"
└── last_summary / last_graph (cached per doc_id)
```

### Key Data Flows Summary

1. **Upload → Persist:** raw bytes → content-hashed file in `data/uploads/` → cached extraction in `data/cache/{hash}.json` → vectors in `data/chroma/`.
2. **Question → Answer:** UI → router → retriever → LLM → cited answer back to UI.
3. **Doc → Summary/Graph:** UI → pipeline → retriever (full doc) → LLM (templated prompt) → structured render.
4. **Routing decision:** every LLM-bound call goes through `model_router.route()` so the UI can always show "which model + why."

## Persistence

| Path | Contents | Lifecycle |
|------|----------|-----------|
| `data/uploads/{sha256}.{ext}` | Raw uploaded files, named by content hash | Persist across runs; deduped by hash |
| `data/cache/{sha256}.json` | Extracted text + OCR results keyed by content hash | Persist; skip extract/OCR on repeat upload |
| `data/chroma/` | ChromaDB `PersistentClient` directory (sqlite + parquet) | Persist; survives Streamlit restarts |
| `data/samples/` | Bundled demo PDFs (committed) | Read-only |
| `.env.local` | `NVIDIA_API_KEY`, model names, paths | Never committed |

**Cleanup:** `make clean` removes `data/uploads`, `data/cache`, `data/chroma` (preserves `data/samples`). UI also exposes a sidebar "Reset workspace" button calling the same logic.

**Path discipline:** All paths come from `core/config.Settings` — no hard-coded `data/...` strings inside pipelines. Lets a developer point at a different location via env var.

## Suggested Build Order

Build bottom-up; each step ends with something runnable.

| # | Phase | Components | Verifiable Outcome |
|---|-------|------------|--------------------|
| 1 | **Skeleton & config** | `pyproject.toml`, `Makefile`, `core/config.py`, `app.py` (hello world), `.env.local.example` | `make setup && make run` opens a Streamlit page |
| 2 | **LLM client** | `core/llm_client.py` (port `test-nvidia.mjs` to Python), smoke test | `python -m core.llm_client` echoes `{"status":"ok"}` |
| 3 | **Extractor + OCR** | `core/extractor.py`, `core/ocr.py`, sample PDFs in `data/samples/` | Unit tests extract text from one native + one scanned PDF |
| 4 | **Chunker + embedder** | `core/chunker.py`, `core/embedder.py` | Test produces N chunks with metadata + vectors of expected dim |
| 5 | **Vector store wrapper** | `core/vectorstore.py` (Chroma persistent) | Add → query round-trip test passes |
| 6 | **Ingestion pipeline + Upload UI** | `pipelines/ingest.py`, `ui/upload.py` | Upload PDF in browser → see "ingested N chunks" |
| 7 | **Retriever + Q&A pipeline + Chat UI** | `core/retriever.py`, `pipelines/query.py`, `prompts/qa.txt`, `ui/chat.py` | End-to-end demo flow: upload → ask → cited answer |
| 8 | **Summarizer** | `pipelines/summarize.py`, `prompts/summary.txt`, `ui/summary_view.py` | Click "Summarize" → readable summary |
| 9 | **Graph extractor** | `pipelines/graph.py`, `prompts/graph.txt`, `ui/graph_view.py` | Click "Extract graph" → JSON + node-edge view |
| 10 | **Model router + routing toggle** | `routers/model_router.py`, sidebar toggle, route-reason badge in chat | Toggle changes model; reason shown in UI |
| 11 | **Polish** | Sample-doc menu, "reset workspace", error toasts, README quickstart, `make clean` | Demo is one-take fluid |

**Dependencies between phases:**
- Phase 6 depends on **2–5** (needs LLM client only for sanity, plus extract/chunk/embed/store).
- Phase 7 depends on **6** (needs ingested data) and **2** (LLM).
- Phases 8 and 9 depend on **6** (need ingested chunks) and **2**.
- Phase 10 depends on **7–9** (router needs at least one task type to route).
- Steps 8/9 can be built in **parallel** once 7 lands.

**Why this order:** Validates the riskiest integrations first (NVIDIA API at step 2; OCR at step 3; vector persistence at step 5) and produces a usable demo at step 7 — every step beyond that adds value but is cuttable if time runs short.

## Packaging Implications — ≤ 3-command setup

**The 3-command target:**

```bash
git clone <repo> && cd docbot              # 1. clone
cp .env.local.example .env.local           # 2. add NVIDIA_API_KEY
make run                                   # 3. setup (idempotent) + launch
```

Where `Makefile`:

```makefile
.PHONY: setup run clean
setup:
	uv sync                                # or: pip install -e .

run: setup
	uv run streamlit run app.py            # setup is idempotent, so this is one command

clean:
	rm -rf data/uploads data/cache data/chroma
```

**What this forces architecturally:**

| Constraint | Architectural Consequence |
|------------|---------------------------|
| No system binaries | EasyOCR (pure Python) over Tesseract; pypdf over poppler-only paths; if `pdf2image` is needed, document it as an optional install or use `pypdfium2` |
| No DB server | Chroma `PersistentClient` (embedded sqlite) — *not* `HttpClient` |
| No build step | Streamlit (no webpack); plain `.txt` prompts; no codegen |
| One language | All Python; the `.mjs` script stays as a reference only |
| One dependency manifest | `pyproject.toml` (preferred via `uv`) — no separate `requirements.txt` drift |
| Lazy heavy imports | EasyOCR reader and embedding model loaded on first use, not at app start, so `make run` is fast and cold-start failures localize to the responsible feature |
| Model downloads cached on first run | EasyOCR + sentence-transformers cache to `~/.cache/...` automatically; document this in README so first run is "slow once, fast forever" |
| Env via `.env.local` | `core/config.Settings` reads via `pydantic-settings` or `python-dotenv`; never committed; matches the existing JS reference script |

**Anti-pattern to avoid:** Splitting into `backend/` (FastAPI) + `frontend/` (Streamlit) services. Doubles the setup surface, breaks the "one command" promise, and adds zero value at POC scope.

## Anti-Patterns

### Anti-Pattern 1: One-mega `app.py`

**What people do:** Cram extraction, chunking, embedding, LLM calls, *and* UI rendering into `app.py` because Streamlit examples show it.
**Why it's wrong:** Untestable; impossible to swap components; reruns on every widget change re-execute heavy code.
**Do this instead:** Keep `app.py` as a composition root only; push logic into `core/` and `pipelines/`. Use `@st.cache_resource` for heavy singletons (Chroma client, embedder, EasyOCR reader).

### Anti-Pattern 2: Re-instantiating Chroma / embedding model on every interaction

**What people do:** `chromadb.PersistentClient(...)` inside a request handler.
**Why it's wrong:** Streamlit re-runs the script on every widget interaction; this re-opens the DB, re-loads models, and tanks UX.
**Do this instead:** Wrap singletons with `@st.cache_resource` (or a module-level lazy init in `core/`).

### Anti-Pattern 3: Embedding prompts inside Python f-strings deep in pipeline code

**What people do:** `prompt = f"You are an expert... {context} ... {question}"` scattered across modules.
**Why it's wrong:** Iterating on prompts requires code edits + restarts; impossible to diff prompt-only changes.
**Do this instead:** `prompts/*.txt` loaded by a `load_prompt(name, **vars)` helper.

### Anti-Pattern 4: No `doc_id` metadata on chunks

**What people do:** Dump all chunks into one collection with no per-doc tag.
**Why it's wrong:** Can't scope queries to a doc, can't delete a doc, can't show citations meaningfully.
**Do this instead:** Always attach `{doc_id, page, source, chunk_index}` to every chunk.

### Anti-Pattern 5: OCR on every PDF unconditionally

**What people do:** Run EasyOCR on all uploads "to be safe."
**Why it's wrong:** 10–100× slower than native text extraction; ruins demo pacing.
**Do this instead:** Branching extractor (Pattern 2) — OCR only when text extraction yields nothing.

### Anti-Pattern 6: Hiding the routing decision

**What people do:** Pick a model silently and just return the answer.
**Why it's wrong:** The whole point of this POC's routing demo is to *show* the decision. An invisible router is indistinguishable from no router.
**Do this instead:** Router returns `(model, reason)`; UI surfaces both.

### Anti-Pattern 7: Trusting LLM JSON without validation

**What people do:** `json.loads(response)` and pass the result straight to the graph view.
**Why it's wrong:** Models occasionally return prose, partial JSON, or wrong-shaped objects — graph view crashes mid-demo.
**Do this instead:** Use `response_format={"type":"json_object"}` *and* validate with a Pydantic model; on failure, retry once with an explicit "valid JSON only" reminder, then surface a friendly error.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| NVIDIA NIM (`/v1/chat/completions`) | HTTP via `httpx`, Bearer auth, JSON body, optional `response_format: json_object` | 30s timeout (matches `test-nvidia.mjs`); handle 401 (key), 429 (rate), 504 (overloaded — retry with backoff or fall back to alternate model) |
| NVIDIA NIM embeddings (optional) | Same client, `/v1/embeddings` endpoint | If used, falls under same router/retry logic. Otherwise local `sentence-transformers/all-MiniLM-L6-v2` is the simpler default |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `ui/` ↔ `pipelines/` | Direct function calls returning dataclasses | Pipelines never import `streamlit`; UI never imports `core/` directly (goes via pipelines) |
| `pipelines/` ↔ `core/` | Direct function calls | Core is the only layer that talks to external systems (Chroma, NVIDIA, filesystem, EasyOCR) |
| `pipelines/query` ↔ `routers/model_router` | Pipeline calls `route()` before every LLM call | Router is pure; deterministic in tests |
| `core/llm_client` ↔ `core/config` | Config injected, not imported globally | Lets tests stub the client |

## Sources

- ChromaDB persistence model — https://docs.trychroma.com/usage-guide (PersistentClient, metadata filters)
- Streamlit caching patterns — https://docs.streamlit.io/library/advanced-features/caching (`@st.cache_resource` for singletons)
- LangChain RAG reference architecture — https://python.langchain.com/docs/tutorials/rag/ (component decomposition: loader → splitter → embedder → vectorstore → retriever → chain)
- LlamaIndex reference structure — https://docs.llamaindex.ai/en/stable/getting_started/concepts/ (ingestion vs query separation)
- EasyOCR Python API — https://github.com/JaidedAI/EasyOCR (pure-Python install)
- NVIDIA NIM OpenAI-compatible API — https://docs.api.nvidia.com (validated locally via `test-nvidia.mjs`)
- `uv` packaging for single-`pyproject.toml` workflows — https://docs.astral.sh/uv/

---
*Architecture research for: Local RAG + document-intelligence POC*
*Researched: 2026-04-28*

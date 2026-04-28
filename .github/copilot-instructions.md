<!-- GSD Configuration — managed by get-shit-done installer -->
# Instructions for GSD

- Use the get-shit-done skill when the user asks for GSD or uses a `gsd-*` command.
- Treat `/gsd-...` or `gsd-...` as command invocations and load the matching file from `.github/skills/gsd-*`.
- When a command says to spawn a subagent, prefer a matching custom agent from `.github/agents`.
- Do not apply GSD workflows unless the user explicitly asks for them.
- After completing any `gsd-*` command (or any deliverable it triggers: feature, bug fix, tests, docs, etc.), ALWAYS: (1) offer the user the next step by prompting via `ask_user`; repeat this feedback loop until the user explicitly indicates they are done.
<!-- /GSD Configuration -->

# Project: DocBot — Local Intelligent Document Query POC

**Core value:** A user can drop a document into a local web app, ask questions in natural language, get summaries, and see entities/relationships extracted — with one-command setup.

## Stack (locked)

- **Language:** Python 3.10–3.12 (CPU-only)
- **Packaging:** `uv` + `tasks.ps1` (≤ 3 commands from clone to running demo)
- **UI:** Streamlit
- **RAG orchestration:** LlamaIndex (`llama-index-core ^0.12`)
- **PDF extraction:** PyMuPDF (`^1.24`)
- **OCR:** EasyOCR (`^1.7.2`), English-only, CPU, weights pre-downloaded in `.\tasks.ps1 setup`
- **Vector store:** ChromaDB (`^0.5`) `PersistentClient`, telemetry off, single collection with `doc_id` metadata
- **LLM client:** `openai ^1.50` SDK against NVIDIA NIM (`https://integrate.api.nvidia.com/v1`)
- **Default models:** `meta/llama-3.1-70b-instruct` (chat), `nvidia/nv-embedqa-e5-v5` (embeddings); routing target via `NVIDIA_ROUTE_MODEL`
- **Validation:** Pydantic `^2.7`
- **Env:** `.env.local` (mirrors `test-nvidia.mjs` pattern)

## Layout

```
app.py                    # Streamlit composition root (thin)
core/                     # capabilities (config, llm_client, extractor, ocr, chunker, embedder, vectorstore, retriever)
pipelines/                # orchestration (ingest, query, summarize, graph)
routers/model_router.py   # pure-function router with explainable RouteDecision
prompts/                  # externalized prompt templates
ui/                       # Streamlit view partials (upload, chat, summary_view, graph_view, sidebar)
data/samples/             # bundled sample PDFs (committed)
data/uploads/, data/cache/, data/chroma/   # runtime state (gitignored)
```

## Hard rules (from PITFALLS research)

- **Wrap heavy resources in `@st.cache_resource`** (LLM client, EasyOCR Reader, Chroma client) — Streamlit reruns the script on every interaction.
- **Single `EMBEDDING_MODEL` constant** imported by ingest and query paths; ChromaDB collection metadata stores `embedding_model` + `embedding_dim` and asserts on startup.
- **Batch embeddings** (32–64 chunks/call) with exponential backoff + jitter on 429/504; 60s timeout.
- **Env-configurable fallback model** for resilience during demos.
- **Structure-aware chunker** never splits across tables/lists/headings; tables emitted as atomic chunks with `chunk_type` metadata.
- **Per-page `<50 chars` heuristic** triggers OCR fallback for scanned/image pages.
- **Grounded prompt + post-hoc citation validation** — flag hallucinated `[chunk_id]` references in the UI.
- **Reorder retrieved chunks so highest-scored chunk appears first AND last** (anti "lost in the middle"); top-k = 3–5.
- **Graph extraction:** `response_format={"type":"json_object"}` + Pydantic schema + one-shot self-correction on parse failure; entity dedup via `rapidfuzz`.
- **Routing comparison panel:** disable caching; identical system prompt / user prompt / retrieved chunks / temperature — only the model differs; parallel calls via `asyncio.gather`; "concept demo, not benchmark" disclaimer.

## Workflow

- Mode: YOLO (auto-approve, just execute)
- Granularity: standard (7 phases)
- Research: enabled (run before each phase as needed)
- Plan check + verifier: enabled
- Sub-agents (`gsd-*`) referenced in `.github/agents/` are the canonical executors

See `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, and `.planning/research/SUMMARY.md` for full context. Next: `/gsd-plan-phase 1`.

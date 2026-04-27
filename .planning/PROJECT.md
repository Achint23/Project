# DocBot — Local Intelligent Document Query POC

## What This Is

DocBot is a **locally deployable Proof-of-Concept** that ingests business documents (PDFs, scanned PDFs, image-based docs), extracts content, and lets users **query, summarize, and explore graph-style semantic structure** through a simple web interface. Built for developer/demo machines — not enterprise scale — to validate feasibility of document understanding, semantic retrieval, and model-routing concepts.

## Core Value

**A user can drop a document into a local web app, ask questions in natural language, get summaries, and see entities/relationships extracted — with one-command setup.**

If everything else is cut, this end-to-end demo flow must work.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Local-only deployment runnable on a developer laptop with minimal install steps
- [ ] One-command project setup + run (e.g., `make setup && make run` or `uv sync && streamlit run`)
- [ ] Ingestion of PDF, scanned PDF, and image-based business documents
- [ ] Text extraction including paragraphs, table-like content, and basic structure
- [ ] OCR for scanned/image documents (EasyOCR)
- [ ] Document indexing into a local embedded vector store (ChromaDB)
- [ ] Semantic / contextual retrieval against indexed documents
- [ ] Natural-language Q&A over document content
- [ ] Document summarization producing business-readable output
- [ ] Prompt-based graph-style semantic extraction (entities, relationships, process steps, decision points, business rules) emitted as structured JSON + readable view
- [ ] Model routing concept demo — direct path vs routed path between two NVIDIA-hosted models
- [ ] Streamlit/Gradio web UI exposing: upload → process → query → summary → graph view → routing toggle
- [ ] NVIDIA NIM API integration using free-tier API key from `.env.local`
- [ ] Demo-ready end-to-end workflow against a small bundled sample document set

### Out of Scope

- Production-grade scaling / bulk enterprise ingestion — POC only, small sample set
- True graph database backend (Neo4j, etc.) — prompt-based simulation is sufficient
- Cloud-hosted deployment, multi-tenancy, user auth — local single-user demo
- Production-grade model routing engine with cost/latency optimization — concept demo only
- Fine-tuning or training custom models — use NVIDIA-hosted models as-is
- Mobile apps, desktop installers
- Real-time collaboration / multi-user document sharing
- Fully offline LLM inference (local Ollama) — deferred; NVIDIA API used for POC simplicity

## Context

- Local execution on a developer/demo machine is the primary delivery target.
- A reference test script `test-nvidia.mjs` already validates NVIDIA NIM connectivity using `NVIDIA_API_KEY`, base URL `https://integrate.api.nvidia.com/v1`, and default model `meta/llama-3.1-70b-instruct`. The Python POC will follow the same auth pattern but is **not required** to use JS.
- "Local deployment" in this POC means the **application** runs locally; the LLM itself is invoked via NVIDIA's hosted free-tier API. This trade-off was made to keep setup minimal.
- Sample documents are limited (handful of PDFs + a scanned/image doc) — quality only needs to support a meaningful demo.
- User is a developer/demo presenter who values minimal-install, one-command setup over architectural purity.

## Constraints

- **Tech stack**: Python (3.10+) — chosen for OCR/RAG/embeddings ecosystem and one-command Streamlit UI.
- **Frontend**: Streamlit (or Gradio) — single-file, zero-config web UI.
- **LLM provider**: NVIDIA NIM hosted API (free tier) — `NVIDIA_API_KEY` from `.env.local`.
- **Vector store**: ChromaDB embedded — zero-server, persists to disk, pip-install only.
- **OCR**: EasyOCR — pure-Python install, no external system binaries required.
- **Setup**: Must be ≤ 3 commands from clone to running demo. Prefer `uv` or `pip` + a `Makefile` / task runner.
- **Cost**: Stay within NVIDIA free-tier API limits.
- **Demo readiness**: Solution must support load → process → query → summarize → graph → compare-routing in a single browser session.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over Node.js for the POC | Best ecosystem for OCR, RAG, embeddings, and one-command Streamlit UI; matches "minimal install" priority | — Pending |
| Streamlit web UI | Single-file, no build step, fastest path to demo-ready UX | — Pending |
| NVIDIA NIM hosted API only (no local LLM) | Keeps setup minimal; routing demo done between two NVIDIA-hosted models | — Pending |
| ChromaDB embedded vector store | Zero-server, persists to disk, pip-only — fits "minimal setup" goal | — Pending |
| EasyOCR for scanned/image docs | Pure-Python, no Tesseract binary install | — Pending |
| LangChain or LlamaIndex as the orchestration layer | Standard RAG abstractions; pick the lighter of the two during research | — Pending |
| Prompt-based graph extraction (no graph DB) | Scope explicitly says graph backend is not required; output as JSON + readable view | — Pending |
| Model routing = router between two NVIDIA models (e.g., Llama-70B vs a smaller/alternate model) | Demonstrates routing concept without local-model setup overhead | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-28 after initialization*

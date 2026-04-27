# Stack Research

**Domain:** Local-deployable RAG + multimodal-document-understanding POC (Python, NVIDIA NIM)
**Researched:** 2026-04-28
**Confidence:** HIGH on framework selection and patterns; MEDIUM on exact patch versions (verify with `pip index versions <pkg>` at install time — the recommendations below pin to safe minor-version floors, not exact patches).

## TL;DR

For a **POC** with the locked constraints (Python 3.10+, NVIDIA NIM, ChromaDB, EasyOCR, ≤3 setup commands), the prescriptive stack is:

> **LlamaIndex** (orchestration) + **PyMuPDF** (PDF text) + **EasyOCR** + **pdf2image** (raster) + **NVIDIA NIM `nv-embedqa-e5-v5`** (embeddings) + **Chroma 0.5+** (vector store, `PersistentClient`) + **`openai` SDK** (LLM client, NIM is OpenAI-compatible) + **Streamlit** (UI) + **uv** + **Makefile** (setup) + **python-dotenv** (config).

Setup collapses to: `uv sync && cp .env.local.example .env.local && make run` — three commands.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | `>=3.10,<3.13` | Runtime | 3.10+ is the project floor; pin `<3.13` because PyTorch wheels (EasyOCR dep) and some Chroma deps lag on the latest 3.13 builds. 3.11 is the sweet spot. |
| LlamaIndex | `llama-index-core ^0.12` | RAG orchestration | Lighter and more "RAG-native" than LangChain. Document → Node → Index → QueryEngine maps 1:1 to this POC's flow. Tree/list summary indices are first-class (LangChain treats summarization as an afterthought). Smaller import surface. |
| Streamlit | `^1.40` | Web UI | Single-file, native file uploader, `st.chat_message`/`st.chat_input` are stable, hot-reload, and `st.cache_resource` caches the Chroma client and embedding model trivially. Gradio's chat UX is fine but its state model is awkward for multi-step flows (upload → index → query → summarize → graph → routing toggle). |
| ChromaDB | `chromadb ^0.5` (or 0.6 if released) | Vector store | Locked. Use `chromadb.PersistentClient(path="./.chroma")` — pure embedded, no server, persists to disk, re-opens cleanly across runs. |
| EasyOCR | `easyocr ^1.7.2` | OCR | Locked. Pure-Python (no Tesseract binary). Pulls torch + torchvision; warm the `Reader(['en'], gpu=False)` once per session via `st.cache_resource`. |
| NVIDIA NIM (hosted) | API: `https://integrate.api.nvidia.com/v1` | LLM + embeddings | Locked. OpenAI-compatible — use the stock `openai` client. Default chat model `meta/llama-3.1-70b-instruct` (matches `test-nvidia.mjs`); routing demo against e.g. `meta/llama-3.1-8b-instruct` or `mistralai/mixtral-8x7b-instruct-v0.1`. Default embedding model `nvidia/nv-embedqa-e5-v5` (1024-dim, retrieval-tuned). |
| openai (SDK) | `openai ^1.50` | LLM + embedding client | NVIDIA NIM is fully OpenAI-compatible (`/v1/chat/completions`, `/v1/embeddings`). One client serves chat **and** embeddings — no need for a NIM-specific package. Mirrors the `test-nvidia.mjs` Bearer-token + base-URL pattern exactly. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyMuPDF (`pymupdf`) | `^1.24` | Native PDF text + layout extraction | Primary text extractor. Fastest of the four candidates; preserves block/line structure (needed for "table-like content" requirement); exposes `page.get_text("blocks")` and `page.get_images()`. AGPL — fine for a POC; if commercial licensing ever matters, swap to `pdfplumber`. |
| pdf2image | `^1.17` | Rasterize PDF pages → PIL Images for OCR | When PyMuPDF reports a page has no extractable text (scanned PDF) or low text-coverage ratio, render at 200–300 DPI and feed to EasyOCR. Requires the `poppler` system binary on Windows — bundle install instructions in README, but this stays within the 3-command rule because it's a one-time prereq, not a setup step. |
| Pillow (`PIL`) | `^11.0` | Image I/O for standalone image docs | Direct upload path: PNG/JPG/TIFF → `Image.open()` → `numpy` array → EasyOCR. Already a transitive dep of pdf2image and easyocr; pin explicitly to surface upgrades. |
| llama-index-vector-stores-chroma | `^0.4` | LlamaIndex ↔ Chroma adapter | Wires `PersistentClient` collection into a LlamaIndex `VectorStoreIndex`. Avoids hand-writing `collection.add()` / `collection.query()` glue. |
| llama-index-llms-openai-like | `^0.3` | LlamaIndex LLM wrapper for NIM | `OpenAILike(model="meta/llama-3.1-70b-instruct", api_base=..., api_key=..., is_chat_model=True)` — points LlamaIndex at NIM via the OpenAI-compat shim. Avoid `llama-index-llms-nvidia` (heavier, pulls `langchain-nvidia-ai-endpoints` indirectly in some versions). |
| llama-index-embeddings-openai-like | `^0.1` | LlamaIndex embedding wrapper for NIM | Same trick for `nvidia/nv-embedqa-e5-v5` via the OpenAI-compat embeddings endpoint. Single SDK, single auth path. |
| python-dotenv | `^1.0` | Load `.env.local` | Match the `test-nvidia.mjs` pattern: `load_dotenv(".env.local", override=False)` at app entry. Read `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_MODEL`, `NVIDIA_EMBED_MODEL`. |
| pydantic | `^2.7` | Structured graph-extraction output | Define `Entity`, `Relationship`, `ProcessStep` models; pass `response_format={"type": "json_object"}` to NIM (already proven in `test-nvidia.mjs`); validate the parsed JSON against the Pydantic schema before rendering. |
| numpy | `^1.26` (or `^2.0` if torch wheel allows) | EasyOCR image arrays | Transitive; pin to whatever the installed torch + easyocr accept. |
| tiktoken | `^0.7` | Token counting for chunk sizing | Optional but cheap insurance — keeps RAG chunks under NIM's context window. LlamaIndex uses it under the hood for the OpenAI tokenizer; close enough for Llama-3 budgeting. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **uv** (`>=0.5`) | Package + venv manager | 10–100× faster than `pip`. Single `pyproject.toml`, lockfile (`uv.lock`) for reproducibility, `uv sync` creates the venv and installs everything in one command. Astral is maintaining it actively; this is the 2025/2026 default for greenfield Python. |
| **Makefile** | Task runner | Use `make` over `just`/`taskipy` — `make` is preinstalled on macOS/Linux, available via `choco install make` or WSL on Windows, zero Python dep. Targets: `setup`, `run`, `test`, `clean`. |
| **ruff** | Lint + format | Replaces flake8 + black + isort; `uv add --dev ruff`. Optional for a POC but the cost is ~2 lines in `pyproject.toml`. |
| **pytest** | Tests | One smoke test per ingestion path (PDF / scanned / image) is enough for a POC. |

## Installation

Recommended `pyproject.toml` dependency block (Python equivalent of npm install):

```toml
# pyproject.toml
[project]
name = "docbot"
version = "0.1.0"
requires-python = ">=3.10,<3.13"
dependencies = [
  "streamlit>=1.40",
  "llama-index-core>=0.12",
  "llama-index-vector-stores-chroma>=0.4",
  "llama-index-llms-openai-like>=0.3",
  "llama-index-embeddings-openai-like>=0.1",
  "chromadb>=0.5",
  "openai>=1.50",
  "pymupdf>=1.24",
  "pdf2image>=1.17",
  "pillow>=11.0",
  "easyocr>=1.7.2",
  "python-dotenv>=1.0",
  "pydantic>=2.7",
  "tiktoken>=0.7",
]

[dependency-groups]
dev = ["ruff>=0.6", "pytest>=8.0"]
```

```bash
# 3-command setup (matches PROJECT.md constraint)
uv sync                                # creates .venv, installs everything
cp .env.local.example .env.local       # user pastes NVIDIA_API_KEY
make run                               # → streamlit run src/docbot/app.py
```

System prerequisite (one-time, documented in README — does **not** count against the 3-command rule):
- **Poppler** (for `pdf2image`): Windows → `choco install poppler` or download binaries; macOS → `brew install poppler`; Linux → `apt install poppler-utils`.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **LlamaIndex** | LangChain (`langchain ^0.3` + `langchain-nvidia-ai-endpoints ^0.3`) | If you later need agents, tool-calling chains, or multi-step pipelines beyond RAG. LangChain wins on agent ecosystem; LlamaIndex wins on RAG ergonomics — this POC is RAG. |
| **LlamaIndex** | Haystack 2.x (`haystack-ai ^2.5`) | If you need a production-style pipeline DSL with strongly-typed components. Overkill for a 1-week POC; steeper ramp than LlamaIndex. |
| **PyMuPDF** | `pdfplumber ^0.11` | If AGPL is a non-starter (PyMuPDF is AGPL/commercial dual-licensed). pdfplumber is MIT and slightly better at table extraction, but ~3× slower and weaker on complex layouts. |
| **PyMuPDF** | `pypdf ^5.0` | If you want pure-Python with no native deps. Acceptable for clean digital PDFs only — falls apart on multi-column or table layouts. |
| **PyMuPDF** | `unstructured ^0.15` | If you need built-in element classification (Title, NarrativeText, Table) and don't mind a heavy install (drags in detectron2/onnx for the high-res strategy). Too much weight for a POC. |
| **NVIDIA NIM embeddings** (`nv-embedqa-e5-v5`) | `sentence-transformers ^3.0` (e.g. `BAAI/bge-small-en-v1.5`) | If you want fully-offline embeddings, no API quota use, or sub-50ms per chunk. Tradeoff: ~120MB model download on first run + torch already in the tree from EasyOCR, so disk cost is small. Recommend NIM here only because it keeps the auth + provider story uniform with chat. |
| **`openai` SDK** | `langchain-nvidia-ai-endpoints` | Only if you commit to LangChain. It adds NIM-specific helpers (function calling, model listing) but you give up the "one client for chat + embeddings" simplicity. |
| **Streamlit** | Gradio `^4.40` | If the demo is primarily a chat-with-doc UX with minimal multi-step state. Gradio's `gr.ChatInterface` is one line. Streamlit wins here because of the upload→index→summarize→graph→routing-toggle multi-panel layout. |
| **uv** | `pip` + `python -m venv` + `requirements.txt` | If the demo machine forbids new tooling. Costs 5× setup time and you lose the lockfile. |
| **Makefile** | `just`, `taskipy`, `poethepoet` | If `make` is unavailable (rare). `just` is the modern alternative; `taskipy`/`poe` keep tasks inside `pyproject.toml`. All add an extra install step. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `PyPDF2` | Deprecated since 2022; renamed to `pypdf`. Many tutorials still reference it. | `pypdf` — or better, `pymupdf` for this project. |
| `pytesseract` / Tesseract OCR | Requires a system binary install (breaks the "minimal install" constraint). EasyOCR is pure-pip. | `easyocr` (locked). |
| `faiss-cpu` / `faiss-gpu` | Heavier install, no built-in persistence model, and Chroma is locked anyway. | `chromadb` (locked). |
| `langchain` (as the orchestration layer) | Heavier import surface; abstraction churn between 0.1 → 0.2 → 0.3 has burned many POCs; agent-centric mental model fights a pure-RAG flow. | `llama-index-core`. |
| `llama-cpp-python` / Ollama | Out of scope per PROJECT.md ("Fully offline LLM inference deferred"). Adds gigabytes of model weights and CUDA/Metal setup. | NVIDIA NIM hosted API. |
| `flask` / `fastapi` (as the UI) | Requires writing HTML + a separate frontend or a Jinja stack. Kills the one-command-demo goal. | `streamlit`. |
| `weaviate-client`, `qdrant-client`, `pinecone-client` | All require a running server (or a managed account). Violates "embedded, zero-server". | `chromadb` PersistentClient. |
| Hand-rolled `requests`/`httpx` calls to NIM | Re-implements retries, streaming, token accounting, and error mapping that `openai` already handles. | `openai` SDK with `base_url=NVIDIA_BASE_URL`. |
| `conda` / `miniconda` | Heavyweight, slow, and unnecessary now that PyTorch and friends ship clean wheels on PyPI. Breaks the 3-command rule (env activation step). | `uv`. |
| `pdfminer.six` directly | Lower-level than `pdfplumber` (which wraps it) and slower than PyMuPDF. No reason to use it raw in 2026. | `pymupdf` or `pdfplumber`. |
| `chromadb` HTTP/server mode for the POC | Adds a second process, kills the embedded promise. | `chromadb.PersistentClient(path=...)`. |

## Stack Patterns by Variant

**If the demo machine has a CUDA GPU:**
- Set `easyocr.Reader(..., gpu=True)` — 5–10× faster OCR on scanned PDFs.
- Otherwise leave `gpu=False` and accept ~1–3s per scanned page.

**If the demo will run airgapped or NIM rate limits become a problem:**
- Swap NIM embeddings → `sentence-transformers/all-MiniLM-L6-v2` (384-dim, 90MB) or `BAAI/bge-small-en-v1.5` (384-dim, 130MB).
- Keep NIM for chat (the routing demo requires a real provider).

**If commercial licensing matters later:**
- Replace PyMuPDF (AGPL) → `pdfplumber` (MIT). Acceptable quality loss; ~3× slowdown on large PDFs is fine for a POC.

**If Streamlit's reruns become a UX problem (long indexing redoing on every interaction):**
- Wrap the index build in `@st.cache_resource(show_spinner="Indexing...")` keyed on a content hash of uploaded files.
- This is the single most common Streamlit-RAG pitfall.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `easyocr 1.7.2` | `torch >=2.0,<2.5` (typical resolution) | Let pip resolve torch; do not pin torch yourself unless you hit conflicts. |
| `chromadb >=0.5` | `pydantic >=2.x` | Chroma 0.4.x was Pydantic-1 — avoid. |
| `llama-index-core 0.12.x` | `pydantic >=2.7`, `openai >=1.40` | Major rewrite landed in 0.10; 0.12 is current as of late 2025. |
| `pymupdf 1.24` | Python 3.10–3.12 wheels | 3.13 wheels lag — pin `python <3.13`. |
| `streamlit 1.40+` | `pydantic 2.x`, `pillow >=10` | `st.cache_resource` and `st.chat_message` both stable. |
| `pdf2image` | Poppler ≥ 22.x system binary | Will raise `PDFInfoNotInstalledError` at runtime if missing — fail fast in a startup health-check. |

## NVIDIA NIM Integration Pattern (matches `test-nvidia.mjs`)

```python
# src/docbot/llm.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(".env.local", override=False)

NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_API_KEY  = os.environ["NVIDIA_API_KEY"]  # fail fast if missing
CHAT_MODEL      = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
EMBED_MODEL     = os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")
ROUTE_MODEL     = os.getenv("NVIDIA_ROUTE_MODEL", "meta/llama-3.1-8b-instruct")

client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL, timeout=30.0)
```

Same auth pattern as the JS reference: Bearer token via `Authorization` header (the SDK handles it), 30s timeout, `response_format={"type":"json_object"}` for the graph-extraction call. One client object covers both `client.chat.completions.create(...)` and `client.embeddings.create(...)`.

## Sources

- **NVIDIA NIM API docs** — https://docs.api.nvidia.com/nim/reference/llm-apis (OpenAI-compat, base URL, model catalog including `nv-embedqa-e5-v5`). Confidence: **HIGH** (official).
- **`test-nvidia.mjs`** — verified base URL, default model, auth header pattern. Confidence: **HIGH** (in-repo).
- **LlamaIndex docs** — https://docs.llamaindex.ai/ — `OpenAILike` LLM/embedding wrappers, Chroma vector store integration, `VectorStoreIndex` query/summary patterns. Confidence: **HIGH** (official).
- **Chroma docs** — https://docs.trychroma.com/ — `PersistentClient`, embedded mode, collection lifecycle. Confidence: **HIGH** (official).
- **Streamlit docs** — https://docs.streamlit.io/ — `st.cache_resource`, `st.chat_message`, file uploader. Confidence: **HIGH** (official).
- **EasyOCR repo** — https://github.com/JaidedAI/EasyOCR — pure-Python install, GPU/CPU modes. Confidence: **HIGH** (official).
- **PyMuPDF docs** — https://pymupdf.readthedocs.io/ — text-extraction modes, license terms. Confidence: **HIGH** (official).
- **Astral `uv` docs** — https://docs.astral.sh/uv/ — `uv sync`, lockfile semantics, `pyproject.toml` integration. Confidence: **HIGH** (official).
- **OpenAI Python SDK** — https://github.com/openai/openai-python — `base_url` override pattern used for any OpenAI-compatible provider. Confidence: **HIGH** (official).
- Patch-version specifics (e.g. `streamlit 1.40` vs `1.42`, `chromadb 0.5` vs `0.6`, `llama-index-core 0.12.x`) — Confidence: **MEDIUM** — major-version floors are correct; run `uv lock --upgrade` at install time to land on the latest patch.

---
*Stack research for: Local-deployable RAG + multimodal-document-understanding POC*
*Researched: 2026-04-28*

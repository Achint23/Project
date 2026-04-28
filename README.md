# 📄 DocBot

![Python 3.10–3.12](https://img.shields.io/badge/python-3.10%E2%80%933.12-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)
![NVIDIA NIM](https://img.shields.io/badge/LLM-NVIDIA%20NIM-76B900)

**Local Intelligent Document Query POC** — drop a document, ask questions in natural language, get summaries, and see entities/relationships extracted.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Python 3.10–3.12** | [Download](https://www.python.org/downloads/) — must be `>=3.10,<3.13` |
| **uv** | Fast Python package manager — [Install](https://docs.astral.sh/uv/getting-started/installation/) |
| **Git** | [Download](https://git-scm.com/downloads) |
| **NVIDIA NIM API key** | Free tier — sign up at [build.nvidia.com](https://build.nvidia.com/) |

> **No GPU required** — the application runs on CPU-only machines. LLM inference is handled by NVIDIA's hosted API.

---

## Quick Start

### 1. Clone and install dependencies

```powershell
git clone <repo-url>
cd DocBot
.\tasks.ps1 setup        # Windows PowerShell
```

<details>
<summary>macOS / Linux</summary>

```bash
git clone <repo-url>
cd DocBot
uv sync
uv run python -c "import easyocr; easyocr.Reader(['en'], gpu=False)"
```
</details>

<details>
<summary>Windows cmd.exe</summary>

```cmd
git clone <repo-url>
cd DocBot
tasks.cmd setup
```
</details>

### 2. Configure environment

```powershell
Copy-Item .env.local.example .env.local
```

Open `.env.local` and replace the placeholder with your real NVIDIA API key:

```
NVIDIA_API_KEY=nvapi-your-real-key-here
```

The other variables have sensible defaults and can be left as-is:

| Variable | Default | Purpose |
|----------|---------|---------|
| `NVIDIA_API_KEY` | *(required)* | NVIDIA NIM API key |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | NIM endpoint |
| `NVIDIA_MODEL` | `meta/llama-3.1-70b-instruct` | Primary chat model |
| `NVIDIA_ROUTE_MODEL` | `meta/llama-3.1-8b-instruct` | Routed (smaller) model |
| `NVIDIA_EMBED_MODEL` | `nvidia/nv-embedqa-e5-v5` | Embedding model |

### 3. Run

```powershell
.\tasks.ps1 run           # Windows PowerShell
```

<details>
<summary>macOS / Linux</summary>

```bash
uv run streamlit run app.py
```
</details>

<details>
<summary>Windows cmd.exe</summary>

```cmd
tasks.cmd run
```
</details>

The app opens at **http://localhost:8501**.

---

## Demo Walkthrough

Follow these steps for a complete end-to-end demo:

### 1. Load a sample document

Click **Load samples** in the sidebar. Three bundled PDFs are loaded automatically (digital text, scanned/OCR, table-heavy). Processing status appears as each document is ingested.

### 2. Ask a question

Switch to the **💬 Chat** tab. Type a natural-language question about the loaded document (e.g., *"What are the key findings?"*). An answer appears with `[chunk_id]` citations — click to expand source previews.

### 3. Get a summary

Switch to the **📝 Summary** tab. Select a document and click **Summarize**. A business-readable summary is generated (direct or map-reduce depending on document length).

### 4. Extract a knowledge graph

Switch to the **🕸️ Graph** tab. Select a document and click **Extract**. An entity table and interactive node-edge graph are rendered (powered by streamlit-agraph). A Mermaid flowchart shows process steps.

### 5. Compare model routing

Switch to the **🔄 Compare** tab. Type the same question and click **Compare**. Side-by-side results appear from the large model and the routed smaller model, with latency and token metrics.

### 6. Try routing modes

Use the **routing toggle** in the sidebar (auto / small / large), then re-ask a question in the Chat tab. The model name and route reason are displayed under the answer.

---

## Available Commands

All commands are run via the PowerShell task runner (or `tasks.cmd` for cmd.exe):

| Command | Description |
|---------|-------------|
| `.\tasks.ps1 setup` | Install dependencies via `uv sync`, download EasyOCR weights |
| `.\tasks.ps1 run` | Launch Streamlit app on http://localhost:8501 |
| `.\tasks.ps1 test` | Run all pytest tests |
| `.\tasks.ps1 doctor` | Verify environment setup + NIM API connectivity |
| `.\tasks.ps1 clean` | Remove `.venv`, caches, uploaded/generated data |

---

## Troubleshooting

### Missing API key

**Symptom:** Error about `NVIDIA_API_KEY` not set or config check fails.

**Fix:** Copy the example env file and add your key:
```powershell
Copy-Item .env.local.example .env.local
# Edit .env.local — paste your key after NVIDIA_API_KEY=
```

Get a free key at [build.nvidia.com](https://build.nvidia.com/).

### EasyOCR weight download fails

**Symptom:** `setup` hangs or fails downloading model weights (~100 MB).

**Fix:** Check proxy/firewall settings. If behind a corporate proxy, set `HTTP_PROXY` / `HTTPS_PROXY` environment variables before running setup. Alternatively, manually download the weights from the [EasyOCR model hub](https://github.com/JaidedAI/EasyOCR/releases) and place them in `~/.EasyOCR/model/`.

### ChromaDB permission errors

**Symptom:** Permission denied writing to `data/chroma/`.

**Fix:** Run clean and retry:
```powershell
.\tasks.ps1 clean
.\tasks.ps1 setup
```

### Port 8501 in use

**Symptom:** Streamlit fails to start — address already in use.

**Fix:** Find and stop the process using port 8501:
```powershell
netstat -ano | findstr 8501
# Note the PID, then:
taskkill /PID <pid> /F
```

### Python version mismatch

**Symptom:** Installation fails with version constraint errors.

**Fix:** This project requires Python `>=3.10,<3.13`. Check your version:
```powershell
python --version
```
Install a compatible version from [python.org/downloads](https://www.python.org/downloads/).

### uv not found

**Symptom:** `uv` command not recognized.

**Fix:** Install uv following the [official guide](https://docs.astral.sh/uv/getting-started/installation/). On Windows:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Architecture

```
app.py                    # Streamlit composition root (thin)
core/                     # config, llm_client, extractor, ocr, chunker, embedder, vectorstore, retriever
pipelines/                # ingest, query, summarize, graph, compare
routers/model_router.py   # pure-function router → RouteDecision(model, reason)
prompts/                  # externalized prompt templates (qa, summary, graph)
ui/                       # Streamlit view partials (upload, chat, summary_view, graph_view, comparison, sidebar)
data/samples/             # bundled sample PDFs (committed)
data/uploads/             # user uploads (gitignored)
data/cache/               # processing cache (gitignored)
data/chroma/              # ChromaDB persistent storage (gitignored)
tests/                    # pytest test suite
```

**Data flow:**

```
User → Streamlit UI (app.py)
        ├── Upload → extractor → OCR (if scanned) → chunker → embedder → vectorstore
        ├── Chat   → retriever → reorder → QA prompt → LLM → cited answer
        ├── Summary → retriever → map/reduce prompt → LLM → summary
        ├── Graph  → retriever → graph_extract prompt → LLM → JSON → dedup → agraph
        └── Compare → parallel LLM calls (large + routed) → side-by-side
```

The thin `app.py` composes UI partials from `ui/`, which call `pipelines/` for orchestration. Pipelines use `core/` modules for capabilities. All LLM calls go through the `openai` SDK to NVIDIA NIM's OpenAI-compatible endpoint.

---

## Tech Stack

- **Python 3.10–3.12** — runtime
- **Streamlit** — web UI framework
- **NVIDIA NIM** — hosted LLM (chat + embeddings) via OpenAI-compatible API
- **ChromaDB** — embedded vector store with persistent storage
- **PyMuPDF** — PDF text and layout extraction
- **EasyOCR** — OCR for scanned/image pages (CPU, English)
- **Pydantic** — settings and data validation
- **tiktoken** — token counting for budget routing
- **rapidfuzz** — fuzzy entity deduplication in graph extraction
- **streamlit-agraph** — interactive graph visualization
- **uv** — fast Python package management

---

## License

POC / demo project — not for production use.

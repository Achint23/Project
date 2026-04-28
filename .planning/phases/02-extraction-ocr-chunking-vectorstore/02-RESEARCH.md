# Research: Phase 2 — Extraction, OCR, Chunking & Vector Store

**Phase:** 02-extraction-ocr-chunking-vectorstore
**Researched:** 2026-04-28
**Confidence:** HIGH (all libraries locked in PROJECT.md; patterns validated against official docs and PITFALLS.md)
**Mode:** ecosystem

## Standard Stack

| Library | Version | Role | Notes |
|---------|---------|------|-------|
| PyMuPDF (`pymupdf`) | `^1.24` | PDF text + layout extraction, table detection | AGPL; fastest Python PDF lib; `page.get_text("blocks")` for layout, `page.find_tables()` for tables |
| EasyOCR | `^1.7.2` | OCR for scanned/image pages | CPU-only, English; `Reader(['en'], gpu=False)`; ~2GB models on first use |
| ChromaDB | `^0.5` | Vector persistence | `PersistentClient`, telemetry off, `get_or_create_collection` |
| openai SDK | `^1.50` | Embedding via NVIDIA NIM | Already in Phase 1; `NIMClient.embed()` |
| tiktoken | `^0.7` | Token counting for chunk sizing | OpenAI tokenizer; close enough for Llama-3 budget |

## Architecture Patterns

### Pattern 1: Two-Path Extraction (text-first, OCR fallback)

Per-page decision: attempt PyMuPDF text extraction first. If a page yields `< 50 chars` of stripped text, route that page to EasyOCR.

```python
import pymupdf  # PyMuPDF

def extract_pages(pdf_path: str) -> list[dict]:
    """Extract text per page with OCR fallback detection."""
    doc = pymupdf.open(pdf_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")  # plain text extraction
        needs_ocr = len(text.strip()) < 50
        pages.append({
            "page_num": page_num,
            "text": text if not needs_ocr else "",
            "needs_ocr": needs_ocr,
        })
    doc.close()
    return pages
```

**Key insight:** The decision is per-PAGE, not per-document. A mixed PDF (some digital pages, some scanned) should route only the scanned pages through OCR.

### Pattern 2: Table Detection via PyMuPDF `find_tables()`

PyMuPDF 1.24+ has built-in table detection (`page.find_tables()`). Tables are extracted as markdown, then treated as atomic chunks.

```python
def extract_tables(page) -> list[dict]:
    """Extract tables as markdown chunks."""
    tables = page.find_tables()
    results = []
    for i, table in enumerate(tables.tables):
        md = table.to_markdown()
        results.append({
            "text": md,
            "chunk_type": "table",
            "page_num": page.number,
            "table_index": i,
        })
    return results
```

**Critical:** Tables are emitted as **atomic chunks** (never split). Each carries `chunk_type: "table"` metadata.

### Pattern 3: EasyOCR Page Rasterization

For pages needing OCR, render the PDF page to a pixmap at 200-300 DPI, convert to numpy array, feed to EasyOCR.

```python
import numpy as np

def ocr_page(page, reader) -> str:
    """Render PDF page and OCR it."""
    # 200 DPI: good balance of accuracy vs speed
    pix = page.get_pixmap(dpi=200)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n
    )
    results = reader.readtext(img, detail=0, paragraph=True)
    return "\n".join(results)
```

**Key insight:** PyMuPDF can render pages to pixmaps directly (`page.get_pixmap(dpi=200)`) — no need for `pdf2image` or Poppler. This eliminates the Poppler system dependency entirely.

### Pattern 4: Structure-Aware Chunking

Split on paragraph boundaries (`\n\n`) first, then line boundaries (`\n`), then sentence boundaries. Never split inside a table or heading.

```python
def chunk_text(
    text: str,
    doc_id: str,
    page_num: int,
    max_tokens: int = 700,
    overlap_tokens: int = 100,
) -> list[dict]:
    """Structure-aware chunking with overlap."""
    # Split on double-newlines (paragraphs) first
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    # ... accumulate paragraphs until max_tokens, then start new chunk with overlap
    return chunks
```

**Chunk parameters:**
- Target: 500–800 tokens per chunk
- Overlap: 100–150 tokens
- Atomic units: tables, headings (never split)
- Metadata per chunk: `doc_id`, `page_num`, `chunk_type`, `chunk_index`

### Pattern 5: ChromaDB with Embedding-Model Metadata

```python
import chromadb
from chromadb.config import Settings

def get_chroma_client(path: str = "data/chroma") -> chromadb.ClientAPI:
    """Create PersistentClient with telemetry off."""
    return chromadb.PersistentClient(
        path=path,
        settings=Settings(anonymized_telemetry=False),
    )

def get_or_create_collection(client, embed_model: str, embed_dim: int):
    """Get/create collection with embedding model metadata."""
    return client.get_or_create_collection(
        name="documents",
        metadata={
            "embedding_model": embed_model,
            "embedding_dim": embed_dim,
            "hnsw:space": "cosine",
        },
    )
```

**Startup validation:** On app start, read collection metadata and compare against current config. If `embedding_model` or `embedding_dim` differs → raise a clear error instructing the user to reset or rebuild.

## Don't Hand-Roll

| Problem | Use Instead | Why |
|---------|-------------|-----|
| PDF table detection | `page.find_tables()` + `table.to_markdown()` | PyMuPDF 1.24+ handles this natively; hand-parsing table cells from text blocks is fragile |
| PDF page rasterization | `page.get_pixmap(dpi=200)` | Built into PyMuPDF; no need for `pdf2image` + Poppler dependency |
| Token counting | `tiktoken` (`cl100k_base` encoding) | Character-based length estimates are unreliable for chunk sizing |
| Vector distance metric config | ChromaDB collection `metadata={"hnsw:space": "cosine"}` | Set once at creation; ChromaDB handles indexing |
| Embedding batching | Already implemented in `NIMClient.embed()` (Phase 1) | 32 chunks/request with retry/backoff |

## Common Pitfalls

### Pitfall 1: EasyOCR First-Run Download (~2GB)

**Problem:** First call to `Reader(['en'])` downloads detector + recognizer models. On demo machines this causes a multi-minute hang.

**Solution:** Pre-download during `tasks.ps1 setup`:
```powershell
python -c "import easyocr; easyocr.Reader(['en'], gpu=False)"
```

Cache the Reader with `@st.cache_resource` so Streamlit reruns don't re-instantiate it.

### Pitfall 2: PyMuPDF Multi-Column Interleaving

**Problem:** `get_text("text")` walks content in draw order, not reading order for multi-column layouts.

**Solution:** Use `page.get_text("blocks")` which returns positioned text blocks with bounding boxes — then sort by `(y0, x0)` for reading order. Or use `page.get_text("text", sort=True)` (available in PyMuPDF 1.23+) which re-synthesizes reading order.

### Pitfall 3: Embedding Model Mismatch

**Problem:** Ingest and query paths use different embedding models silently.

**Solution:**
1. Single constant `EMBEDDING_MODEL` from `core/config.py` used by both paths
2. ChromaDB collection stores `embedding_model` + `embedding_dim` in metadata
3. Startup assertion: if collection exists and metadata differs from config → hard error

### Pitfall 4: ChromaDB Telemetry + In-Memory Default

**Problem:** Default `Client()` is in-memory (data lost on restart); telemetry adds latency.

**Solution:** Always `PersistentClient(path="data/chroma", settings=Settings(anonymized_telemetry=False))`. Use `get_or_create_collection` (not `create_collection`) for idempotency.

### Pitfall 5: Chunking Splits Tables and Headings

**Problem:** Naive character splitters cut mid-table-row, producing garbage retrieval.

**Solution:** Extract tables as atomic chunks BEFORE running the text chunker on remaining content. Detect headings (lines followed by `\n` that are short and possibly uppercase/bold) and keep them attached to the following paragraph.

### Pitfall 6: Poppler System Dependency

**Problem:** `pdf2image` requires Poppler binaries — breaks the "no external system binaries" constraint.

**Solution:** Use `page.get_pixmap()` from PyMuPDF instead. PyMuPDF is pure-pip-install and handles page rasterization natively. **Do NOT add `pdf2image` to dependencies.**

## Code Examples

### Full Extraction Pipeline (Pseudocode)

```python
def extract_document(pdf_path: str, ocr_reader) -> list[dict]:
    """Full extraction: text + tables + OCR fallback."""
    doc = pymupdf.open(pdf_path)
    all_content = []

    for page in doc:
        # 1. Try table extraction first (tables are atomic)
        tables = extract_tables(page)
        all_content.extend(tables)

        # 2. Extract remaining text
        text = page.get_text("text", sort=True)

        # 3. OCR fallback if insufficient text
        if len(text.strip()) < 50:
            text = ocr_page(page, ocr_reader)

        if text.strip():
            all_content.append({
                "text": text,
                "chunk_type": "text",
                "page_num": page.number,
            })

    doc.close()
    return all_content
```

### ChromaDB Add with Metadata

```python
def add_to_vectorstore(collection, chunks: list[dict], embeddings: list[list[float]], doc_id: str):
    """Add chunks with full metadata."""
    collection.add(
        ids=[f"{doc_id}_chunk_{i}" for i in range(len(chunks))],
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[
            {
                "doc_id": doc_id,
                "page_num": c["page_num"],
                "chunk_type": c.get("chunk_type", "text"),
                "chunk_index": i,
            }
            for i, c in enumerate(chunks)
        ],
    )
```

### Embedding Model Mismatch Detection

```python
def validate_collection_model(collection, current_model: str, current_dim: int):
    """Assert collection was built with the same embedding model."""
    meta = collection.metadata or {}
    stored_model = meta.get("embedding_model")
    stored_dim = meta.get("embedding_dim")

    if stored_model and stored_model != current_model:
        raise RuntimeError(
            f"Collection was built with '{stored_model}' but current config uses '{current_model}'. "
            f"Delete data/chroma/ and re-ingest, or update NVIDIA_EMBED_MODEL."
        )
    if stored_dim and int(stored_dim) != current_dim:
        raise RuntimeError(
            f"Collection has embedding_dim={stored_dim} but current model produces dim={current_dim}. "
            f"Delete data/chroma/ and re-ingest."
        )
```

## Key Dimensions

| Dimension | Value | Source |
|-----------|-------|--------|
| Embedding model | `nvidia/nv-embedqa-e5-v5` | config.py (Phase 1) |
| Embedding dim | 1024 | NVIDIA docs |
| Chunk size target | 500–800 tokens | PITFALLS #6 |
| Chunk overlap | 100–150 tokens | PITFALLS #6 |
| Batch size | 32 chunks/request | Phase 1 `NIMClient.embed()` |
| OCR threshold | `< 50 chars` per page | PITFALLS #2, ARCHITECTURE |
| OCR render DPI | 200 | PITFALLS #2 |
| ChromaDB distance | cosine | Standard for embedding retrieval |
| Telemetry | OFF | PITFALLS #7 |

## Architectural Responsibility Map

| Component | Tier | File | Responsibility |
|-----------|------|------|----------------|
| Extractor | core | `core/extractor.py` | PDF text extraction + scanned-page detection |
| OCR | core | `core/ocr.py` | EasyOCR wrapper (lazy-loaded, cached reader) |
| Chunker | core | `core/chunker.py` | Structure-aware text splitting + chunk metadata |
| VectorStore | core | `core/vectorstore.py` | ChromaDB wrapper (add, query, delete_by_doc, validate) |
| Embedder | core | `core/embedder.py` | Thin wrapper calling `NIMClient.embed()` with model config |

## Dependencies on Phase 1

- `core/config.py` → `Settings.nvidia_embed_model` (embedding model name)
- `core/llm_client.py` → `NIMClient.embed()` (batched embedding with retry)
- `pyproject.toml` → add `pymupdf`, `easyocr`, `chromadb`, `tiktoken` to dependencies

## Open Questions (Resolved)

| Question | Resolution |
|----------|-----------|
| Need `pdf2image` + Poppler? | **No** — PyMuPDF `page.get_pixmap()` handles rasterization natively |
| Use LlamaIndex chunker? | **No for Phase 2** — custom structure-aware chunker is simpler and gives full control. LlamaIndex integration deferred to Phase 3 pipeline |
| Embedding dim for `nv-embedqa-e5-v5`? | **1024** (confirmed via NVIDIA API docs) |
| ChromaDB HNSW distance metric? | **cosine** (standard for normalized embeddings) |

---
*Research completed: 2026-04-28*

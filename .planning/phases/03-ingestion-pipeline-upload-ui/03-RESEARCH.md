# Phase 3: Ingestion Pipeline + Upload UI - Research

**Researched:** 2026-04-28
**Domain:** Streamlit upload UI + orchestration pipeline + content-hash idempotent ingestion + ChromaDB dedupe
**Confidence:** HIGH

## Summary

Phase 3 is a composition phase — all hard integrations (PDF extraction, OCR, chunking, embedding, ChromaDB) were solved in Phases 1–2. This phase wires them into an orchestration pipeline (`pipelines/ingest.py`) triggered by a Streamlit upload UI (`ui/upload.py`), with content-hash-based idempotent re-uploads, `st.status` progress tracking, sample-document one-click loading, and a delete/reset capability. The `@st.cache_resource` singleton pattern prevents heavy-resource re-instantiation across Streamlit reruns.

The primary risk is Streamlit's "rerun the whole script" model: every widget interaction re-executes `app.py` top-to-bottom, so any resource not cached via `@st.cache_resource` gets re-created. The secondary risk is the `st.file_uploader` widget returning `None` on subsequent reruns after the file has been consumed — the file bytes must be persisted to disk and tracked in `st.session_state` immediately on first receipt.

**Primary recommendation:** Build `pipelines/ingest.py` as a pure-Python function (no Streamlit imports) that accepts a file path and returns a result dataclass. Wrap it in `ui/upload.py` which handles `st.file_uploader`, `st.status` progress, `st.session_state` document tracking, and `@st.cache_resource` singletons. Keep the pipeline testable without Streamlit.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INGEST-01 | User can upload PDF, scanned PDF, and image-based document files via the web UI | `st.file_uploader(type=["pdf", "png", "jpg", "jpeg", "tiff"])` with file-type whitelist; save to `data/uploads/` keyed by content hash |
| INGEST-04 | Bundled sample docs in `data/samples/` loadable with one click | `pathlib.Path("data/samples").glob("*.pdf")` listed as buttons; same ingest pipeline as upload |
| INGEST-05 | Re-uploading the same file is idempotent (content-hash dedupe) | `hashlib.sha256(file_bytes).hexdigest()` as `doc_id`; check ChromaDB `collection.get(where={"doc_id": hash})` before ingesting |
| INGEST-06 | Upload UI shows progress (`st.status`) and surfaces errors clearly | `with st.status("Processing...", expanded=True) as status:` with `st.write()` per stage and `status.update()` on completion |
| IDX-05 | Semantic top-k retrieval (k=3–5) supports filtering by `doc_id` | Already implemented in `VectorStore.query(doc_id=...)` — phase 3 only needs to pass `doc_id` through the pipeline |
| IDX-06 | Delete document removes vectors + cached files cleanly | `VectorStore.delete_by_doc(doc_id)` + `os.remove(data/uploads/{hash}.pdf)` + remove from `st.session_state.documents` |
| UX-03 | Heavy resources wrapped in `@st.cache_resource` | Singleton factory functions for `NIMClient`, `OCRReader`, `VectorStore`, `Embedder` decorated with `@st.cache_resource` |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| File upload widget | Frontend (Streamlit) | — | `st.file_uploader` is a Streamlit-native widget |
| Content-hash computation | Pipeline (Python) | — | Pure `hashlib` operation, no UI or storage dependency |
| Idempotent dedupe check | Pipeline + Storage | — | Pipeline queries ChromaDB before ingesting |
| Extract → OCR → Chunk → Embed → Persist | Pipeline orchestration | Core modules | `pipelines/ingest.py` composes `core/extractor`, `core/ocr`, `core/chunker`, `core/embedder`, `core/vectorstore` |
| Progress display | Frontend (Streamlit) | — | `st.status` context manager for stage-by-stage feedback |
| Sample document loading | Frontend (Streamlit) | Pipeline | UI lists samples, pipeline ingests them identically to uploads |
| Document deletion | Pipeline + Storage | Frontend (Streamlit) | Pipeline deletes from ChromaDB + filesystem; UI updates session_state |
| Resource caching | Frontend (Streamlit) | — | `@st.cache_resource` prevents re-instantiation across Streamlit reruns |

## Standard Stack

### Core

All libraries are already in `pyproject.toml` from Phases 1–2. No new dependencies needed for Phase 3.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `hashlib` (stdlib) | Python 3.10+ | SHA-256 content hashing for dedupe | Built-in, no dependency; SHA-256 is the standard for content-addressable storage [VERIFIED: Python stdlib] |
| `pathlib` (stdlib) | Python 3.10+ | File path management for uploads/samples/cache | Built-in, cross-platform path handling [VERIFIED: Python stdlib] |
| `shutil` (stdlib) | Python 3.10+ | File copy/move for saving uploads | Built-in [VERIFIED: Python stdlib] |
| `streamlit` | >=1.40 | `st.file_uploader`, `st.status`, `st.cache_resource`, `st.session_state` | Already pinned in pyproject.toml [VERIFIED: pyproject.toml] |
| `chromadb` | >=0.5 | `collection.get(where=...)` for existence check, `delete(where=...)` for cleanup | Already pinned; `get_or_create_collection` and where-filter are stable API [VERIFIED: ChromaDB docs] |

### Supporting

No additional supporting libraries needed. Phase 3 is pure composition over existing deps.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `hashlib.sha256` | `xxhash` (faster non-crypto hash) | SHA-256 is fast enough for <100 MB PDFs; xxhash adds a dep for zero user-visible benefit in a POC |
| `st.status` context manager | `st.progress` + `st.spinner` | `st.status` is purpose-built for multi-stage progress with expandable output; `st.progress` is for single-bar progress only |
| Saving file to disk + hash as filename | Storing file bytes in `st.session_state` | Files must survive Streamlit reruns AND be accessible to PyMuPDF (which needs a file path, not bytes); disk persistence is the correct pattern |

## Architecture Patterns

### System Architecture Diagram

```
[User Browser]
    │
    ▼
[Streamlit app.py]
    │
    ├──► st.file_uploader ──► UploadedFile.getvalue() ──► SHA-256 hash
    │                                                         │
    │   ┌─────────────────────────────────────────────────────┘
    │   ▼
    │   Hash already in ChromaDB? ──YES──► Skip, show "Already indexed"
    │   │
    │   NO
    │   ▼
    │   Save bytes to data/uploads/{hash}.pdf
    │   │
    │   ▼
    │   pipelines/ingest.py
    │   ├── extractor.extract_document(path, ocr_reader)
    │   ├── chunker.chunk_document(pages, doc_id=hash)
    │   ├── vectorstore.add(chunks, doc_id=hash)
    │   └── Return IngestResult(doc_id, chunk_count, pages, ...)
    │
    ├──► st.status ──► Stage-by-stage progress updates
    │
    ├──► st.session_state.documents ──► Document list in sidebar
    │
    └──► Delete button ──► vectorstore.delete_by_doc(doc_id)
                           + os.remove(data/uploads/{hash}.pdf)
```

### Recommended Project Structure

```
pipelines/
├── __init__.py
└── ingest.py          # ingest_document(file_path, doc_id, vectorstore, ocr_reader) -> IngestResult
ui/
├── __init__.py
├── upload.py          # render_upload_ui() — file uploader + sample loader + progress
└── sidebar.py         # render_sidebar() — document list + delete buttons
```

### Pattern 1: Content-Hash Idempotent Ingestion

**What:** Compute SHA-256 of uploaded file bytes, use as `doc_id`. Before ingesting, check if ChromaDB already has chunks with that `doc_id`. If yes, skip. If no, run the full pipeline.

**When to use:** Every file upload and sample-doc load.

**Example:**
```python
# Source: Python stdlib hashlib + ChromaDB where-filter
import hashlib

def compute_content_hash(file_bytes: bytes) -> str:
    """SHA-256 hex digest of file content."""
    return hashlib.sha256(file_bytes).hexdigest()

def is_already_indexed(vectorstore, doc_id: str) -> bool:
    """Check if any chunks exist for this doc_id in ChromaDB."""
    results = vectorstore._collection.get(
        where={"doc_id": doc_id},
        limit=1,
    )
    return len(results["ids"]) > 0
```

[VERIFIED: hashlib is Python stdlib; ChromaDB `collection.get(where=...)` is stable API per ChromaDB docs]

### Pattern 2: Streamlit @st.cache_resource Singletons

**What:** Decorate factory functions with `@st.cache_resource` so heavy objects (VectorStore, OCRReader, NIMClient, Embedder) are instantiated once per Streamlit server process, surviving reruns.

**When to use:** Every heavy resource that is expensive to create.

**Example:**
```python
# Source: Streamlit docs — st.cache_resource
import streamlit as st
from core.config import get_settings
from core.llm_client import NIMClient
from core.ocr import OCRReader
from core.embedder import Embedder
from core.vectorstore import VectorStore

@st.cache_resource
def get_nim_client() -> NIMClient:
    return NIMClient(get_settings())

@st.cache_resource
def get_ocr_reader() -> OCRReader:
    return OCRReader(languages=["en"])

@st.cache_resource
def get_vectorstore() -> VectorStore:
    embedder = Embedder(nim_client=get_nim_client())
    vs = VectorStore(persist_path="data/chroma", embedder=embedder)
    vs.validate_model()
    return vs
```

**Critical:** `@st.cache_resource` objects are global singletons shared across all sessions. They must be thread-safe for read operations. ChromaDB PersistentClient is thread-safe for reads and writes. [CITED: Streamlit docs — st.cache_resource: "Objects cached by st.cache_resource act like singletons and can mutate."]

### Pattern 3: st.status for Multi-Stage Progress

**What:** Use `st.status` as a context manager that shows an expandable progress container with stage-by-stage updates.

**When to use:** During the ingest pipeline (extract → OCR → chunk → embed → persist).

**Example:**
```python
# Source: Streamlit docs — st.status
with st.status("Processing document...", expanded=True) as status:
    st.write("📄 Extracting text...")
    pages = extractor.extract_document(file_path, ocr_reader)
    st.write(f"✅ Extracted {len(pages)} pages")

    st.write("✂️ Chunking...")
    chunks = chunker.chunk_document(pages, doc_id)
    st.write(f"✅ Created {len(chunks)} chunks")

    st.write("🔢 Embedding & indexing...")
    vectorstore.add(chunks, doc_id)
    st.write(f"✅ Indexed {len(chunks)} chunks")

    status.update(label="Document processed!", state="complete", expanded=False)
```

[CITED: Streamlit docs — "Display output of long-running tasks in a container. `with st.status('Running'): do_something_slow()`"]

### Pattern 4: st.file_uploader Bytes Handling

**What:** `st.file_uploader` returns an `UploadedFile` object (or `None`). Call `.getvalue()` to get bytes for hashing, then save to disk for PyMuPDF (which needs a file path, not a bytes buffer).

**When to use:** On every upload event.

**Example:**
```python
# Source: Streamlit docs — st.file_uploader
uploaded_file = st.file_uploader(
    "Upload a document",
    type=["pdf"],
    key="doc_upload",
)
if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    doc_id = compute_content_hash(file_bytes)

    # Save to disk — PyMuPDF needs a file path
    upload_path = Path("data/uploads") / f"{doc_id}.pdf"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(file_bytes)
```

[CITED: Streamlit docs — `uploaded_file.getvalue()` returns bytes; `type` parameter filters allowed extensions]

### Pattern 5: Session State Document Tracking

**What:** Maintain a list of indexed documents in `st.session_state` so the document list survives reruns. Hydrate from ChromaDB on first run.

**When to use:** Document list in sidebar, delete buttons, doc_id filtering.

**Example:**
```python
# Source: Streamlit docs — st.session_state
if "documents" not in st.session_state:
    # Hydrate from ChromaDB on first run
    st.session_state.documents = _load_indexed_documents(vectorstore)

# After successful ingestion:
st.session_state.documents.append({
    "doc_id": doc_id,
    "filename": uploaded_file.name,
    "chunk_count": len(chunks),
    "indexed_at": datetime.now().isoformat(),
})
```

[CITED: Streamlit docs — "Session State is a way to share variables between reruns, for each user session."]

### Anti-Patterns to Avoid

- **Instantiating heavy resources at module level or inside callbacks:** Use `@st.cache_resource` factory functions instead. Module-level instantiation runs on every import; callback instantiation runs on every click.
- **Storing file bytes in `st.session_state`:** Session state lives in server memory. A 50MB PDF stored there for every user session will exhaust memory. Save to disk, track metadata in session state.
- **Using `st.file_uploader` key as the file identifier:** The key is a widget identifier, not a content identifier. Two different files uploaded to the same widget key produce different bytes but the same key.
- **Calling `vectorstore.add()` without checking for existing doc_id:** ChromaDB will raise on duplicate IDs. Always check existence first or use a prefix-based ID scheme that includes the doc_id hash.
- **Using `collection.upsert()` instead of check-then-add:** Upsert silently overwrites, which sounds idempotent, but it would re-embed all chunks on every re-upload — expensive and wasteful. Check-then-skip is the correct pattern for content-hash dedupe.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Content hashing | Custom hash or file-name-based dedup | `hashlib.sha256(bytes).hexdigest()` | Stdlib, collision-resistant, deterministic; file names are not unique identifiers |
| File type validation | Extension string parsing | `st.file_uploader(type=[...])` + magic byte check on backend | Streamlit handles the UI-side filtering; magic bytes prevent extension spoofing |
| Multi-stage progress UI | Custom HTML/JS progress bars | `st.status()` context manager with `st.write()` per stage | Purpose-built for this exact use case; auto-handles expand/collapse/completion state |
| Resource singleton management | Global variables or `__init__` guards | `@st.cache_resource` decorated factory functions | Handles Streamlit's rerun model correctly; supports TTL, clear, and validation |
| Document list persistence across reruns | Writing to a JSON file on every change | `st.session_state` dict hydrated from ChromaDB on first run | Session state is the Streamlit-native way to persist UI state across reruns |
| File path management | String concatenation | `pathlib.Path` | Cross-platform, composable, type-safe |

**Key insight:** Phase 3 has zero novel problems. Every sub-task maps to a stdlib facility or Streamlit built-in. The value is in correct composition, not invention.

## Common Pitfalls

### Pitfall 1: Streamlit Re-runs Re-instantiate Everything

**What goes wrong:** Every widget interaction (button click, slider move, file upload) re-executes `app.py` from top to bottom. If `VectorStore()`, `OCRReader()`, or `NIMClient()` are created inline, they re-instantiate on every click — adding 2–5 seconds per interaction and potentially exhausting memory.

**Why it happens:** Streamlit's execution model is "re-run the script." Developers from Flask/FastAPI don't expect this.

**How to avoid:** All heavy resources behind `@st.cache_resource` factory functions. These execute once per Streamlit server process and return the cached singleton on subsequent runs.

**Warning signs:** Spinner appears on every keypress; memory usage climbs with each interaction; "ChromaDB client created" log messages on every rerun.

### Pitfall 2: st.file_uploader Returns None After Consumption

**What goes wrong:** `st.file_uploader` returns an `UploadedFile` object only on the rerun triggered by the upload event. On subsequent reruns (e.g., when the user clicks a different widget), it returns `None`. If the code relies on `uploaded_file` being non-None to display the document, the document "disappears" from the UI.

**Why it happens:** Streamlit file uploader is ephemeral by default. The `UploadedFile` object lives in a temporary buffer that's cleared.

**How to avoid:** On first receipt, immediately: (1) compute content hash, (2) save bytes to `data/uploads/{hash}.pdf`, (3) add metadata to `st.session_state.documents`. Never rely on `uploaded_file` being available on subsequent reruns.

**Warning signs:** Uploaded document vanishes from UI after clicking any other widget; file processing triggers twice (once from upload, once from a stale reference).

### Pitfall 3: ChromaDB Duplicate ID Error on Re-ingest

**What goes wrong:** If the same file is ingested twice, `collection.add()` generates the same IDs (`{doc_id}_chunk_0`, `{doc_id}_chunk_1`, ...) and ChromaDB raises `IDAlreadyExistsError`.

**Why it happens:** The current `VectorStore.add()` generates IDs from `doc_id` + sequential index. Re-uploading the same file produces identical IDs.

**How to avoid:** Check existence BEFORE calling `vectorstore.add()`. Use `collection.get(where={"doc_id": doc_id}, limit=1)` — if results are non-empty, skip ingestion. This is the content-hash dedupe pattern.

**Warning signs:** `chromadb.errors.IDAlreadyExistsError` in logs; duplicate entries in the document list.

### Pitfall 4: PyMuPDF Needs a File Path, Not Bytes

**What goes wrong:** `pymupdf.open()` can accept a file path or a bytes buffer with a `filetype` parameter, but the OCR fallback path re-opens the document by path. If the file was never saved to disk (only held in memory), the OCR re-open fails.

**Why it happens:** The `extract_document()` function opens the PDF by path in two places: once for text extraction, once for OCR rendering. Both need a valid file path.

**How to avoid:** Always save uploaded file bytes to `data/uploads/{doc_id}.pdf` before calling the ingestion pipeline. Pass the file path (not bytes) to the pipeline.

**Warning signs:** `FileNotFoundError` on OCR pages; OCR fallback silently skipped.

### Pitfall 5: Sample Documents Not Found on Fresh Clone

**What goes wrong:** `data/samples/` is committed to git but `data/uploads/` and `data/chroma/` are gitignored. If the code assumes `data/uploads/` exists at startup, it crashes. If sample loading copies to `data/uploads/` first, the directory must be created.

**Why it happens:** Runtime directories are gitignored (correctly), but the code doesn't create them lazily.

**How to avoid:** Use `Path.mkdir(parents=True, exist_ok=True)` before any write to `data/uploads/`, `data/cache/`, or `data/chroma/`. The ingest pipeline should ensure directories exist.

**Warning signs:** `FileNotFoundError` or `OSError: [Errno 2]` on first upload or sample load after a fresh clone.

### Pitfall 6: Delete Document Leaves Orphaned Files

**What goes wrong:** `VectorStore.delete_by_doc(doc_id)` removes vectors from ChromaDB but doesn't remove the uploaded file from `data/uploads/` or any cached extraction results from `data/cache/`. Disk usage grows; re-uploading the "same" file skips ingestion (hash matches session_state) but the old file is still on disk.

**Why it happens:** The vectorstore wrapper only knows about ChromaDB, not the filesystem.

**How to avoid:** The delete operation must be a pipeline-level function that: (1) calls `vectorstore.delete_by_doc(doc_id)`, (2) removes `data/uploads/{doc_id}.pdf` if it exists, (3) removes `data/cache/{doc_id}.*` if any, (4) removes the document from `st.session_state.documents`.

**Warning signs:** Disk usage grows after repeated upload/delete cycles; files in `data/uploads/` don't match the document list.

## Code Examples

### Full Ingest Pipeline (pipelines/ingest.py)

```python
# Source: Composition of Phase 1-2 APIs + hashlib stdlib
"""Document ingestion pipeline: hash → check → extract → chunk → embed → persist."""

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

from core.chunker import chunk_document
from core.extractor import extract_document

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    doc_id: str
    filename: str
    chunk_count: int
    page_count: int
    already_indexed: bool = False
    error: str | None = None


def compute_content_hash(file_bytes: bytes) -> str:
    """SHA-256 hex digest of file content."""
    return hashlib.sha256(file_bytes).hexdigest()


def save_upload(file_bytes: bytes, doc_id: str, upload_dir: str = "data/uploads") -> Path:
    """Save uploaded file bytes to disk, return the path."""
    upload_path = Path(upload_dir) / f"{doc_id}.pdf"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(file_bytes)
    return upload_path


def is_already_indexed(vectorstore, doc_id: str) -> bool:
    """Check if any chunks for this doc_id exist in ChromaDB."""
    results = vectorstore._collection.get(
        where={"doc_id": doc_id},
        limit=1,
    )
    return len(results["ids"]) > 0


def ingest_document(
    file_path: str | Path,
    doc_id: str,
    filename: str,
    vectorstore,
    ocr_reader=None,
) -> IngestResult:
    """Run the full ingest pipeline: extract → chunk → embed → persist.

    Args:
        file_path: Path to the PDF file on disk.
        doc_id: Content hash used as document identifier.
        filename: Original filename for display.
        vectorstore: VectorStore instance.
        ocr_reader: Optional OCRReader for scanned pages.

    Returns:
        IngestResult with doc metadata and status.
    """
    try:
        # Check dedupe
        if is_already_indexed(vectorstore, doc_id):
            return IngestResult(
                doc_id=doc_id,
                filename=filename,
                chunk_count=0,
                page_count=0,
                already_indexed=True,
            )

        # Extract
        pages = extract_document(str(file_path), ocr_reader)

        # Chunk
        chunks = chunk_document(pages, doc_id)

        # Embed + persist (VectorStore.add handles embedding internally)
        vectorstore.add(chunks, doc_id)

        return IngestResult(
            doc_id=doc_id,
            filename=filename,
            chunk_count=len(chunks),
            page_count=len(set(p["page_num"] for p in pages)),
        )
    except Exception as e:
        logger.exception("Ingestion failed for %s", filename)
        return IngestResult(
            doc_id=doc_id,
            filename=filename,
            chunk_count=0,
            page_count=0,
            error=str(e),
        )


def delete_document(doc_id: str, vectorstore, upload_dir: str = "data/uploads") -> None:
    """Delete a document's vectors and cached files."""
    vectorstore.delete_by_doc(doc_id)
    upload_path = Path(upload_dir) / f"{doc_id}.pdf"
    if upload_path.exists():
        upload_path.unlink()
```

### Streamlit Upload UI (ui/upload.py)

```python
# Source: Streamlit docs — st.file_uploader + st.status + st.session_state
"""Upload UI with progress tracking and sample document loading."""

import streamlit as st
from pathlib import Path
from pipelines.ingest import (
    compute_content_hash,
    save_upload,
    ingest_document,
    delete_document,
)


def _init_session_state():
    if "documents" not in st.session_state:
        st.session_state.documents = []


def render_upload_ui(vectorstore, ocr_reader):
    """Render the file upload widget and process uploaded files."""
    _init_session_state()

    uploaded_file = st.file_uploader(
        "Upload a PDF document",
        type=["pdf"],
        key="doc_upload",
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        doc_id = compute_content_hash(file_bytes)

        # Check if already tracked in session
        known_ids = {d["doc_id"] for d in st.session_state.documents}
        if doc_id in known_ids:
            st.info(f"'{uploaded_file.name}' is already indexed.")
            return

        # Save to disk
        file_path = save_upload(file_bytes, doc_id)

        # Ingest with progress
        with st.status("Processing document...", expanded=True) as status:
            st.write("📄 Extracting text and detecting scanned pages...")
            result = ingest_document(file_path, doc_id, uploaded_file.name, vectorstore, ocr_reader)

            if result.error:
                status.update(label="Error!", state="error")
                st.error(f"Failed: {result.error}")
                return

            if result.already_indexed:
                status.update(label="Already indexed", state="complete", expanded=False)
                st.info(f"'{uploaded_file.name}' was already indexed.")
            else:
                st.write(f"✅ {result.page_count} pages, {result.chunk_count} chunks indexed")
                status.update(label="Document processed!", state="complete", expanded=False)

            st.session_state.documents.append({
                "doc_id": doc_id,
                "filename": uploaded_file.name,
                "chunk_count": result.chunk_count,
            })


def render_sample_loader(vectorstore, ocr_reader):
    """Render one-click sample document loader."""
    _init_session_state()
    samples_dir = Path("data/samples")
    if not samples_dir.exists():
        return

    samples = sorted(samples_dir.glob("*.pdf"))
    if not samples:
        return

    st.subheader("📚 Sample Documents")
    for sample in samples:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text(sample.name)
        with col2:
            if st.button("Load", key=f"load_{sample.name}"):
                file_bytes = sample.read_bytes()
                doc_id = compute_content_hash(file_bytes)
                # Ingest follows same path as upload
                ...
```

### @st.cache_resource Factory Functions (core/__init__.py or ui helpers)

```python
# Source: Streamlit docs — @st.cache_resource
import streamlit as st
from core.config import get_settings
from core.llm_client import NIMClient
from core.ocr import OCRReader
from core.embedder import Embedder
from core.vectorstore import VectorStore


@st.cache_resource
def get_nim_client():
    """Singleton NIMClient — survives Streamlit reruns."""
    return NIMClient(get_settings())


@st.cache_resource
def get_ocr_reader():
    """Singleton OCRReader — avoids 2GB reload per rerun."""
    return OCRReader(languages=["en"])


@st.cache_resource
def get_embedder():
    """Singleton Embedder — shares NIMClient."""
    return Embedder(nim_client=get_nim_client())


@st.cache_resource
def get_vectorstore():
    """Singleton VectorStore — validates embedding model on creation."""
    vs = VectorStore(persist_path="data/chroma", embedder=get_embedder())
    vs.validate_model()
    return vs
```

[CITED: Streamlit docs — "Objects cached by st.cache_resource act like singletons and can mutate. To cache data and return copies, use st.cache_data instead."]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `st.spinner` + manual state management | `st.status` context manager (expandable, multi-stage) | Streamlit 1.25+ | Purpose-built for multi-step pipelines; auto expand/collapse |
| `@st.experimental_singleton` | `@st.cache_resource` | Streamlit 1.18+ | `experimental_singleton` is deprecated; `cache_resource` is the stable replacement |
| Global variables for singletons | `@st.cache_resource` | Streamlit 1.18+ | Global vars don't handle Streamlit's rerun model correctly; cache_resource does |
| `chromadb.Client()` (in-memory) | `chromadb.PersistentClient(path=...)` | ChromaDB 0.4+ | In-memory loses index on restart; PersistentClient survives Streamlit reloads |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `st.status` supports `state="error"` parameter for error display | Code Examples — render_upload_ui | Minor — would need to use `st.error()` outside the status container instead |
| A2 | ChromaDB `collection.get(where={"doc_id": hash}, limit=1)` is efficient for existence checks | Pattern 1 | Low — even a full scan of a small POC collection is <10ms; could add a local set cache if needed |
| A3 | `@st.cache_resource` functions can call other `@st.cache_resource` functions (nested singletons) | Pattern 2 — get_vectorstore calls get_embedder | Low — Streamlit docs show nested cache calls; well-established pattern |

## Open Questions

1. **Sample document selection**
   - What we know: Sample PDFs go in `data/samples/`, loaded via one-click buttons
   - What's unclear: Exact set of sample documents (digital PDF, scanned PDF, multi-column, table-heavy) — need to source or create these
   - Recommendation: Include 3–4 small PDFs (<5 pages each) covering the test matrix; create synthetic test PDFs if no suitable open-source samples are available

2. **Document metadata hydration from ChromaDB**
   - What we know: `st.session_state.documents` tracks indexed docs; ChromaDB stores chunks with `doc_id` metadata
   - What's unclear: How to reconstruct the document list (with filenames) from ChromaDB on a fresh session when only `doc_id` hashes are stored
   - Recommendation: Store `filename` as additional metadata on chunks, or maintain a simple JSON manifest at `data/uploads/manifest.json`

3. **Accepted file types beyond PDF**
   - What we know: INGEST-01 says "PDF, scanned PDF, and image-based document files"
   - What's unclear: Whether "image-based" means standalone images (.png/.jpg) or image-heavy PDFs
   - Recommendation: Start with PDF-only (`type=["pdf"]`); the existing extractor handles scanned PDFs via OCR. Standalone image support would need a separate extraction path — defer unless required.

## Environment Availability

Step 2.6: SKIPPED (no external dependencies identified — Phase 3 is pure composition over Phase 1–2 packages already installed and verified).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_ingest_pipeline.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INGEST-01 | Upload triggers ingest pipeline | unit | `uv run pytest tests/test_ingest_pipeline.py::test_ingest_document -x` | ❌ Wave 0 |
| INGEST-04 | Sample docs loadable via same pipeline | unit | `uv run pytest tests/test_ingest_pipeline.py::test_ingest_sample_document -x` | ❌ Wave 0 |
| INGEST-05 | Content-hash dedupe skips re-upload | unit | `uv run pytest tests/test_ingest_pipeline.py::test_dedupe_skips_reupload -x` | ❌ Wave 0 |
| INGEST-06 | Ingest returns error on failure | unit | `uv run pytest tests/test_ingest_pipeline.py::test_ingest_error_handling -x` | ❌ Wave 0 |
| IDX-05 | Query filters by doc_id | unit | `uv run pytest tests/test_vectorstore.py::test_query_with_doc_id_filter -x` | ❌ Wave 0 |
| IDX-06 | Delete removes vectors + files | unit | `uv run pytest tests/test_ingest_pipeline.py::test_delete_document -x` | ❌ Wave 0 |
| UX-03 | @st.cache_resource singletons | manual-only | Manual — verify heavy resources don't re-instantiate on Streamlit rerun | N/A |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_ingest_pipeline.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_ingest_pipeline.py` — covers INGEST-01, INGEST-04, INGEST-05, INGEST-06, IDX-06
- [ ] Update `tests/test_vectorstore.py` — add IDX-05 doc_id filter test

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — single-user local POC |
| V3 Session Management | no | N/A — Streamlit handles sessions internally |
| V4 Access Control | no | N/A — single-user local POC |
| V5 Input Validation | yes | Whitelist file types via `st.file_uploader(type=["pdf"])`; validate file size; do not trust file extension alone |
| V6 Cryptography | no | SHA-256 used for content hashing (integrity, not security) |

### Known Threat Patterns for Streamlit + PDF Upload

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious PDF exploiting parser CVE | Tampering | Whitelist allowed MIME types; keep PyMuPDF updated; run in sandboxed environment |
| Oversized file upload DoS | Denial of Service | Set `server.maxUploadSize` in `.streamlit/config.toml`; check file size before processing |
| Path traversal in filename | Tampering | Never use original filename as file path; use content hash as filename |
| Prompt injection in document content | Elevation of Privilege | System prompt treats retrieved context as data, not instructions (Phase 4 concern, but relevant to ingestion metadata) |

## Project Constraints (from copilot-instructions.md)

- **Layout:** `pipelines/` for orchestration, `core/` for capabilities, `ui/` for Streamlit partials
- **Content-hash dedupe** for idempotent re-uploads (locked decision)
- **`@st.cache_resource`** for heavy singletons: LLM client, EasyOCR Reader, Chroma client
- **`doc_id` metadata** in ChromaDB for per-doc filtering
- **Runtime state directories:** `data/uploads/`, `data/cache/`, `data/chroma/` (gitignored)
- **Sample documents:** `data/samples/` (committed)
- **Structure-aware chunker:** never splits across tables/lists/headings; tables as atomic chunks with `chunk_type` metadata
- **Per-page `<50 chars` heuristic** triggers OCR fallback
- **Batch embeddings** (32–64 chunks/call) with exponential backoff + jitter on 429/504

## Sources

### Primary (HIGH confidence)

- Streamlit `st.file_uploader` docs — file upload widget API, `type` parameter, `getvalue()` for bytes [CITED: docs.streamlit.io/develop/api-reference/widgets/st.file_uploader]
- Streamlit `st.cache_resource` docs — singleton caching, global scope, mutable objects [CITED: docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource]
- Streamlit `st.session_state` docs — cross-rerun state persistence, widget association [CITED: docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state]
- Streamlit `st.status` docs — multi-stage progress container [CITED: docs.streamlit.io/develop/api-reference/status/st.status]
- Python `hashlib` stdlib — SHA-256 content hashing [VERIFIED: Python 3.10+ stdlib]
- ChromaDB getting started docs — `get_or_create_collection`, `collection.get(where=...)`, `collection.delete(where=...)` [CITED: docs.trychroma.com/docs/overview/getting-started]
- Existing codebase: `core/extractor.py`, `core/chunker.py`, `core/vectorstore.py`, `core/embedder.py`, `core/ocr.py` — Phase 1–2 APIs [VERIFIED: codebase read]

### Secondary (MEDIUM confidence)

- `.planning/research/PITFALLS.md` — Pitfalls #1 (EasyOCR rerun), #7 (ChromaDB config), #11 (Streamlit state) [VERIFIED: project artifact]
- `.planning/research/SUMMARY.md` — Architecture patterns, build order rationale [VERIFIED: project artifact]

### Tertiary (LOW confidence)

- None — all claims verified against official docs or codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib or existing deps, no new packages
- Architecture: HIGH — standard Streamlit + pipeline composition, well-documented patterns
- Pitfalls: HIGH — each pitfall verified against Streamlit docs or observed in existing codebase structure

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable — no fast-moving dependencies)

# DocBot Functional Overview

## 1. What DocBot Is

DocBot is a local Streamlit application for document intelligence. A user can upload PDFs (or load bundled samples), ask natural-language questions, generate summaries, and extract a knowledge graph.

The app runs locally for UI and document processing, while model inference is handled by NVIDIA NIM through an OpenAI-compatible API.

## 2. Core Capabilities

DocBot provides four primary user-facing capabilities:

1. Chat Q&A with source grounding.
2. Document summarization.
3. Knowledge graph extraction and visualization.
4. Side-by-side model comparison (large vs route model).

Each capability works on top of a shared ingestion and retrieval foundation.

## 3. High-Level Architecture

The project is organized by responsibility:

- `app.py`: Streamlit composition root; wires tabs and shared services.
- `ui/`: Feature views (`chat`, `summary_view`, `graph_view`, `comparison`, `upload`, `sidebar`).
- `pipelines/`: Orchestration logic for ingest, query, summarize, graph extraction, and comparison.
- `core/`: Foundational capabilities (config, LLM client, extractor/OCR, chunker, embedder, vector store, retriever).
- `routers/model_router.py`: Pure routing logic that picks model by task and document complexity signals.
- `prompts/`: External prompt templates for QA, summarization, and graph extraction/correction.

## 4. Tech Stack and Key Components

### Runtime and UI

- Python 3.10-3.12
- Streamlit for local web UI

### LLM and Embeddings

- `openai` Python SDK against NVIDIA NIM endpoint (`https://integrate.api.nvidia.com/v1`)
- Default chat model: `meta/llama-3.1-70b-instruct`
- Default route model: `meta/llama-3.1-8b-instruct`
- Default embedding model: `nvidia/nv-embedqa-e5-v5`

### Document Processing

- PyMuPDF for PDF text and table extraction
- EasyOCR (English, CPU) for scanned/low-text pages
- tiktoken-based chunk sizing and summarization token budget decisions

### Retrieval and Storage

- ChromaDB `PersistentClient` for vector storage (`data/chroma`)
- Single `documents` collection with metadata (`doc_id`, filename, page number, chunk type, chunk index)
- Embedding model and dimension stored in collection metadata and validated on startup

### Validation and Parsing

- Pydantic models for structured graph extraction outputs
- RapidFuzz for entity deduplication in graph mode

## 5. End-to-End Data Flow

1. User uploads a PDF (or loads from `data/samples`).
2. File bytes are hashed to create a deterministic `doc_id` (SHA-256).
3. The PDF is extracted:
   - Text blocks and tables are parsed.
   - Pages with very little text (`<50` chars) are OCR candidates.
4. Extracted content is chunked with structure-aware rules.
5. Chunks are embedded in batches and written to ChromaDB.
6. Feature tabs (Chat, Summary, Graph, Compare) run read/query pipelines against stored chunks.

## 6. How Ingestion Works

Ingestion is designed for repeatability and persistence:

- **Deterministic identity**: `doc_id` is derived from file content hash.
- **Deduplication**: Existing `doc_id` in vector store is treated as already indexed.
- **OCR fallback**: If a page has too little extractable text, OCR can replace that page text.
- **Table handling**: Tables are extracted separately and preserved as atomic chunks.
- **Persistence**: Indexed docs remain available across app reruns and restarts through ChromaDB.

The sidebar can reconstruct document state by scanning vector metadata, so indexed documents reappear without re-upload.

## 7. How Chat Q&A Works

Chat uses retrieval-augmented generation (RAG):

1. User question is embedded as a query vector.
2. Top-k chunks are retrieved from ChromaDB (optionally document-scoped).
3. Retrieved chunks are reordered so the best chunk appears first and last (anti "lost in the middle").
4. A QA prompt is assembled with chunk IDs and page context.
5. The selected model generates an answer with citations.
6. Citations are validated against retrieved chunk IDs:
   - Valid citations are shown as source expanders.
   - Non-retrieved citations are flagged as possibly hallucinated.

For cleaner UX, raw chunk IDs in answer text are remapped to `[1]`, `[2]`, etc., while preserving source traceability.

## 8. How Summarization Works

Summarization operates at document level:

1. All chunks for a selected document are loaded.
2. Combined token count is estimated.
3. The pipeline chooses one of two methods:
   - **Direct**: entire text summarized in one call when within token budget.
   - **Map-reduce**: chunk-level summaries are generated first, then reduced into a final summary.

The UI reports method used, chunk count, model, latency, and token usage.

## 9. How Graph Extraction Works

Graph extraction turns document content into structured knowledge:

1. All document chunks are concatenated as extraction context.
2. Model is called in JSON mode (`response_format=json_object`).
3. Output is validated against Pydantic schema (entities, relationships, process steps, decision points, business rules).
4. On parse/validation failure, a one-shot self-correction prompt is executed.
5. Entity names are deduplicated using fuzzy matching (RapidFuzz), and relationships are rewritten to canonical names.
6. Results are shown as:
   - Tabular data views
   - Interactive node-edge graph (`streamlit-agraph`)
   - Mermaid process flow for process steps

## 10. How Model Selection Works

DocBot supports three routing modes from the sidebar:

- **auto**: router chooses model by task type and complexity signals.
- **small (route)**: forces route model.
- **large (direct)**: forces large model.

Auto-routing decisions:

- Graph extraction routes to large model for JSON reliability.
- Larger document signals (`doc_length > 10,000` chars or `chunk_count > 15`) route to large model.
- Otherwise, route model is used for faster responses.

Route reason text is surfaced in the UI for explainability.

## 11. How Model Comparison Works

Comparison mode runs the same question through both models in parallel:

- Inputs are held constant (same question, retrieval context, and generation settings).
- Only model identity differs.
- Output is presented side-by-side with latency and token metrics.

This is intentionally a concept/demo comparison panel, not a benchmarking framework.

## 12. Reliability and Operational Behavior

Important operational characteristics:

- Heavy resources are cached with `@st.cache_resource` (NIM client, OCR reader, vector store).
- NIM client includes retry with exponential backoff + jitter on 429/504.
- Embeddings are batched (default 32 items/request).
- Vector collection validates embedding model/dimension compatibility at startup.
- API error classes (rate limit, auth, timeout, connection/status) are handled and surfaced clearly in UI.

## 13. What a New Reader Should Remember

At a functional level, DocBot is a local RAG document workbench with four coordinated user experiences:

- Ask grounded questions with citations.
- Produce document summaries with adaptive summarization strategy.
- Convert unstructured text into structured graph knowledge.
- Compare large vs smaller routed model behavior side-by-side.

The shared backbone is: extraction -> structure-aware chunking -> embeddings -> persistent vector retrieval -> task-specific LLM orchestration.
# Phase 5: Summarization + Graph Extraction - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers two new capabilities for any indexed document: (1) a concise, business-readable summary using a map-reduce pattern for long documents, and (2) structured entity/relationship/process-step extraction as validated JSON, rendered in both table and interactive graph views. The UI gets two new view partials (summary_view, graph_view) integrated into the main app.

</domain>

<decisions>
## Implementation Decisions

### Summary Presentation
- **D-01:** Summary output is flowing prose with key points bolded — the most business-readable format. The reduce prompt instructs the LLM to produce 5-10 sentences organized by importance.
- **D-02:** Use a token-budget threshold (6000 tokens) to decide between direct single-call summarization and map-reduce. Below threshold → single call; above → map each chunk then reduce.

### Graph Extraction Strategy
- **D-03:** Use a single mega-prompt that extracts all five categories (entities, relationships, process_steps, decision_points, business_rules) in one LLM call. This minimizes API calls and preserves cross-references between categories.
- **D-04:** Entity types are fixed at 7: PERSON, ORG, PROCESS, SYSTEM, CONCEPT, DOCUMENT, ROLE. Listed explicitly in the extraction prompt.
- **D-05:** Extraction operates on all chunks for a document, concatenated. If the concatenated text exceeds the LLM's practical input limit, fall back to a map-reduce extraction pattern (extract per chunk group, then merge+dedup).

### Validation & Dedup
- **D-06:** Pydantic v2 `GraphExtraction` model validates the JSON output. On parse failure, a one-shot self-correction retry sends both the malformed output AND the human-readable error message back to the LLM at temperature=0.1.
- **D-07:** Entity dedup uses `rapidfuzz.fuzz.token_sort_ratio` at threshold 85, comparing within same entity type only. The longer name is kept as canonical. After dedup, relationship source/target and ProcessStep actors are updated to use canonical names.

### UI Layout
- **D-08:** Tab-based layout — "Summary" and "Graph" tabs alongside the existing Chat view. Each tab has a document selector and an action button ("Summarize" / "Extract").
- **D-09:** Graph view uses `st.tabs()` within itself: "Table View" (st.dataframe for each category) and "Graph View" (streamlit-agraph interactive node-edge). Process steps optionally rendered as mermaid flowchart via native st.markdown.
- **D-10:** Both summarization and extraction show progress via `st.status()` — consistent with the existing upload UI pattern.

### Pipeline Design
- **D-11:** Two new pipeline modules: `pipelines/summarize.py` (SummaryResult dataclass, run_summarize function) and `pipelines/graph.py` (GraphExtraction Pydantic model, GraphResult dataclass, run_graph_extraction function). Follow the existing `run_query` pattern from `pipelines/query.py`.
- **D-12:** VectorStore needs a new `get_all_by_doc(doc_id)` method using ChromaDB's `collection.get(where={"doc_id": doc_id})` — retrieves all chunks without requiring a query embedding.

### LLM Parameters
- **D-13:** Graph extraction uses `temperature=0.2` and `max_tokens=4096` to prevent truncation of complex JSON output. Self-correction retry uses `temperature=0.1`.
- **D-14:** Summarization uses `temperature=0.3` (matching existing QA pipeline) and `max_tokens=1024`.

### Agent's Discretion
- Prompt template wording — exact phrasing of map/reduce/extract/correct prompts can be tuned during implementation
- streamlit-agraph Config parameters (width, height, physics settings) — tune for best visual result
- Whether to add a mermaid process-flow tab — implement if process_steps are non-empty, skip if agraph covers it adequately

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Research
- `.planning/phases/05-summarization-graph-extraction/05-RESEARCH.md` — Full research on JSON-mode prompting, entity dedup, Streamlit rendering, Pydantic schema design

### Project Context
- `.planning/REQUIREMENTS.md` — SUM-01, SUM-02, GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04 requirement definitions
- `.planning/ROADMAP.md` — Phase 5 success criteria and dependency on Phase 4
- `.planning/research/SUMMARY.md` — Research flags and pitfalls for graph extraction

### Existing Codebase Patterns
- `pipelines/query.py` — QueryResult dataclass pattern, pipeline structure to follow
- `pipelines/ingest.py` — IngestResult dataclass pattern
- `core/vectorstore.py` — VectorStore class (needs get_all_by_doc addition)
- `core/llm_client.py` — NIMClient with json_mode=True, retry, batched embeddings
- `core/retriever.py` — RetrievedChunk dataclass pattern
- `prompts/qa.txt` — Existing prompt template format (str.format placeholders)
- `app.py` — Streamlit composition root to extend with new view partials
- `.github/copilot-instructions.md` — Project hard rules and pitfall patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `NIMClient.chat(json_mode=True)` — already supports `response_format={"type":"json_object"}`, retry on 429/504
- `VectorStore.query()` — similarity search with doc_id filtering; need to add `get_all_by_doc()` for full-doc retrieval
- `VectorStore.delete_by_doc()` — uses `collection.delete(where=...)` pattern; `get_all_by_doc` follows same pattern with `collection.get(where=...)`
- `@st.cache_resource` singletons in `ui/upload.py` — `get_vectorstore()`, `get_nim_client()`, `get_ocr_reader()`
- `st.session_state` pattern from chat UI — document list tracking

### Established Patterns
- Plain dataclasses for pipeline results (IngestResult, QueryResult, RetrievedChunk)
- Prompt templates as `.txt` files in `prompts/` using `str.format()` placeholders
- Pipeline modules expose a `run_*()` function as the public API
- UI partials as `render_*()` functions in `ui/` called from `app.py`
- `st.status()` for progress indication (used in upload flow)
- Error handling via `st.error()` for NVIDIA API exceptions

### Integration Points
- `app.py` — add imports for `render_summary_view` and `render_graph_view`; add to page layout
- `core/vectorstore.py` — add `get_all_by_doc()` method
- `pyproject.toml` — add `rapidfuzz>=3.14` and `streamlit-agraph>=0.0.45` dependencies

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches guided by research findings.

</specifics>

<deferred>
## Deferred Ideas

- Streaming summarization progress (show partial summary as it generates) — Phase 7 polish
- Graph export to JSON/GraphML file — potential v2 feature
- Hierarchical map-reduce extraction for very long documents (100+ pages) — implement simpler all-chunks path first, revisit if needed
- Graph comparison across documents — v2 feature

</deferred>

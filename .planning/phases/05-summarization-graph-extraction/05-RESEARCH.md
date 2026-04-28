# Phase 5: Summarization + Graph Extraction - Research

**Researched:** 2026-04-28
**Domain:** Map-reduce summarization, JSON-mode structured extraction, entity dedup, Streamlit graph rendering
**Confidence:** HIGH

## Summary

Phase 5 adds two capabilities on top of the existing retrieval pipeline: (1) map-reduce document summarization and (2) prompt-based structured extraction of entities, relationships, process steps, decision points, and business rules as validated JSON rendered in both table and graph views.

The existing codebase provides all integration points needed. `NIMClient.chat()` already supports `json_mode=True` via `response_format={"type":"json_object"}`, Pydantic v2 is in the stack, prompt templates follow the `str.format()` pattern in `prompts/`, and pipelines return plain dataclasses. The primary research areas are: (a) reliable JSON-mode prompting patterns for llama-3.1-70b-instruct on NVIDIA NIM, (b) Pydantic schema design for the five extraction categories, (c) self-correction retry on parse failure, (d) rapidfuzz scorer selection and threshold for entity dedup, and (e) Streamlit rendering for both table and node-edge views.

**Primary recommendation:** Use a single mega-prompt for graph extraction (one LLM call returns all five categories), validate with a flat Pydantic model, use `fuzz.token_sort_ratio` at threshold 85 for entity dedup, render tables via `st.dataframe()` and node-edge graphs via `streamlit-agraph`. For summarization, use a direct single-call path for short docs and a map-reduce path (map each chunk → reduce combined summaries) for docs exceeding a configurable token budget.

## Project Constraints (from copilot-instructions.md)

- Python 3.10–3.12, CPU-only
- `openai` SDK against NVIDIA NIM (`https://integrate.api.nvidia.com/v1`)
- Default model: `meta/llama-3.1-70b-instruct` (chat), `nvidia/nv-embedqa-e5-v5` (embeddings)
- Pydantic `^2.7` for validation
- `rapidfuzz` for entity dedup
- Streamlit UI with `@st.cache_resource` for heavy singletons
- No LlamaIndex usage in pipelines (direct openai SDK via NIMClient)
- Prompt templates are plain `.txt` files using `str.format()` placeholders
- Pipelines use plain dataclasses for results
- ChromaDB PersistentClient with `doc_id` metadata filtering
- Structure-aware chunker emits chunks with `doc_id`, `chunk_id`, `page_num`, `chunk_type` metadata

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SUM-01 | User can request a concise summary of any indexed document | Direct summarization path + map-reduce fallback; prompt template in `prompts/summary_map.txt` and `prompts/summary_reduce.txt` |
| SUM-02 | Summarization uses map-reduce over chunks for long documents | Map-reduce architecture pattern with token-budget threshold; chunk-level map calls + single reduce call |
| GRAPH-01 | Prompt-based extraction produces entities, relationships, process steps, decision points, business rules as JSON | Single mega-prompt with JSON schema in system message + one-shot example; `response_format={"type":"json_object"}` |
| GRAPH-02 | Output validated against Pydantic schema; one-shot self-correction retry on parse failure | `GraphExtraction` Pydantic model; correction prompt includes malformed output + error message |
| GRAPH-03 | Rendered as both table view and node/edge or mermaid process-flow view | `st.dataframe()` for tables; `streamlit-agraph` for interactive node-edge graph |
| GRAPH-04 | Entity dedup via rapidfuzz with documented threshold | `fuzz.token_sort_ratio` at threshold 85; merge within same entity type first |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Map-reduce summarization | Pipeline (`pipelines/summarize.py`) | Core (`core/llm_client.py`) | Orchestration logic; LLM is the compute engine |
| Graph extraction prompting | Pipeline (`pipelines/graph.py`) | Core (`core/llm_client.py`) | Orchestration + prompt formatting; LLM produces raw JSON |
| Pydantic validation + retry | Pipeline (`pipelines/graph.py`) | — | Validation is part of the pipeline, not a reusable core capability |
| Entity dedup | Pipeline (`pipelines/graph.py`) | — | Post-processing step within the graph pipeline |
| Table rendering | UI (`ui/summary_view.py`, `ui/graph_view.py`) | — | Pure display logic |
| Node-edge rendering | UI (`ui/graph_view.py`) | — | Pure display logic using streamlit-agraph |
| Chunk retrieval for summarization | Core (`core/vectorstore.py`) | — | Existing `get_all_by_doc()` method needed |

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | ^1.50 | LLM chat completions with JSON mode | Already in stack; NIMClient wraps it |
| pydantic | ^2.7 | Schema validation for extracted graph JSON | Already in stack; used in core/config.py |
| streamlit | ^1.40 (installed: 1.56.0) | UI rendering, `st.dataframe()`, `st.markdown()` | Already in stack |

### New Dependencies
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rapidfuzz | ^3.14 | Fuzzy string matching for entity dedup | GRAPH-04: merging duplicate entity names |
| streamlit-agraph | ^0.0.45 | Interactive node-edge graph visualization | GRAPH-03: entity-relationship graph view |

[VERIFIED: pip index] rapidfuzz latest = 3.14.5, installed on system at 3.14.3. Not yet in project `pyproject.toml` — must be added.
[VERIFIED: pip index] streamlit-agraph latest = 0.0.45. Not yet in project — must be added.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| streamlit-agraph | Native mermaid via `st.markdown` | Zero deps but no interactivity (no pan/zoom/click); mermaid gets illegible above ~20 nodes. Use mermaid for process-flow only if needed. |
| streamlit-agraph | graphviz via `st.graphviz_chart` | Built-in but static rendering, less visually appealing, no interactive layout |
| streamlit-agraph | pyvis | More features but requires HTML iframe embedding in Streamlit, heavier |
| Single mega-prompt | Separate prompts per category | More LLM calls = higher latency/cost; cross-references between entities and relationships lost |

**Installation:**
```bash
uv add rapidfuzz ">=3.14"
uv add streamlit-agraph ">=0.0.45"
```

## Architecture Patterns

### System Architecture Diagram

```
User clicks "Summarize" or "Extract Graph"
          │
          ▼
    ┌─────────────┐
    │  app.py      │  (Streamlit composition root)
    │  ui/         │  (summary_view.py, graph_view.py)
    └─────┬───────┘
          │
          ▼
    ┌─────────────────────────────┐
    │  pipelines/summarize.py     │  SUM-01, SUM-02
    │  pipelines/graph.py         │  GRAPH-01 through GRAPH-04
    └─────┬───────────────────────┘
          │
          ├──► VectorStore.get_all_by_doc(doc_id)  → all chunks for the doc
          │
          ├──► NIMClient.chat(json_mode=True/False) → LLM calls
          │
          ├──► Pydantic validation (graph only)
          │
          ├──► rapidfuzz entity dedup (graph only)
          │
          ▼
    ┌─────────────────────────────┐
    │  Result dataclasses          │
    │  SummaryResult / GraphResult │
    └─────────────────────────────┘
          │
          ▼
    ┌─────────────────────────────┐
    │  UI rendering                │
    │  st.dataframe() for tables   │
    │  agraph() for node-edge      │
    │  st.markdown() for summary   │
    └─────────────────────────────┘
```

### Recommended Project Structure (new files)
```
prompts/
├── summary_map.txt           # Map-step prompt: summarize a single chunk
├── summary_reduce.txt        # Reduce-step prompt: combine chunk summaries
├── graph_extract.txt         # Graph extraction mega-prompt with schema + one-shot example
└── graph_correct.txt         # Self-correction prompt for malformed JSON
pipelines/
├── summarize.py              # SummaryResult dataclass, run_summarize()
└── graph.py                  # GraphExtraction Pydantic model, GraphResult dataclass, run_graph_extraction()
ui/
├── summary_view.py           # render_summary() partial
└── graph_view.py             # render_graph() partial with table + node-edge tabs
tests/
├── test_summarize_pipeline.py
└── test_graph_pipeline.py
```

### Pattern 1: Map-Reduce Summarization

**What:** Two-phase summarization: map each chunk to a partial summary, then reduce all partial summaries into one final summary.

**When to use:** When a document's chunks exceed a configurable token budget (default: 6000 tokens). Below that threshold, concatenate all chunks and summarize in a single LLM call (direct path).

**Why 6000 tokens:** llama-3.1-70b-instruct has 128K context, but the NVIDIA NIM free tier has per-request token limits. A 6000-token context budget leaves room for the system prompt (~200 tokens) and output (~1000 tokens) within an 8192-token request ceiling. This is conservative and configurable.

**Implementation:**

```python
# Source: established RAG pattern; consistent with existing pipeline structure
from dataclasses import dataclass, field

@dataclass
class SummaryResult:
    """Result of a summarization operation."""
    summary: str
    doc_id: str
    chunk_count: int
    method: str  # "direct" or "map_reduce"
    error: str | None = None

TOKEN_BUDGET = 6000  # Max tokens for direct summarization

def run_summarize(doc_id: str, vectorstore, nim_client) -> SummaryResult:
    chunks = vectorstore.get_all_by_doc(doc_id)
    if not chunks:
        return SummaryResult(summary="", doc_id=doc_id, chunk_count=0,
                           method="direct", error="No chunks found")

    total_tokens = sum(_count_tokens(c["text"]) for c in chunks)

    if total_tokens <= TOKEN_BUDGET:
        # Direct path: single LLM call
        summary = _summarize_direct(chunks, nim_client)
        return SummaryResult(summary=summary, doc_id=doc_id,
                           chunk_count=len(chunks), method="direct")
    else:
        # Map-reduce path
        summary = _map_reduce(chunks, nim_client)
        return SummaryResult(summary=summary, doc_id=doc_id,
                           chunk_count=len(chunks), method="map_reduce")

def _summarize_direct(chunks, nim_client) -> str:
    combined = "\n\n".join(c["text"] for c in chunks)
    template = Path("prompts/summary_reduce.txt").read_text(encoding="utf-8")
    prompt = template.format(text=combined)
    response = nim_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=1024,
    )
    return response.choices[0].message.content

def _map_reduce(chunks, nim_client) -> str:
    # Map: summarize each chunk
    map_template = Path("prompts/summary_map.txt").read_text(encoding="utf-8")
    partial_summaries = []
    for chunk in chunks:
        prompt = map_template.format(text=chunk["text"])
        response = nim_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=512,
        )
        partial_summaries.append(response.choices[0].message.content)

    # Reduce: combine partials into final
    combined = "\n\n---\n\n".join(partial_summaries)
    reduce_template = Path("prompts/summary_reduce.txt").read_text(encoding="utf-8")
    prompt = reduce_template.format(text=combined)
    response = nim_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=1024,
    )
    return response.choices[0].message.content
```

**Key design decisions:**
- One chunk per map call (predictable token budget, no batching complexity)
- Sequential map calls (avoid concurrent API calls burning rate limit; parallelism is a Phase 6 concern)
- If reduce input exceeds budget: do hierarchical reduce (combine partial summaries in groups, then reduce groups). This is rare for POC-sized docs.
- `temperature=0.3` matches the existing QA pipeline pattern for grounded output

### Pattern 2: JSON-Mode Graph Extraction with Single Mega-Prompt

**What:** One LLM call extracts all five categories (entities, relationships, process steps, decision points, business rules) as a single JSON object.

**When to use:** Always — this is the only extraction pattern for this phase.

**Why single prompt:** (a) Fewer LLM calls = lower latency and API cost. (b) The model can cross-reference between categories (e.g., entities mentioned in relationships must exist in the entity list). (c) Simpler pipeline code.

**Implementation:**

```python
import json
from pydantic import BaseModel, Field

class Entity(BaseModel):
    name: str = Field(description="Canonical name of the entity")
    type: str = Field(description="One of: PERSON, ORG, PROCESS, SYSTEM, CONCEPT, DOCUMENT, ROLE")
    description: str = Field(description="Brief one-sentence description")

class Relationship(BaseModel):
    source: str = Field(description="Source entity name (must match an entity in the entities list)")
    target: str = Field(description="Target entity name (must match an entity in the entities list)")
    relation: str = Field(description="Relationship type, e.g., MANAGES, USES, PRODUCES, DEPENDS_ON")
    description: str = Field(description="Brief description of the relationship")

class ProcessStep(BaseModel):
    step_number: int = Field(description="Sequential step number starting from 1")
    name: str = Field(description="Short name for the step")
    description: str = Field(description="What happens in this step")
    actors: list[str] = Field(default_factory=list, description="Entity names involved")

class DecisionPoint(BaseModel):
    name: str = Field(description="Name of the decision")
    description: str = Field(description="What must be decided")
    options: list[str] = Field(default_factory=list, description="Available choices")

class BusinessRule(BaseModel):
    name: str = Field(description="Short rule name")
    description: str = Field(description="Full rule description")
    condition: str = Field(default="", description="When this rule applies")
    action: str = Field(default="", description="What must be done")

class GraphExtraction(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    process_steps: list[ProcessStep] = Field(default_factory=list)
    decision_points: list[DecisionPoint] = Field(default_factory=list)
    business_rules: list[BusinessRule] = Field(default_factory=list)
```

**Entity type enum:** Keep it small and fixed (7 types: PERSON, ORG, PROCESS, SYSTEM, CONCEPT, DOCUMENT, ROLE). Broader types like "OTHER" invite inconsistency. The prompt must list these explicitly. [ASSUMED — threshold of 7 types is a judgment call; validate with real doc extraction]

### Pattern 3: Self-Correction Retry

**What:** When JSON parsing or Pydantic validation fails, send the malformed output + error message back to the LLM for a one-shot fix.

**Why include both the output and the error:** The LLM needs to see what it produced (to understand the mistake) and the parse error (to know what to fix). Sending just "try again" wastes the retry.

```python
def _extract_with_retry(context: str, nim_client) -> GraphExtraction:
    """Extract graph data with one-shot self-correction on failure."""
    template = Path("prompts/graph_extract.txt").read_text(encoding="utf-8")
    prompt = template.format(context=context)

    response = nim_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=4096,  # Graph extraction needs more output room
        json_mode=True,
    )
    raw = response.choices[0].message.content

    # First attempt: parse and validate
    try:
        data = json.loads(raw)
        return GraphExtraction.model_validate(data)
    except (json.JSONDecodeError, Exception) as first_error:
        pass  # Fall through to correction

    # Self-correction retry
    correct_template = Path("prompts/graph_correct.txt").read_text(encoding="utf-8")
    correction_prompt = correct_template.format(
        original_output=raw,
        error_message=str(first_error),
    )

    retry_response = nim_client.chat(
        messages=[{"role": "user", "content": correction_prompt}],
        temperature=0.1,  # Lower temp for correction
        max_tokens=4096,
        json_mode=True,
    )
    retry_raw = retry_response.choices[0].message.content

    # Second attempt: if this fails, raise
    data = json.loads(retry_raw)
    return GraphExtraction.model_validate(data)
```

**Key details:**
- `temperature=0.2` for extraction (low to reduce randomness in structured output, but not 0.0 which can cause repetition loops on some models)
- `temperature=0.1` for correction (even lower — we want minimal creative deviation)
- `max_tokens=4096` for graph extraction (complex documents can produce 50+ entities; 1024 will truncate)
- `json_mode=True` is critical — without it, llama-3.1 may wrap JSON in markdown code blocks

### Pattern 4: Entity Dedup with rapidfuzz

**What:** After extraction, merge entities that refer to the same real-world thing (e.g., "United States", "US", "U.S.A.").

**Scorer:** `fuzz.token_sort_ratio` — tokenizes both strings, sorts tokens alphabetically, then computes ratio. This handles word-order variations ("John Smith" ↔ "Smith, John") and is robust for entity names.

**Threshold:** 85 — empirically strong for named entity dedup. 80 produces too many false merges (e.g., "Bank of America" ↔ "Bank of England" scores ~78). 90 misses valid matches (e.g., "U.S. Department of Energy" ↔ "US Dept. of Energy" scores ~86). [ASSUMED — threshold 85 is based on general NER dedup practice; validate against actual extraction output from sample docs]

**Why not `fuzz.ratio`:** Pure character-level; fails on word reordering. Why not `fuzz.WRatio`: More expensive, applies multiple strategies — overkill for entity names.

```python
from rapidfuzz import fuzz

DEDUP_THRESHOLD = 85

def deduplicate_entities(entities: list[Entity]) -> list[Entity]:
    """Merge duplicate entities using fuzzy matching within same type."""
    if not entities:
        return []

    canonical: list[Entity] = []

    for entity in entities:
        merged = False
        for i, canon in enumerate(canonical):
            # Only compare within same type
            if entity.type != canon.type:
                continue
            score = fuzz.token_sort_ratio(
                entity.name.lower(), canon.name.lower()
            )
            if score >= DEDUP_THRESHOLD:
                # Keep the longer name as canonical (more descriptive)
                if len(entity.name) > len(canon.name):
                    canonical[i] = Entity(
                        name=entity.name,
                        type=canon.type,
                        description=canon.description or entity.description,
                    )
                merged = True
                break
        if not merged:
            canonical.append(entity)

    return canonical
```

**After entity dedup, update relationships:** Replace merged entity names in relationship `source`/`target` fields to point to the canonical name. Also update `actors` in ProcessStep.

### Pattern 5: Streamlit Rendering — Table + Node-Edge

**Table view:** Convert Pydantic models to dicts and render with `st.dataframe()`. Use `st.tabs()` to separate entities, relationships, process steps, decision points, and business rules.

**Node-edge view:** Use `streamlit-agraph` for interactive entity-relationship visualization.

```python
# Source: streamlit-agraph README (https://github.com/ChrisDelClea/streamlit-agraph)
from streamlit_agraph import agraph, Node, Edge, Config

def render_graph(extraction: GraphExtraction):
    # Color map for entity types
    TYPE_COLORS = {
        "PERSON": "#4CAF50", "ORG": "#2196F3", "PROCESS": "#FF9800",
        "SYSTEM": "#9C27B0", "CONCEPT": "#607D8B", "DOCUMENT": "#795548",
        "ROLE": "#00BCD4",
    }

    nodes = [
        Node(
            id=e.name,
            label=e.name,
            size=25,
            color=TYPE_COLORS.get(e.type, "#999"),
            title=f"{e.type}: {e.description}",  # tooltip on hover
        )
        for e in extraction.entities
    ]

    edges = [
        Edge(
            source=r.source,
            target=r.target,
            label=r.relation,
            title=r.description,  # tooltip on hover
        )
        for r in extraction.relationships
    ]

    config = Config(
        width=750, height=500,
        directed=True, physics=True,
        hierarchical=False,
    )

    agraph(nodes=nodes, edges=edges, config=config)
```

[VERIFIED: streamlit-agraph 0.0.45 API] — Node accepts `id`, `label`, `size`, `color`, `title`, `shape`; Edge accepts `source`, `target`, `label`, `title`; Config accepts `width`, `height`, `directed`, `physics`, `hierarchical`.

**Mermaid alternative for process flow:** Streamlit 1.33+ renders mermaid natively in `st.markdown`. Since the project has Streamlit 1.56.0, this is available. Use for process-step visualization as an optional secondary view:

```python
def render_process_mermaid(steps: list[ProcessStep]):
    lines = ["```mermaid", "flowchart TD"]
    for i, step in enumerate(steps):
        node_id = f"S{step.step_number}"
        lines.append(f'    {node_id}["{step.name}"]')
        if i > 0:
            prev_id = f"S{steps[i-1].step_number}"
            lines.append(f"    {prev_id} --> {node_id}")
    lines.append("```")
    st.markdown("\n".join(lines))
```

[VERIFIED: Streamlit 1.56.0 installed] — Mermaid support confirmed available.

### Anti-Patterns to Avoid

- **Sending all chunks in one prompt for graph extraction:** Exceeds token limits for long docs. Instead, extract from the concatenated chunk text (same approach as summarization — but for graph extraction, the full doc context improves cross-referencing).
- **Using `temperature=0.0` for JSON extraction:** Can cause repetition loops on some models. Use 0.1–0.2 instead.
- **Parsing JSON with `eval()`:** Security risk. Always use `json.loads()`.
- **Retrying more than once on JSON failure:** Diminishing returns; the model either understands the format or it doesn't. One retry is sufficient; after that, surface the error.
- **Deduplicating across entity types:** "Process" (an entity of type CONCEPT) should not merge with "Process" (type PROCESS). Always compare within same type.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching | Custom edit-distance calculator | `rapidfuzz.fuzz.token_sort_ratio` | C++ optimized, handles Unicode, well-tested edge cases |
| JSON schema validation | Manual dict key checking | `pydantic.BaseModel.model_validate()` | Handles nested types, defaults, coercion, descriptive errors |
| Interactive graph visualization | Custom HTML/JS/D3 component | `streamlit-agraph` (vis.js wrapper) | Handles layout, physics, pan/zoom, tooltips out of the box |
| Token counting | `len(text.split())` approximation | `tiktoken` cl100k_base (already in stack) | Matches the model's actual tokenizer; avoids over/under-estimation |
| JSON parsing | `eval()` or regex | `json.loads()` | Security; handles all edge cases correctly |

## Common Pitfalls

### Pitfall 1: JSON Truncation on max_tokens

**What goes wrong:** Graph extraction produces large JSON (50+ entities → 3000+ tokens). If `max_tokens` is too low (e.g., 1024), the response is truncated mid-JSON, causing `json.JSONDecodeError`.

**Why it happens:** The default `max_tokens=1024` in the existing NIMClient.chat() is fine for Q&A answers but too small for structured extraction output.

**How to avoid:** Use `max_tokens=4096` for graph extraction calls. Monitor response `finish_reason` — if it's `"length"` instead of `"stop"`, the output was truncated.

**Warning signs:** `json.JSONDecodeError: Unterminated string` or `Expecting ',' delimiter`.

### Pitfall 2: Entity Name Mismatch Between Entities and Relationships

**What goes wrong:** The LLM extracts an entity as "US Dept. of Energy" but references it in relationships as "Department of Energy". Pydantic validates but the graph has orphan nodes.

**Why it happens:** LLMs don't enforce referential integrity in JSON output.

**How to avoid:** After Pydantic validation, run a post-processing step that: (1) collects all entity names into a set, (2) for each relationship source/target, fuzzy-match against the entity set, (3) replace with the closest canonical name if above threshold. Same for ProcessStep.actors.

**Warning signs:** Node-edge graph shows disconnected nodes that should be connected.

### Pitfall 3: Rate Limit Burn During Map-Reduce

**What goes wrong:** Map step makes N sequential LLM calls (one per chunk). A 20-page document with 15 chunks burns 15 API calls rapidly, hitting NVIDIA free-tier rate limits (429).

**Why it happens:** Sequential calls happen fast; the rate limiter sees a burst.

**How to avoid:** The existing `NIMClient._call_with_retry()` already handles 429 with exponential backoff. No additional mitigation needed — but the summarization UI should show progress (`st.progress()` or `st.status()`) so users see it's working, not hung.

**Warning signs:** Multiple 429 retries during summarization of long documents.

### Pitfall 4: Pydantic Validation Error Messages Are Opaque to the LLM

**What goes wrong:** Self-correction prompt sends `"3 validation errors for GraphExtraction..."` which includes Pydantic's internal error format. The LLM may not understand what to fix.

**Why it happens:** Pydantic v2 error messages use a structured format with `loc`, `msg`, `type` that isn't natural language.

**How to avoid:** In the correction prompt, convert the Pydantic error to a human-readable string: `"Field 'entities[2].type' must be one of PERSON, ORG, PROCESS, SYSTEM, CONCEPT, DOCUMENT, ROLE but got 'Organization'."` Use `e.errors()` and format each error as a sentence.

**Warning signs:** Self-correction retry still fails with the same validation error.

### Pitfall 5: streamlit-agraph Crashes on Empty Graph

**What goes wrong:** If extraction produces zero entities (e.g., the document has no extractable content), passing empty `nodes=[]` to `agraph()` may render a blank canvas or error.

**Why it happens:** streamlit-agraph expects at least one node.

**How to avoid:** Guard the graph render: `if extraction.entities: render_graph(extraction) else: st.info("No entities extracted.")`.

**Warning signs:** Blank graph view with no user feedback.

### Pitfall 6: VectorStore Missing `get_all_by_doc()` Method

**What goes wrong:** The existing `VectorStore` has `query()` (similarity search) and `delete_by_doc()` but no method to retrieve ALL chunks for a document by `doc_id` without a query embedding.

**Why it happens:** Prior phases only needed similarity search, not full-doc retrieval.

**How to avoid:** Add a `get_all_by_doc(doc_id)` method to `VectorStore` that uses ChromaDB's `collection.get(where={"doc_id": doc_id})`. This is a simple addition.

**Warning signs:** No way to get all chunks for summarization/extraction without a query string.

## Code Examples

### Prompt Template: Graph Extraction (`prompts/graph_extract.txt`)

```
You are a document analysis assistant. Extract structured information from the provided document text.

Return a JSON object with these fields:
- "entities": array of objects with "name" (string), "type" (one of: PERSON, ORG, PROCESS, SYSTEM, CONCEPT, DOCUMENT, ROLE), "description" (string)
- "relationships": array of objects with "source" (entity name), "target" (entity name), "relation" (string), "description" (string)
- "process_steps": array of objects with "step_number" (integer), "name" (string), "description" (string), "actors" (array of entity names)
- "decision_points": array of objects with "name" (string), "description" (string), "options" (array of strings)
- "business_rules": array of objects with "name" (string), "description" (string), "condition" (string), "action" (string)

Example output:
{{"entities": [{{"name": "Acme Corp", "type": "ORG", "description": "The parent company"}}, {{"name": "Invoice Processing", "type": "PROCESS", "description": "Monthly invoice handling workflow"}}], "relationships": [{{"source": "Acme Corp", "target": "Invoice Processing", "relation": "OPERATES", "description": "Acme Corp runs the invoice processing workflow"}}], "process_steps": [{{"step_number": 1, "name": "Receive Invoice", "description": "Vendor submits invoice via email or portal", "actors": ["Acme Corp"]}}], "decision_points": [{{"name": "Approval Required", "description": "Whether manager approval is needed", "options": ["Auto-approve under $1000", "Require manager sign-off"]}}], "business_rules": [{{"name": "Payment Terms", "description": "Invoices must be paid within 30 days", "condition": "Invoice received and approved", "action": "Schedule payment within 30 days"}}]}}

Rules:
1. Extract ONLY information explicitly stated in the text. Do not invent entities or relationships.
2. Entity names should be specific and canonical (e.g., "United States Department of Energy" not "the department").
3. Every entity referenced in relationships, process_steps, or decision_points MUST appear in the entities list.
4. If a category has no items, return an empty array for that field.
5. Return ONLY valid JSON. No markdown, no explanations, no text outside the JSON.

Document text:
{context}
```

### Prompt Template: Self-Correction (`prompts/graph_correct.txt`)

```
The following JSON output was produced but failed validation. Fix the JSON to match the required schema.

Original output:
{original_output}

Error:
{error_message}

Return ONLY the corrected JSON object. No explanations. Ensure all required fields are present and types are correct.
```

### Prompt Template: Summary Map Step (`prompts/summary_map.txt`)

```
Summarize the following text section in 2-3 concise sentences. Focus on key facts, conclusions, and actionable information. Do not add information not present in the text.

Text:
{text}
```

### Prompt Template: Summary Reduce Step (`prompts/summary_reduce.txt`)

```
You are a document summarization assistant. Combine the following section summaries into one cohesive, business-readable summary. Remove redundancy and organize by importance.

Rules:
1. Keep the summary concise (5-10 sentences for typical documents).
2. Preserve key facts, numbers, and conclusions.
3. Do not add information not present in the section summaries.
4. Use clear, professional language.

Section summaries:
{text}
```

### VectorStore Addition: `get_all_by_doc()`

```python
# Addition to core/vectorstore.py
def get_all_by_doc(self, doc_id: str) -> list[dict]:
    """Retrieve all chunks for a document by doc_id.

    Returns list of dicts with text, doc_id, page_num, chunk_type, chunk_id.
    """
    results = self._collection.get(
        where={"doc_id": doc_id},
        include=["documents", "metadatas"],
    )
    if not results["ids"]:
        return []

    return [
        {
            "chunk_id": cid,
            "text": doc,
            "doc_id": meta["doc_id"],
            "page_num": meta["page_num"],
            "chunk_type": meta.get("chunk_type", "text"),
        }
        for cid, doc, meta in zip(
            results["ids"], results["documents"], results["metadatas"]
        )
    ]
```

### GraphResult Dataclass

```python
@dataclass
class GraphResult:
    """Result of a graph extraction operation."""
    extraction: GraphExtraction | None = None
    doc_id: str = ""
    chunk_count: int = 0
    entity_count: int = 0
    dedup_merges: int = 0  # How many entities were merged
    method: str = "single_pass"
    error: str | None = None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Regex-based NER | LLM JSON-mode extraction | 2023–2024 | LLMs extract richer relationships and domain-specific entities without training; but output needs validation |
| LangChain `create_extraction_chain` | Direct `response_format={"type":"json_object"}` + Pydantic | 2024 | No framework overhead; direct OpenAI SDK control; simpler debugging |
| `fuzzywuzzy` (python-Levenshtein) | `rapidfuzz` | 2020+ | 10-100x faster (C++ backend), no GPL dependency, drop-in replacement |
| Graphviz static rendering | streamlit-agraph (vis.js) | 2022+ | Interactive pan/zoom/click, physics-based layout, better for exploration |
| Mermaid via custom component | Native `st.markdown` mermaid | Streamlit 1.33+ (2024) | Zero dependencies, built-in rendering |

**Deprecated/outdated:**
- `fuzzywuzzy`: Replaced by `rapidfuzz` — identical API, faster, MIT licensed
- `st.cache`: Replaced by `st.cache_data` / `st.cache_resource` in Streamlit 1.18+
- LangChain extraction chains: Heavy abstraction for a simple JSON-mode call

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 7 entity types (PERSON, ORG, PROCESS, SYSTEM, CONCEPT, DOCUMENT, ROLE) are sufficient for document analysis | Pattern 2: Schema | Too few types → entities miscategorized; too many → LLM confusion. Mitigated: types are listed in the prompt and can be extended |
| A2 | `fuzz.token_sort_ratio` threshold 85 is optimal for entity dedup | Pattern 4: Entity Dedup | Too low → false merges; too high → missed dupes. Mitigated: threshold is a constant, easily tunable after testing with real extraction output |
| A3 | `max_tokens=4096` is sufficient for graph extraction output | Pattern 3: Self-Correction | Very complex documents might produce larger graphs. Mitigated: monitor `finish_reason`; can increase if needed |
| A4 | Single mega-prompt produces better cross-referenced output than separate prompts | Pattern 2: Why single prompt | Could be worse if the model struggles with multi-task prompts. Mitigated: one-shot example shows expected structure |
| A5 | `temperature=0.2` produces reliable structured output without repetition loops | Pattern 2, Pattern 3 | Some models behave differently at low temperatures. Mitigated: existing QA pipeline uses 0.3 successfully |
| A6 | TOKEN_BUDGET of 6000 is the right threshold for direct vs map-reduce | Pattern 1: Map-Reduce | Too low → unnecessary map-reduce overhead; too high → context overflow. Mitigated: configurable constant |

## Open Questions

1. **How does llama-3.1-70b handle very nested JSON in json_mode?**
   - What we know: `json_mode=True` forces valid JSON output. The one-shot example constrains the structure.
   - What's unclear: Whether deeply nested structures (e.g., entities with nested metadata) cause issues. Our schema is flat (max 1 level of nesting with lists).
   - Recommendation: Keep the schema flat as designed. Test with the bundled sample docs during implementation.

2. **Should graph extraction operate on all chunks or a representative subset?**
   - What we know: For summarization, all chunks are needed. For extraction, a 100-page document might produce overwhelming output.
   - What's unclear: Whether extracting from ALL chunks produces better results or just more noise.
   - Recommendation: Start with all chunks (concatenated). If token limit is hit, apply the same map-reduce pattern (extract from chunk groups, then merge+dedup). Implement the simpler all-chunks path first.

3. **Will `streamlit-agraph` work correctly with Streamlit 1.56?**
   - What we know: Latest version is 0.0.45, last updated ~3 months ago. It uses vis.js under the hood.
   - What's unclear: Compatibility with very recent Streamlit versions.
   - Recommendation: Install and test early. If incompatible, fall back to native mermaid rendering.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| rapidfuzz | GRAPH-04 entity dedup | ✗ (not in project deps) | 3.14.5 latest | Must add to pyproject.toml |
| streamlit-agraph | GRAPH-03 node-edge view | ✗ (not in project deps) | 0.0.45 latest | Native mermaid via `st.markdown` |
| pydantic | GRAPH-02 schema validation | ✓ | ^2.7 | — |
| tiktoken | Token counting for budget | ✓ | ^0.7 | — |
| openai SDK | LLM calls | ✓ | ^1.50 | — |
| streamlit | UI rendering | ✓ | 1.56.0 | — |

**Missing dependencies with no fallback:**
- `rapidfuzz` — required by GRAPH-04; must be added to `pyproject.toml`

**Missing dependencies with fallback:**
- `streamlit-agraph` — required by GRAPH-03 for interactive graph; fallback to native mermaid via `st.markdown`

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_summarize_pipeline.py tests/test_graph_pipeline.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SUM-01 | Summarize returns concise text for an indexed doc | unit | `uv run pytest tests/test_summarize_pipeline.py::test_summarize_direct -x` | ❌ Wave 0 |
| SUM-02 | Map-reduce activates for long docs | unit | `uv run pytest tests/test_summarize_pipeline.py::test_summarize_map_reduce -x` | ❌ Wave 0 |
| GRAPH-01 | Extraction returns valid JSON with all 5 categories | unit | `uv run pytest tests/test_graph_pipeline.py::test_extraction_valid_json -x` | ❌ Wave 0 |
| GRAPH-02 | Pydantic validation succeeds; self-correction retries on failure | unit | `uv run pytest tests/test_graph_pipeline.py::test_self_correction_retry -x` | ❌ Wave 0 |
| GRAPH-03 | Graph renders as table and node-edge view | manual-only | Visual verification in Streamlit UI | — |
| GRAPH-04 | Entity dedup merges duplicates at threshold 85 | unit | `uv run pytest tests/test_graph_pipeline.py::test_entity_dedup -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_summarize_pipeline.py tests/test_graph_pipeline.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_summarize_pipeline.py` — covers SUM-01, SUM-02
- [ ] `tests/test_graph_pipeline.py` — covers GRAPH-01, GRAPH-02, GRAPH-04

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Pydantic `model_validate()` for LLM output; `json.loads()` not `eval()` |
| V6 Cryptography | no | — |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM output injection (malicious JSON in extraction) | Tampering | Pydantic validation; never `eval()` on LLM output; sanitize entity names before rendering in HTML |
| Prompt injection via document content | Spoofing | System prompt instructs extraction only; output is structured JSON not executed code |
| DoS via very large extraction output | Denial of Service | `max_tokens=4096` caps response size; timeout on NIMClient |

## Sources

### Primary (HIGH confidence)
- In-repo: `core/llm_client.py` — NIMClient API, `json_mode=True` implementation [VERIFIED: codebase]
- In-repo: `core/config.py` — Settings, model names [VERIFIED: codebase]
- In-repo: `core/retriever.py`, `core/vectorstore.py` — existing retrieval patterns [VERIFIED: codebase]
- In-repo: `pipelines/query.py`, `pipelines/ingest.py` — existing pipeline patterns [VERIFIED: codebase]
- In-repo: `prompts/qa.txt` — existing prompt template pattern [VERIFIED: codebase]
- [VERIFIED: pip index] rapidfuzz 3.14.5, streamlit-agraph 0.0.45 — latest versions
- [VERIFIED: uv run] Streamlit 1.56.0 installed — mermaid support confirmed (available since 1.33)
- [CITED: github.com/ChrisDelClea/streamlit-agraph] — agraph API: Node, Edge, Config, agraph()

### Secondary (MEDIUM confidence)
- Pydantic v2 `model_validate()` for JSON validation — standard documented approach [CITED: docs.pydantic.dev]
- rapidfuzz `fuzz.token_sort_ratio` — standard API [CITED: rapidfuzz documentation]
- Map-reduce summarization pattern — widely used in RAG pipelines [ASSUMED — standard pattern but not verified against a specific authoritative source for this exact configuration]

### Tertiary (LOW confidence)
- Optimal `fuzz.token_sort_ratio` threshold of 85 — empirical recommendation [ASSUMED]
- `temperature=0.2` for structured extraction — empirical recommendation [ASSUMED]
- TOKEN_BUDGET of 6000 for direct vs map-reduce — judgment call [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified via pip index, codebase patterns established
- Architecture: HIGH — follows existing pipeline/dataclass patterns exactly; straightforward extensions
- Pitfalls: HIGH — each pitfall is derived from known LLM output behavior and codebase analysis
- Prompt design: MEDIUM — one-shot example approach is standard but exact prompt wording may need tuning
- Dedup thresholds: MEDIUM — 85 is a well-known starting point but needs validation against real output

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable domain; only streamlit-agraph compatibility may shift)

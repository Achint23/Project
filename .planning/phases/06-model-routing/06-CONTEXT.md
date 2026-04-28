# Phase 6: Model Routing + Side-by-Side Comparison - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds a pure-function model router, a sidebar toggle for manual/auto model selection, per-call metadata display (model used, tokens consumed, latency), and a side-by-side comparison panel that runs the same question through two models in parallel. No new external dependencies are introduced — this is pure composition over the existing NIMClient, pipelines, and Streamlit UI.

</domain>

<decisions>
## Implementation Decisions

### Router Design
- **D-01:** The router is a pure function `route(task, signals) → RouteDecision(model, reason)` in `routers/model_router.py`. No I/O, no side effects, all configuration injected via parameters. `TaskType` is an enum (`QA`, `SUMMARY`, `GRAPH_EXTRACT`), `RouteDecision` is a dataclass with `model: str` and `reason: str`.
- **D-02:** Auto-routing heuristics: graph extraction always routes to the large model (JSON-mode reliability); long documents (>10,000 chars or >15 chunks) route to the large model; short Q&A and summaries route to the smaller model. These are simple, explainable rules — not ML-based.
- **D-03:** Model names are always read from `Settings` (injected), never hardcoded string literals in the router function.

### Model Selection UI
- **D-04:** Sidebar radio toggle with three options: `auto`, `small (route)`, `large (direct)`. Stored in `st.session_state.model_routing_mode`. Default is `auto`.
- **D-05:** The routing mode applies to all LLM calls in the app (chat, summarize, graph extract). When in `auto` mode, the router's `reason` string is displayed below the answer.

### Per-Call Metadata Display
- **D-06:** Every LLM call extracts `model_used`, `prompt_tokens`, `completion_tokens`, and `latency_ms` from the response object. These are added as fields to existing result dataclasses (QueryResult, SummaryResult, GraphResult) with default values for backward compatibility.
- **D-07:** Metadata is displayed using `st.caption` or small text below each answer showing model name, token count, and latency. Not `st.metric` — that's reserved for the comparison panel.
- **D-08:** Guard all `response.usage` access with null checks. Display "N/A" if usage data is unavailable from the NIM endpoint.

### Side-by-Side Comparison Panel
- **D-09:** Comparison panel is a new tab ("🔄 Compare") in the main tab bar alongside Chat, Summary, and Graph. It gets its own UI partial `ui/comparison.py`.
- **D-10:** Parallel execution uses `asyncio.run()` → `asyncio.gather()` → `loop.run_in_executor(ThreadPoolExecutor, sync_call)` to bridge the existing sync NIMClient to concurrent execution. No `AsyncOpenAI` client introduced.
- **D-11:** Chunks are retrieved once (shared) before dispatching to both models. Both calls use identical system prompt, user prompt, retrieved chunks, and temperature (0.3). Only the model differs.
- **D-12:** Comparison results displayed in two `st.columns` with `st.metric` for latency and token counts, and `st.markdown` for the answers.
- **D-13:** A prominent `st.info` disclaimer reads: "⚠️ Concept demo, not benchmark. Results may vary between runs due to model non-determinism and network conditions."
- **D-14:** Caching is explicitly disabled for comparison calls — no `@st.cache_data` on the comparison function.

### Error Handling
- **D-15:** If one model fails during comparison, show the error for the failed model alongside the successful result. Don't silently fall back or hide the failure — the comparison is only meaningful with both results visible.
- **D-16:** Existing NIMClient retry/backoff handles 429/504 transparently for both parallel calls. No additional rate-limit logic needed.

### Agent's Discretion
- Exact wording of router reason strings — as long as they are human-readable and explain the routing decision
- Exact layout proportions for the comparison panel columns
- Whether to add a brief stagger (0.1s) between parallel API calls to reduce rate-limit risk
- Color scheme for model badges in metadata display

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Architecture
- `.planning/research/SUMMARY.md` — Overall architecture, phase ordering rationale, pitfall #6 (routing comparison)
- `.planning/phases/06-model-routing/06-RESEARCH.md` — Phase 6 research: standard stack, architecture patterns, code examples, common pitfalls
- `.planning/ROADMAP.md` §Phase 6 — Success criteria and requirements mapping
- `.planning/REQUIREMENTS.md` §Model Routing — ROUTE-01 through ROUTE-05 specifications

### Existing Code
- `core/llm_client.py` — NIMClient with chat() model override, retry/backoff, embed()
- `core/config.py` — Settings class with nvidia_model and nvidia_route_model
- `pipelines/query.py` — QueryResult dataclass, run_query() pattern, citation validation
- `pipelines/summarize.py` — SummaryResult dataclass, summarize pattern
- `pipelines/graph.py` — GraphResult, graph extraction pipeline
- `ui/sidebar.py` — Current sidebar structure (document list + delete)
- `app.py` — Tab-based layout composition root

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `NIMClient.chat(model=...)`: Already supports per-call model override — no changes to the client needed
- `Settings.nvidia_route_model`: Already configured as `meta/llama-3.1-8b-instruct` — route model ready
- `NIMClient._call_with_retry()`: Retry/backoff on 429/504 — works per-thread in parallel execution
- `QueryResult`, `SummaryResult`: Existing dataclasses to extend with metadata fields
- `st.tabs` layout in `app.py`: Existing tab bar to add comparison tab

### Established Patterns
- **Dataclass results:** All pipelines return plain dataclasses (QueryResult, SummaryResult, IngestResult) — follow this for ComparisonResult and LLMCallMetadata
- **Prompt templates from files:** `prompts/*.txt` loaded via `Path.read_text()` — comparison uses same QA prompt
- **Temperature 0.3:** Used across all grounded Q&A calls — must match in comparison
- **@st.cache_resource for singletons:** NIMClient, VectorStore — must NOT be used for comparison calls
- **Session state for UI state:** `st.session_state.documents`, `st.session_state.chat_messages` — follow for routing mode

### Integration Points
- `app.py`: Add comparison tab to existing `st.tabs` call
- `ui/sidebar.py`: Add model routing radio toggle section
- `pipelines/query.py`: Extend `run_query()` to accept explicit model parameter and return metadata
- `pipelines/summarize.py`: Extend to accept model parameter and return metadata
- `pipelines/graph.py`: Extend to accept model parameter and return metadata
- `ui/chat.py`: Display model/tokens/latency metadata below each answer
- `ui/summary_view.py`: Display metadata below summary
- `ui/graph_view.py`: Display metadata below graph results

</code_context>

<specifics>
## Specific Ideas

- The router's `reason` string is the demo's hero moment — "routed via llama-3.1-8b because this is a short Q&A task" makes routing tangible and explainable
- Side-by-side comparison is the strongest demo visual — identical question, two models, side-by-side answers with latency/tokens
- The disclaimer is important to set expectations — this is a concept demo, not a benchmarking tool

</specifics>

<deferred>
## Deferred Ideas

- Streaming token output (SSE) in comparison panel — Phase 7 polish item
- Cost estimation per model call — out of scope for POC
- Historical comparison logs / persistence — out of scope for POC
- More sophisticated routing (ML-based, cost-aware) — explicitly out of scope per PROJECT.md
- A/B testing framework — enterprise feature, not POC

None — discussion stayed within phase scope (deferred ideas are all out-of-scope items from PROJECT.md)

</deferred>

---

*Phase: 06-model-routing*
*Context gathered: 2026-04-28*

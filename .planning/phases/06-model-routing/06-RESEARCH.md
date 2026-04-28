# Phase 6: Model Routing + Side-by-Side Comparison — Research

**Researched:** 2026-04-28
**Domain:** Model routing, parallel LLM calls, side-by-side comparison UI in Streamlit
**Confidence:** HIGH

## Summary

Phase 6 adds a pure-function model router, a manual/auto model selection toggle, per-call metadata display (model, tokens, latency), and a side-by-side comparison panel that runs the same query against two models in parallel. The implementation is straightforward because the existing `NIMClient` already supports model override per call, the OpenAI-compatible response objects include `usage` fields with token counts, and Streamlit's `st.columns` provides the two-column layout natively.

The primary technical risk is running two LLM calls in parallel from Streamlit's synchronous script execution model. The proven pattern is `asyncio.run()` wrapping `asyncio.gather()` with `loop.run_in_executor()` to dispatch the existing sync `NIMClient.chat()` calls to a thread pool. This avoids introducing `AsyncOpenAI` as a second client pattern while satisfying the `asyncio.gather` requirement from the project instructions.

**Primary recommendation:** Use `concurrent.futures.ThreadPoolExecutor` dispatched via `asyncio.gather` + `run_in_executor` for parallel calls; keep the existing sync `NIMClient`; extract `response.usage` for token display; use `time.perf_counter()` for latency; implement the router as a pure function with a `TaskType` enum and `RouteDecision` dataclass.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ROUTE-01 | `routers/model_router.py` exposes pure function `route(task, signals) → RouteDecision(model, reason)` | Router design pattern section: TaskType enum + RouteDecision dataclass + heuristic rules |
| ROUTE-02 | Sidebar toggle: `auto`, `small (route)`, `large (direct)` with model/tokens/latency display | Streamlit `st.radio` in sidebar + `st.metric` for per-call metadata; Architecture Patterns §2 |
| ROUTE-03 | Every LLM call surfaces model used, tokens consumed, and latency in UI | OpenAI SDK response.usage fields + time.perf_counter() pattern; Code Examples §2–3 |
| ROUTE-04 | Side-by-side comparison panel with parallel asyncio.gather calls | Async-in-Streamlit pattern: asyncio.run + gather + run_in_executor; Code Examples §4 |
| ROUTE-05 | Auto-router decisions based on task type + doc length, reason rendered as plain text | Router heuristic rules in Architecture Patterns §1; reason string is part of RouteDecision |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Model routing logic | Core/Router (`routers/`) | — | Pure function, no UI dependency, unit-testable |
| Per-call metadata extraction (tokens, latency) | Pipeline layer (`pipelines/`) | — | Wraps NIMClient calls, returns enriched result dataclasses |
| Model selection toggle | UI (`ui/sidebar.py`) | — | Streamlit widget stored in session_state |
| Side-by-side comparison panel | UI (`ui/`) | Pipeline layer | UI dispatches parallel calls, pipelines execute them |
| Parallel LLM execution | Pipeline layer | — | asyncio.gather + ThreadPoolExecutor in a pipeline function |
| Metadata display (model, tokens, latency) | UI (`ui/`) | — | st.metric / st.caption rendering |

## Standard Stack

### Core

No new libraries required. Phase 6 uses only existing dependencies.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `openai` | `^1.50` (already installed) | Chat completions with per-call model override + response.usage token counts | Already the NIM client; response.usage is part of the OpenAI-compatible API spec |
| `asyncio` | stdlib | `asyncio.run()` + `asyncio.gather()` for parallel LLM calls | Python standard library; no install needed |
| `concurrent.futures` | stdlib | `ThreadPoolExecutor` for `run_in_executor` bridging sync NIMClient to async gather | Python standard library; no install needed |
| `time` | stdlib | `time.perf_counter()` for sub-millisecond latency measurement | Python standard library |
| `streamlit` | `^1.40` (already installed) | `st.columns`, `st.metric`, `st.radio`, `st.session_state` for UI | Already installed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `enum` | stdlib | `TaskType` enum for router input | Always — type-safe task categorization |
| `dataclasses` | stdlib | `RouteDecision` dataclass for router output | Always — consistent with existing codebase pattern (QueryResult, SummaryResult, etc.) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.gather` + `run_in_executor` (sync client in threads) | `AsyncOpenAI` client with native async | Would require a second client instantiation pattern, `@st.cache_resource` for the async client, and changes to NIMClient; unnecessary complexity for 2 parallel calls |
| `concurrent.futures.ThreadPoolExecutor` directly (no asyncio) | Just `executor.map()` | Simpler but doesn't satisfy the `asyncio.gather` requirement in copilot-instructions.md |
| `nest_asyncio` (patch existing event loop) | `asyncio.run()` (new event loop) | `nest_asyncio` adds a dependency and patches global state; `asyncio.run()` works in Streamlit's thread because Tornado's loop is in a different thread |

**Installation:** No new packages needed. All dependencies are already in `pyproject.toml`.

## Architecture Patterns

### System Architecture Diagram

```
User clicks "Compare" in UI
         │
         ▼
┌─────────────────────────────────────────────┐
│           ui/comparison.py                   │
│  ┌──────────────────────────────────────┐   │
│  │ 1. Read question + model selection   │   │
│  │ 2. Retrieve chunks (shared)          │   │
│  │ 3. Dispatch parallel_compare()       │   │
│  └──────────┬───────────────────────────┘   │
└─────────────┼───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│       pipelines/query.py                     │
│  ┌──────────────────────────────────────┐   │
│  │ parallel_compare():                  │   │
│  │   asyncio.run(                       │   │
│  │     asyncio.gather(                  │   │
│  │       run_in_executor(query_model_a),│   │
│  │       run_in_executor(query_model_b) │   │
│  │     )                                │   │
│  │   )                                  │   │
│  └──────┬──────────────┬────────────────┘   │
│         │              │                     │
│    Thread A        Thread B                  │
│         │              │                     │
│         ▼              ▼                     │
│   NIMClient.chat() NIMClient.chat()          │
│   (model=large)    (model=small)             │
│         │              │                     │
│         ▼              ▼                     │
│   ComparisonResult (answer, tokens, latency) │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  routers/model_router.py (for auto mode)     │
│  route(task, signals) → RouteDecision        │
│  Pure function, no I/O, no side effects      │
└─────────────────────────────────────────────┘
```

**Data flow for normal Q&A with routing:**
1. User asks question → sidebar model selection read from `st.session_state`
2. If `auto`: `route(TaskType.QA, {"doc_length": len, ...})` → `RouteDecision(model, reason)`
3. If `small` or `large`: model selected directly
4. `run_query()` called with explicit `model` parameter → response includes `usage` + latency
5. UI renders answer + model badge + token count + latency + router reason (if auto)

**Data flow for side-by-side comparison:**
1. User enters question in comparison panel
2. Chunks retrieved once (shared)
3. `parallel_compare()` fires two `run_query_with_model()` calls via `asyncio.gather`
4. Both results returned with answer, tokens, latency
5. UI renders in two `st.columns` with `st.metric` widgets

### Recommended Project Structure

```
routers/
├── __init__.py
└── model_router.py      # route() pure function + RouteDecision + TaskType
pipelines/
└── query.py              # Extended: run_query_with_model(), parallel_compare()
ui/
├── sidebar.py            # Extended: model selection radio
└── comparison.py         # NEW: side-by-side comparison panel
app.py                    # Extended: new "Compare" tab
```

### Pattern 1: Pure-Function Router with Explainable Decision

**What:** A stateless function that maps (task_type, signals) → (model_name, reason_string). No I/O, no side effects, no config reads inside the function — all configuration injected via parameters.

**When to use:** Every LLM call site (query, summarize, graph) when mode is `auto`.

**Why pure function:**
- Unit-testable without mocks
- Deterministic: same inputs → same output
- The `reason` string is the demo's hero — it must be human-readable and predictable
- No hidden state or caching behavior to debug

### Pattern 2: Enriched Pipeline Results with Metadata

**What:** Extend existing pipeline result dataclasses to include `model_used`, `prompt_tokens`, `completion_tokens`, `latency_ms` fields. Every LLM call extracts these from the response and timing.

**When to use:** All pipeline functions that call `NIMClient.chat()`.

**Why:** ROUTE-03 requires every LLM call to surface model/tokens/latency. Adding fields to existing dataclasses is backward-compatible (default values) and follows the established pattern.

### Pattern 3: Parallel Execution via asyncio.gather + run_in_executor

**What:** Bridge the sync `NIMClient.chat()` to `asyncio.gather()` using `ThreadPoolExecutor` and `loop.run_in_executor()`. Wrap the entire async function in `asyncio.run()` at the Streamlit call site.

**When to use:** Side-by-side comparison panel only.

**Why this specific pattern:**
- Streamlit runs scripts synchronously in a thread; Tornado's event loop is in a separate thread
- `asyncio.run()` creates a new event loop in the current thread — no conflict with Tornado
- `run_in_executor()` dispatches blocking `NIMClient.chat()` calls to separate threads
- `asyncio.gather()` collects results from both threads concurrently
- No need for `AsyncOpenAI` or `nest_asyncio`

### Anti-Patterns to Avoid

- **Caching in comparison panel:** `@st.cache_data` on comparison calls would defeat the purpose. Both calls must hit the API fresh every time. Use a dedicated function without caching decorators.
- **Sequential fallback on error:** If one model fails, don't silently fall back to the other. Show the error for the failed model alongside the successful result. The comparison is only meaningful with both results.
- **Router with I/O:** Don't read config files, make API calls, or access databases inside `route()`. All inputs must be passed as parameters.
- **Shared mutable state between parallel calls:** Each parallel call must use independent prompt strings and response objects. The shared input (chunks, question, temperature) must be read-only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token counting from response | Manual tokenizer counting | `response.usage.prompt_tokens` / `.completion_tokens` from OpenAI SDK response | NIM returns these in the response object; counting yourself would be inaccurate (tokenizer mismatch) |
| Latency measurement | `datetime.now()` subtraction | `time.perf_counter()` | perf_counter is monotonic and has sub-microsecond resolution; datetime.now() has ~15ms resolution on Windows |
| Parallel execution | Manual threading with `threading.Thread` + shared result list | `asyncio.gather()` + `run_in_executor()` | gather handles result collection and exception propagation; raw threads need manual synchronization |
| Two-column comparison layout | Custom HTML/CSS | `st.columns(2)` | Streamlit native, responsive, handles rerun correctly |
| Metrics display (tokens, latency) | Custom `st.write` formatting | `st.metric(label, value, delta)` | Streamlit native component with built-in delta display and formatting |

**Key insight:** This phase is almost entirely composition over existing capabilities. The NIMClient already supports `model` override per call and returns `response.usage`. Streamlit has native two-column layout and metrics widgets. The only new code is the router function and the parallel execution bridge.

## Common Pitfalls

### Pitfall 1: asyncio.run() fails with "event loop already running"

**What goes wrong:** Calling `asyncio.run()` when an event loop is already running in the current thread raises `RuntimeError`.
**Why it happens:** Some environments (Jupyter, certain ASGI servers) run their own event loop in the main thread.
**How to avoid:** In Streamlit, this is NOT an issue because Tornado's event loop runs in a separate thread, and the script runs in a different thread without an event loop. However, if this ever surfaces, the fallback is `concurrent.futures.ThreadPoolExecutor` with `executor.submit()` + `future.result()` directly (no asyncio).
**Warning signs:** `RuntimeError: This event loop is already running` on the first comparison attempt.

### Pitfall 2: NIM response.usage is None or missing fields

**What goes wrong:** Token counts display as `None` or the code crashes on `.prompt_tokens` access.
**Why it happens:** Some NIM model endpoints may not return `usage` in the response, especially during rate-limited retries or for certain model versions. The OpenAI SDK makes `usage` an optional field.
**How to avoid:** Always guard with `if response.usage:` before accessing token fields. Display "N/A" when usage is unavailable. [ASSUMED — NIM typically returns usage, but edge cases exist]
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'prompt_tokens'` in production.

### Pitfall 3: Comparison panel results look cached / identical

**What goes wrong:** Both columns show the same answer, or the second run returns instantly without hitting the API.
**Why it happens:** Streamlit's `@st.cache_data` or `@st.cache_resource` somewhere in the call chain is caching the LLM response.
**How to avoid:** The comparison pipeline function must NOT be decorated with any caching decorator. Verify by checking that latency is non-trivial (>1s) on every comparison run.
**Warning signs:** Both latencies show as 0ms, or both answers are byte-for-byte identical.

### Pitfall 4: Rate limit on parallel calls

**What goes wrong:** One or both parallel calls return 429 Too Many Requests.
**Why it happens:** Two simultaneous requests from the same API key doubles the instantaneous request rate against the free tier's per-minute limit.
**How to avoid:** The existing `NIMClient._call_with_retry()` handles 429 with exponential backoff. Since both calls run in separate threads, their retries are independent. For extra safety, add a brief (0.1s) stagger between dispatching the two calls. Display "Rate limited — retrying..." in the UI via the error handling.
**Warning signs:** Frequent 429s specifically during comparison runs but not during normal Q&A.

### Pitfall 5: Latency measurement includes Streamlit rerun overhead

**What goes wrong:** Latency numbers are inflated or inconsistent.
**Why it happens:** Measuring from button click to result display includes Streamlit's rerun overhead, not just the API call.
**How to avoid:** Measure latency tightly around only the `NIMClient.chat()` call using `time.perf_counter()` before and after. Return latency as part of the result dataclass, not measured in the UI layer.
**Warning signs:** Latency shows 5–10s when the model typically responds in 2–3s.

### Pitfall 6: Router returns wrong model name string

**What goes wrong:** `openai.NotFoundError: Model 'wrong-name' not found` at call time.
**Why it happens:** Typo in model name string, or config not loaded properly.
**How to avoid:** Router reads model names from `Settings` (injected), never hardcodes model strings. Test the router with the actual model names from the config. Add a constant or enum mapping to avoid string literals.
**Warning signs:** `404` or `NotFoundError` on the first routed call.

## Code Examples

### 1. RouteDecision Dataclass and TaskType Enum

```python
# routers/model_router.py
# Pattern: pure function with explainable decision

from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    QA = "qa"
    SUMMARY = "summary"
    GRAPH_EXTRACT = "graph_extract"


@dataclass
class RouteDecision:
    """Routing decision with human-readable reason."""
    model: str
    reason: str


def route(
    task: TaskType,
    settings_large_model: str,
    settings_route_model: str,
    doc_length: int = 0,
    chunk_count: int = 0,
) -> RouteDecision:
    """Pure function: decide which model to use based on task + signals.

    All configuration injected via parameters — no I/O, no side effects.
    """
    # Graph extraction requires reliable JSON mode → large model
    if task == TaskType.GRAPH_EXTRACT:
        return RouteDecision(
            model=settings_large_model,
            reason=f"Graph extraction requires reliable JSON-mode output → using large model",
        )

    # Long documents need stronger comprehension → large model
    if doc_length > 10_000 or chunk_count > 15:
        return RouteDecision(
            model=settings_large_model,
            reason=f"Document is large ({doc_length:,} chars, {chunk_count} chunks) → using large model for better comprehension",
        )

    # Short Q&A and summaries can use the smaller, faster model
    return RouteDecision(
        model=settings_route_model,
        reason=f"Task is {task.value} on a short document → routing to smaller model for faster response",
    )
```

### 2. Token and Latency Extraction from NIMClient Response

```python
# Pattern: extract metadata from OpenAI-compatible response object

import time
from dataclasses import dataclass


@dataclass
class LLMCallMetadata:
    """Metadata from a single LLM call."""
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float


def call_with_metadata(nim_client, messages, model, temperature=0.3, max_tokens=1024):
    """Wrap NIMClient.chat() to extract timing and token usage."""
    start = time.perf_counter()
    response = nim_client.chat(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Guard against missing usage (some NIM endpoints may omit it)
    usage = response.usage
    metadata = LLMCallMetadata(
        model_used=model,
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
        total_tokens=usage.total_tokens if usage else 0,
        latency_ms=round(elapsed_ms, 1),
    )

    content = response.choices[0].message.content
    return content, metadata
```

### 3. Enriched QueryResult with Metadata

```python
# Pattern: extend existing dataclass with optional metadata fields

from dataclasses import dataclass, field


@dataclass
class QueryResult:
    """Structured result from a Q&A query — extended with routing metadata."""
    answer: str
    citations: list[dict] = field(default_factory=list)
    hallucinated_ids: list[str] = field(default_factory=list)
    retrieved_chunks: list = field(default_factory=list)
    # New fields for Phase 6
    model_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    route_reason: str = ""
```

### 4. Parallel Comparison via asyncio.gather + run_in_executor

```python
# Pattern: bridge sync NIMClient to asyncio.gather via ThreadPoolExecutor

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass
class ComparisonResult:
    """Results from running the same query through two models."""
    result_large: QueryResult
    result_small: QueryResult


def run_comparison(
    question: str,
    chunks: list,
    nim_client,
    large_model: str,
    small_model: str,
    temperature: float = 0.3,
) -> ComparisonResult:
    """Run the same query against two models in parallel.

    Uses asyncio.gather + ThreadPoolExecutor to dispatch sync NIMClient
    calls to separate threads. Caching is intentionally NOT applied.
    """

    def _query_with_model(model: str) -> QueryResult:
        """Execute a single query with a specific model. Runs in a thread."""
        # Identical inputs: same question, same chunks, same temperature
        # Only the model differs
        return _run_query_internal(
            question=question,
            chunks=chunks,
            nim_client=nim_client,
            model=model,
            temperature=temperature,
        )

    async def _parallel():
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=2) as executor:
            large_future = loop.run_in_executor(executor, _query_with_model, large_model)
            small_future = loop.run_in_executor(executor, _query_with_model, small_model)
            result_large, result_small = await asyncio.gather(
                large_future, small_future
            )
        return result_large, result_small

    result_large, result_small = asyncio.run(_parallel())

    return ComparisonResult(
        result_large=result_large,
        result_small=result_small,
    )
```

### 5. Side-by-Side UI with st.columns and st.metric

```python
# Pattern: two-column comparison display in Streamlit

import streamlit as st


def render_comparison_result(result: ComparisonResult):
    """Render side-by-side comparison of two model responses."""

    st.info(
        "⚠️ **Concept demo, not benchmark.** "
        "Results may vary between runs due to model non-determinism "
        "and network conditions."
    )

    col_large, col_small = st.columns(2)

    with col_large:
        st.subheader(f"🔵 {result.result_large.model_used}")
        st.metric("Latency", f"{result.result_large.latency_ms:.0f} ms")
        st.metric("Tokens", result.result_large.prompt_tokens + result.result_large.completion_tokens)
        st.markdown(result.result_large.answer)

    with col_small:
        st.subheader(f"🟢 {result.result_small.model_used}")
        st.metric("Latency", f"{result.result_small.latency_ms:.0f} ms")
        st.metric("Tokens", result.result_small.prompt_tokens + result.result_small.completion_tokens)
        st.markdown(result.result_small.answer)
```

### 6. Model Selection in Sidebar

```python
# Pattern: radio toggle in sidebar stored in session_state

import streamlit as st


def render_model_selector():
    """Render model selection radio in the sidebar."""
    with st.sidebar:
        st.subheader("🔀 Model Routing")
        mode = st.radio(
            "Model selection",
            options=["auto", "small (route)", "large (direct)"],
            index=0,
            key="model_routing_mode",
            help="Auto: router decides based on task. Small: always use the smaller model. Large: always use the large model.",
        )
    return mode
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `threading.Thread` + shared result list for parallel calls | `asyncio.gather` + `run_in_executor` | Python 3.9+ | Cleaner result collection, automatic exception propagation |
| `time.time()` for latency | `time.perf_counter()` | Python 3.3+ | Monotonic clock, sub-microsecond resolution, not affected by system clock adjustments |
| Custom token counting via tiktoken | `response.usage` from OpenAI SDK | OpenAI SDK 1.0+ | Accurate counts from the API itself, no tokenizer mismatch risk |
| `nest_asyncio` for async in sync contexts | `asyncio.run()` in Streamlit's thread | Streamlit 1.x on Tornado | No patching needed; Streamlit's script thread has no event loop to conflict with |

**Deprecated/outdated:**
- `nest_asyncio`: Not needed in Streamlit's current architecture. Was necessary in Jupyter-like environments where the main thread runs an event loop.
- `st.experimental_memo` / `st.experimental_singleton`: Replaced by `st.cache_data` / `st.cache_resource` in Streamlit 1.18.0.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | NVIDIA NIM returns `response.usage` with `prompt_tokens`, `completion_tokens`, `total_tokens` for all chat completion calls | Code Examples §2 | Token display shows zeros; fallback to "N/A" display already in code pattern |
| A2 | `meta/llama-3.1-8b-instruct` is available on NVIDIA NIM free tier and performs adequately for grounded Q&A | Standard Stack | Route model doesn't work; env-configurable `NVIDIA_ROUTE_MODEL` allows switching to any available model |
| A3 | `asyncio.run()` works in Streamlit's script execution thread without "event loop already running" error | Pitfall 1 | Comparison panel fails; fallback to raw `ThreadPoolExecutor.submit()` + `future.result()` |
| A4 | Two simultaneous NVIDIA NIM API calls from the same API key are allowed on the free tier | Pitfall 4 | One call gets 429; existing retry/backoff handles it, but comparison takes longer |
| A5 | NVIDIA free tier rate limits are per-minute, not per-second, allowing burst of 2 concurrent requests | Common Pitfalls | Need to serialize calls or add stagger; slight latency increase but comparison still works |

## Open Questions

1. **NVIDIA NIM exact free-tier rate limits**
   - What we know: Free tier has rate limits; 429 responses are returned when exceeded; limits are NOT publicly documented with specific numbers. The project already handles 429 with retry/backoff. [ASSUMED: ~10K requests/month based on community reports]
   - What's unclear: Exact per-minute request limit and whether two concurrent requests count as one or two against the limit.
   - Recommendation: Accept the uncertainty. The existing retry/backoff in `NIMClient._call_with_retry()` handles 429 transparently. Two concurrent calls are well within normal usage. If both hit rate limits, retries will stagger them naturally.

2. **NIM response.usage field consistency**
   - What we know: OpenAI SDK defines `usage` as an optional field on `ChatCompletion`. NIM's OpenAI-compatible endpoint follows this spec. [ASSUMED: NIM returns usage for llama-3.1 models]
   - What's unclear: Whether all NIM model endpoints return `usage` consistently, or if some omit it.
   - Recommendation: Guard all `response.usage` access with a null check. Display "N/A" when unavailable. Test empirically during Phase 6 execution.

3. **Small model JSON-mode reliability for graph extraction**
   - What we know: `meta/llama-3.1-8b-instruct` supports `response_format={"type":"json_object"}`. The 70B model is more reliable at following the Pydantic schema.
   - What's unclear: How often the 8B model produces malformed JSON in graph extraction tasks.
   - Recommendation: The auto-router should always route graph extraction to the large model (ROUTE-05 heuristic). The comparison panel can still compare 8B vs 70B for graph tasks to demonstrate the quality difference.

## Environment Availability

Step 2.6: SKIPPED — Phase 6 has no external dependencies beyond the already-installed packages. All required libraries (`openai`, `streamlit`, `asyncio`, `concurrent.futures`, `time`, `enum`, `dataclasses`) are either already in `pyproject.toml` or Python stdlib.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio 0.23+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ROUTE-01 | `route()` returns correct RouteDecision for each TaskType + signal combination | unit | `uv run pytest tests/test_model_router.py -x` | ❌ Wave 0 |
| ROUTE-02 | Sidebar radio sets session_state correctly | unit | `uv run pytest tests/test_sidebar_routing.py -x` | ❌ Wave 0 |
| ROUTE-03 | LLM call extracts model/tokens/latency into result dataclass | unit | `uv run pytest tests/test_query_pipeline.py -x -k metadata` | ❌ Wave 0 |
| ROUTE-04 | `run_comparison()` returns two results with different model_used values | unit | `uv run pytest tests/test_comparison.py -x` | ❌ Wave 0 |
| ROUTE-05 | Auto-router returns correct model + reason for different task/signal combos | unit | `uv run pytest tests/test_model_router.py -x -k auto` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_model_router.py` — covers ROUTE-01, ROUTE-05 (pure function, no mocks needed)
- [ ] `tests/test_comparison.py` — covers ROUTE-04 (mock NIMClient for parallel execution test)
- [ ] Extended `tests/test_query_pipeline.py` — covers ROUTE-03 (mock response.usage metadata extraction)
- [ ] `tests/test_sidebar_routing.py` — covers ROUTE-02 (Streamlit session_state mock)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (no new auth; NVIDIA_API_KEY already handled) |
| V3 Session Management | no | — (Streamlit session_state unchanged) |
| V4 Access Control | no | — (single-user POC) |
| V5 Input Validation | yes | Pydantic `TaskType` enum validates router input; model names come from Settings, not user input |
| V6 Cryptography | no | — (no new crypto) |

### Known Threat Patterns for This Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Model name injection via sidebar input | Tampering | Model names come from Settings (env vars), NOT from user text input; sidebar radio has fixed options |
| API key exposure in comparison results | Information Disclosure | Never log or display API key; response objects don't contain it |
| Denial of Service via repeated comparisons | Denial of Service | Existing NIMClient retry/backoff + rate limit from NVIDIA side; no additional mitigation needed for POC |

## Project Constraints (from copilot-instructions.md)

- **Pure-function router:** `route(task, signals) → RouteDecision(model, reason)` — no I/O in the router [CITED: copilot-instructions.md]
- **`asyncio.gather` for parallel calls:** Comparison panel must use asyncio.gather [CITED: copilot-instructions.md]
- **Caching disabled in comparison panel:** Identical inputs except model [CITED: copilot-instructions.md]
- **"Concept demo, not benchmark" disclaimer:** Required in comparison UI [CITED: copilot-instructions.md]
- **`@st.cache_resource` for heavy resources:** NIMClient, etc. must remain cached [CITED: copilot-instructions.md]
- **Env-configurable fallback model:** `NVIDIA_ROUTE_MODEL` already in Settings [VERIFIED: core/config.py]
- **Dataclass-based results:** Follow QueryResult/SummaryResult/GraphResult pattern [VERIFIED: codebase]
- **Temperature 0.3 for grounded Q&A:** Consistent across both comparison models [VERIFIED: pipelines/query.py]

## Sources

### Primary (HIGH confidence)
- `core/config.py` — Settings class with `nvidia_route_model = "meta/llama-3.1-8b-instruct"` [VERIFIED: codebase]
- `core/llm_client.py` — NIMClient with chat() model override, retry/backoff, 60s timeout [VERIFIED: codebase]
- `pipelines/query.py` — QueryResult dataclass, run_query() pattern, citation validation [VERIFIED: codebase]
- `pipelines/graph.py`, `pipelines/summarize.py` — Existing pipeline patterns for extension [VERIFIED: codebase]
- OpenAI Python SDK README — `AsyncOpenAI`, `response.usage`, `chat.completions.create()` [CITED: github.com/openai/openai-python]
- Python stdlib docs — `asyncio.run()`, `asyncio.gather()`, `concurrent.futures.ThreadPoolExecutor`, `time.perf_counter()` [CITED: docs.python.org]

### Secondary (MEDIUM confidence)
- Streamlit architecture docs — Tornado-based server, script execution in separate thread [CITED: docs.streamlit.io]
- OpenAI API reference — ChatCompletion response object with `usage` field [CITED: developers.openai.com]
- NVIDIA NIM build.nvidia.com — Model catalog, free-tier endpoints [CITED: build.nvidia.com]

### Tertiary (LOW confidence)
- NVIDIA free-tier rate limits — community-reported ~10K calls/month; no official documentation found [ASSUMED]
- NIM response.usage field consistency across all models — likely but not officially verified [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all patterns verified in codebase
- Architecture: HIGH — pure composition over existing NIMClient/pipelines/Streamlit patterns
- Pitfalls: HIGH — each pitfall has a concrete prevention strategy and fallback
- Async/parallel execution: MEDIUM — asyncio.run() in Streamlit is well-reasoned but A3 is assumed
- NVIDIA rate limits: LOW — exact limits not publicly documented

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (30 days — stable patterns, no fast-moving dependencies)

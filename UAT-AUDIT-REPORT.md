# DocBot — UAT Audit Report

**Date:** 2025-01-20  
**Test Document:** `test docs/raft.pdf` (0.5MB, 18 pages, 79 chunks)  
**Environment:** Streamlit on localhost:8501, NVIDIA NIM API, ChromaDB persistent store  
**Models:** `meta/llama-3.1-70b-instruct` (large), `meta/llama-3.1-8b-instruct` (small)

---

## Summary

| Area | Status | Findings |
|------|--------|----------|
| Upload | ✅ PASS | Works correctly, progress shown |
| Chat | ⚠️ PARTIAL | Functional but UX issues (citations, routing) |
| Summary | ❌ BLOCKED | 429 rate limit; error handling masks specifics |
| Graph | ❌ BLOCKED | Timeout/rate limit; not testable |
| Compare | ✅ PASS | Side-by-side works |
| Sidebar | ⚠️ PARTIAL | Delete works; no session persistence |
| Sample Loader | ❌ FAIL | No sample PDFs bundled |

---

## Findings

### CRITICAL

#### F1 — No Session Persistence
**Severity:** Critical  
**Component:** `ui/upload.py`, `app.py`  
**Description:** After a page reload, the sidebar reverts to "No documents indexed yet" even though documents exist in ChromaDB. All session state (indexed docs, chat history) is lost. There is no startup scan of the ChromaDB collection to restore previously indexed documents.  
**Steps to Reproduce:** Upload a PDF → verify it appears in sidebar → reload the page (F5).  
**Impact:** Users lose all context on every page refresh — a common Streamlit behavior.  
**Recommendation:** On app startup, scan ChromaDB for existing documents and populate `st.session_state` accordingly.

#### F7 — Generic Exception Swallows Specific API Errors
**Severity:** Critical  
**Component:** `pipelines/summarize.py` (and likely `pipelines/graph.py`, `pipelines/query.py`)  
**Description:** The pipeline's `except Exception` catch-all swallows specific OpenAI errors (e.g., `RateLimitError`, `APITimeoutError`) before they reach the UI-level handlers in `ui/summary_view.py`. The user sees a raw error dict instead of a friendly, actionable message.  
**Steps to Reproduce:** Trigger a 429 rate limit on the Summary tab → observe raw error string in UI.  
**Impact:** Users cannot distinguish transient rate limits from permanent failures.  
**Recommendation:** Re-raise `openai.RateLimitError` and `openai.APITimeoutError` from pipelines, or return a typed error result that the UI can pattern-match on.

---

### HIGH

#### F2 — Sidebar Doesn't Update After Upload Until Rerun
**Severity:** High  
**Component:** `app.py` render order  
**Description:** The sidebar renders before the upload handler processes the file. The sidebar only shows the new document on the next Streamlit rerun cycle.  
**Steps to Reproduce:** Upload a PDF → sidebar still shows previous state until next interaction.

#### F5 — Route Reason Always Shows "0 chars, 0 chunks"
**Severity:** High  
**Component:** `routers/model_router.py`, all callers  
**Description:** The `route()` function accepts `doc_length` and `chunk_count` parameters, but no caller ever passes them. Every route decision shows "0 chars, 0 chunks" regardless of actual query/document size. This makes the routing intelligence ineffective — everything defaults to the small model (except graph extraction).  
**Steps to Reproduce:** Ask any chat question → observe route reason: "Short qa task (0 chars, 0 chunks)".  
**Recommendation:** Pass actual query length and chunk count from `ui/chat.py`, `ui/summary_view.py`, etc.

#### F8 — Summarize Error Sets chunk_count=0 Incorrectly
**Severity:** High  
**Component:** `pipelines/summarize.py`  
**Description:** When the LLM call fails after chunks were successfully retrieved, the error handler sets `chunk_count=0` in the result dict, misrepresenting that chunking failed. The UI then shows "Chunks: 0" even though chunks were loaded.  
**Steps to Reproduce:** Trigger a summary on a large doc when the API is rate-limited → observe "Chunks: 0" in the error details.

#### F16 — Duplicate Tab Sets on Rerun After Button Click
**Severity:** High  
**Component:** `app.py` layout  
**Description:** When a button click (e.g., Summarize) triggers a Streamlit rerun while a file is still in the upload widget, the page renders two complete sets of tab bars. The first shows Chat (default), the second shows the tab that was active. This creates a confusing, broken layout.  
**Steps to Reproduce:** Upload a PDF → go to Summary tab → click Summarize → observe two tab bars.

---

### MEDIUM

#### F3 — Citation IDs Are Raw Content Hashes
**Severity:** Medium  
**Component:** `ui/chat.py`  
**Description:** Source citations display raw SHA-256 chunk IDs like `[5a5c679b6a7c88007faeff8c3eef19a77e9e5caa8bd7390922584fe8ecf0ce1f_chunk_18]` instead of user-friendly labels like `[1]`, `[2]`.  
**Steps to Reproduce:** Ask any question in Chat → expand Sources section.  
**Recommendation:** Map chunk IDs to sequential integers in the response and citation list.

#### F4 — Duplicate Source Citations
**Severity:** Medium  
**Component:** `ui/chat.py`, `core/retriever.py`  
**Description:** The same chunk appears multiple times in the citation list. E.g., `chunk_18 — page 5` appears 3 times, `chunk_1 — page 1` appears 2 times.  
**Steps to Reproduce:** Ask "What is RAFT and how does it work?" → count citations.  
**Recommendation:** Deduplicate citations by chunk ID before rendering.

#### F6 — Summarization Blocked by Rate Limiting
**Severity:** Medium  
**Component:** `pipelines/summarize.py`  
**Description:** All 5 summarization attempts returned HTTP 429 (Too Many Requests). No retry with exponential backoff is implemented despite the project spec requiring it.  
**Steps to Reproduce:** Run summarization shortly after other API calls.  
**Recommendation:** Implement exponential backoff with jitter on 429/504 as specified in the project hard rules.

#### F11 — Graph Extraction Timeout
**Severity:** Medium  
**Component:** `pipelines/graph.py`  
**Description:** Graph extraction timed out with "Request timed out". Graph extraction always routes to the large model, which is more prone to rate limiting.  
**Steps to Reproduce:** Click Extract Graph on the Graph tab.

#### F13 — Chat History References Deleted Document Chunks
**Severity:** Medium  
**Component:** `ui/chat.py`  
**Description:** After deleting a document via sidebar, the chat history still displays previous Q&A messages with chunk references to the deleted document. Expanding these citations would reference non-existent chunks.  
**Steps to Reproduce:** Chat about a doc → delete it via sidebar → observe stale chat messages.  
**Recommendation:** Clear chat history when a document is deleted, or add a disclaimer.

---

### LOW

#### F9 — Summary Pipeline chunk_count Metadata Bug
**Severity:** Low  
**Component:** `pipelines/summarize.py`  
**Description:** In the error branch, `chunk_count` is set to `0` even when chunks were successfully loaded. This is a metadata accuracy issue.

#### F12 — Comparison Headers May Scroll Off-Screen
**Severity:** Low  
**Component:** `ui/comparison.py`  
**Description:** On small viewports, the side-by-side model comparison headers (model names) may scroll out of view while reading long responses.

#### F14 — Tab Resets to Chat After Delete
**Severity:** Low  
**Component:** `app.py`  
**Description:** After clicking the delete button on the sidebar, the active tab resets to Chat regardless of which tab the user was on.

#### F15 — No Sample PDFs Bundled
**Severity:** Low  
**Component:** `data/samples/`  
**Description:** The project layout specifies "bundled sample PDFs (committed)" but `data/samples/` contains only `.gitkeep` and `README.md`. The sample loader section never appears in the UI.  
**Recommendation:** Add at least one sample PDF for demo purposes.

#### F17 — "Upload a document first" After Reload Despite Indexed Docs
**Severity:** Low (consequence of F1)  
**Component:** `ui/summary_view.py`  
**Description:** Summary, Graph, and Compare tabs all show "Upload a document first" after a page reload, even though documents are indexed in ChromaDB. This is a downstream effect of F1 (no session persistence).

---

## Features Verified Working

| Feature | Details |
|---------|---------|
| PDF Upload | raft.pdf uploaded successfully; 18 pages extracted, 79 chunks indexed |
| Upload Progress | Step-by-step progress (saving, extracting, chunking, embedding) displayed |
| Duplicate Detection | Re-uploading same file shows "raft.pdf is already indexed" |
| Chat Q&A | Correct, grounded answers about RAFT consensus algorithm |
| Chat History | Messages persist within a session (pre-reload) |
| Model Info Display | Model name, latency, token count shown per response |
| Route Reason Display | Routing explanation shown (though values are 0/0) |
| Compare Tab | Side-by-side model comparison with disclaimer banner works |
| Sidebar Delete | Document deletion removes from sidebar and ChromaDB |
| Sidebar Model Routing | Radio buttons (auto/small/large) work |

---

## Untestable (Rate Limited)

- **Summarization output quality** — all attempts returned 429
- **Graph extraction visualization** — timed out
- **Map-reduce summarization** — couldn't test direct vs. map_reduce behavior
- **Exponential backoff** — not implemented per findings

---

## Recommendations Priority

1. **Fix session persistence (F1)** — scan ChromaDB on startup
2. **Fix error propagation (F7)** — let specific API errors reach UI handlers
3. **Implement retry with backoff (F6)** — per project spec, 429/504 with jitter
4. **Pass routing params (F5)** — wire actual query/doc metrics to `route()`
5. **Deduplicate and simplify citations (F3, F4)**
6. **Fix duplicate tab rendering (F16)**
7. **Bundle sample PDFs (F15)**

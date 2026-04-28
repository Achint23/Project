# Phase 7: Demo Polish & End-to-End UX - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers **demo-readiness**: a presenter (or a fresh developer) can clone the repo, set up in ≤3 commands, and walk through the complete demo flow — upload → process → ask → summarize → extract graph → compare routing — in a single browser session, guided by comprehensive documentation. The demo dry-run and testing are **automated via Playwright** so the flow can be validated headlessly on any machine.

**Expanded scope (user-requested):**
- Detailed from-scratch installation documentation (README.md)
- Automated E2E demo dry-run and testing using Playwright browser automation

</domain>

<decisions>
## Implementation Decisions

### Documentation Structure & Depth
- **D-01:** README.md is the single source of truth for installation, configuration, running, and demo walkthrough. No separate docs/ folder — everything in one file for POC simplicity.
- **D-02:** README targets a developer on a **fresh Windows or macOS machine** with no prior project context. Prerequisites section lists Python 3.10–3.12, uv, git with install links.
- **D-03:** Step-by-step install: clone → `.\tasks.ps1 setup` → copy `.env.local.example` to `.env.local` and add API key → `.\tasks.ps1 run`. Include macOS/Linux equivalents.
- **D-04:** Full demo walkthrough section with numbered steps: (1) load sample doc, (2) watch processing, (3) ask a question in Chat tab, (4) request summary in Summary tab, (5) extract graph in Graph tab, (6) toggle routing and run comparison in Compare tab.
- **D-05:** Troubleshooting section covering: missing API key, EasyOCR weight download failures, ChromaDB permission errors, port conflicts, Python version mismatch.
- **D-06:** Architecture overview section with the project layout table from copilot-instructions.md — gives new developers a mental model.

### Automated E2E Testing with Playwright
- **D-07:** Use `pytest-playwright` Python package — stays in the existing pytest ecosystem, no Node.js test runner needed.
- **D-08:** Add `pytest-playwright` to `[dependency-groups] dev` in pyproject.toml.
- **D-09:** E2E test file: `tests/test_e2e_demo.py` covering the full demo flow as a single sequential test (upload → process → query → summarize → graph → compare).
- **D-10:** Tests run **headless by default**. Use `--headed` flag for visual demo presentations.
- **D-11:** The E2E test manages its own Streamlit server lifecycle: start Streamlit as a subprocess before tests, kill it after. Use a pytest fixture for this.
- **D-12:** Test assertions validate: (a) upload completes without error, (b) document appears in sidebar list, (c) chat response contains text (not empty/error), (d) summary tab produces output, (e) graph tab renders entities, (f) compare tab shows two results side-by-side.

### Demo Dry-Run Automation
- **D-13:** New `demo` command in `tasks.ps1` that: (1) starts Streamlit in background, (2) waits for server ready, (3) runs `pytest tests/test_e2e_demo.py`, (4) kills Streamlit, (5) reports pass/fail.
- **D-14:** The dry-run must pass on a fresh Windows machine with valid `.env.local` and the bundled `data/samples/` set.
- **D-15:** Playwright browser install step added to `tasks.ps1 setup` — `playwright install chromium` to pre-download browser binaries (similar pattern to EasyOCR weight pre-download).

### UI Polish (Flow Continuity)
- **D-16:** No new UI features. Polish focuses on single-session flow continuity — all tabs (Chat, Summary, Graph, Compare) work without page reloads after document upload.
- **D-17:** Verify existing error states surface via `st.error` (already implemented per QA-05 / UX-02). No new error handling unless E2E tests reveal gaps.
- **D-18:** Ensure sidebar document list updates immediately after upload/sample load without manual refresh.

### Agent's Discretion
- File structure within `tests/test_e2e_demo.py` (fixture organization, helper functions) — agent decides based on pytest-playwright best practices.
- Exact Playwright selectors for Streamlit elements — agent discovers during implementation based on rendered DOM.
- README formatting details (badge placement, screenshot inclusion) — agent decides based on standard open-source conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Setup & Configuration
- `.env.local.example` — Environment variable template (NVIDIA_API_KEY, models, base URL)
- `pyproject.toml` — Dependencies and build config
- `tasks.ps1` — Task runner with setup/run/clean/doctor/test commands
- `tasks.cmd` — Windows cmd wrapper for tasks.ps1
- `.streamlit/config.toml` — Streamlit server config (maxUploadSize=50, telemetry off)

### Application Entry Point
- `app.py` — Streamlit composition root (thin — imports and renders all UI partials)

### UI Partials (for Playwright selector discovery)
- `ui/upload.py` — Upload widget, sample loader, @st.cache_resource singletons
- `ui/sidebar.py` — Document list sidebar
- `ui/chat.py` — Chat tab with citations
- `ui/summary_view.py` — Summary tab
- `ui/graph_view.py` — Graph extraction tab (streamlit-agraph + mermaid)
- `ui/comparison.py` — Side-by-side routing comparison tab

### Existing Test Patterns
- `tests/` — All existing unit/integration tests (pytest conventions, conftest patterns)
- `tests/test_smoke_nim.py` — NIM connectivity smoke test (reference for integration test pattern)

### Data
- `data/samples/` — Bundled sample documents for demo
- `data/samples/README.md` — Sample set documentation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tasks.ps1` already has `setup`, `run`, `clean`, `doctor`, `test` commands — `demo` command extends this naturally
- `tests/test_smoke_nim.py` shows the integration test pattern (pytest markers, live API)
- `app.py` is a thin 40-line composition root — all UI in separate partials, easy to test via browser
- `@st.cache_resource` singletons in `ui/upload.py` (get_nim_client, get_ocr_reader, get_vectorstore)

### Established Patterns
- PowerShell task runner (`tasks.ps1`) with `tasks.cmd` wrapper for cmd.exe users
- pytest with `pytest-asyncio` for async tests — `pytest-playwright` follows the same plugin pattern
- `[dependency-groups] dev` in pyproject.toml for dev-only packages
- `data/samples/` for bundled test data

### Integration Points
- New `demo` command hooks into `tasks.ps1` alongside existing commands
- `pytest-playwright` integrates via pytest plugin — existing `conftest.py` patterns apply
- Streamlit app (`app.py`) is the system under test for E2E
- `.env.local` must be configured for E2E tests (real NIM API calls)

</code_context>

<specifics>
## Specific Ideas

- User explicitly requested Playwright for browser-based testing — not Selenium or other alternatives
- User wants the "agent" (Copilot) to use browser tools and Playwright to perform the demo dry-run and testing — both automated test creation AND execution during development
- Documentation should be detailed enough for someone with zero project context to go from clone to running demo
- The dry-run validates the complete flow, not just individual components

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 7-Demo Polish & End-to-End UX*
*Context gathered: 2026-04-28*

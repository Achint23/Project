---
phase: 07-demo-polish-e2e-ux
plan: 02
subsystem: testing/e2e
tags: [playwright, e2e, demo, task-runner]
dependency_graph:
  requires: [phase-06-complete, ui-partials, sample-documents]
  provides: [e2e-test-suite, demo-command]
  affects: [pyproject.toml, tasks.ps1, tests/]
tech_stack:
  added: [pytest-playwright]
  patterns: [playwright-server-fixture, headless-browser-testing, task-runner-lifecycle]
key_files:
  created:
    - tests/test_e2e_demo.py
  modified:
    - pyproject.toml
    - tasks.ps1
decisions:
  - pytest-playwright for E2E testing (stays in pytest ecosystem, no Node.js runner)
  - Streamlit server lifecycle managed in both fixture and tasks.ps1 demo command
  - Generous timeouts (60-90s) for NIM API-backed operations
  - Selectors derived from actual UI code (widget keys, button text, data-testid)
  - Playwright Chromium pre-downloaded during tasks.ps1 setup
metrics:
  duration: ~2m
  completed: 2026-04-28
---

# Phase 7 Plan 02: Playwright E2E Tests & Demo Command Summary

Playwright-based E2E test validating upload → chat → summary → graph → compare flow plus `demo` command in tasks.ps1

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add pytest-playwright dependency and update task runner | `e9e2356` | pyproject.toml, tasks.ps1 |
| 2 | Create E2E demo flow test | `6a52c77` | tests/test_e2e_demo.py |

## What Was Built

### Task 1: pytest-playwright + demo command
- Added `pytest-playwright>=0.5` to `[dependency-groups] dev` in pyproject.toml
- Added `demo` to tasks.ps1 `ValidateSet` and created `Invoke-Demo` function
- `Invoke-Demo` manages full Streamlit server lifecycle: start → health-check wait (30s timeout) → run E2E pytest → kill server → report pass/fail
- Added `playwright install chromium` step to `Invoke-Setup` for browser pre-download
- Updated `Show-Help` with demo command description

### Task 2: E2E demo flow test
- Created `tests/test_e2e_demo.py` with module-scoped `streamlit_server` fixture
- Single sequential test `test_e2e_demo_flow` covering complete demo:
  1. Load sample document via "Load" button
  2. Verify document appears in sidebar (`.pdf` text match)
  3. Chat tab: ask question, verify non-empty response (>10 chars)
  4. Summary tab: click "Summarize", verify output with "Method:/Chunks:" pattern
  5. Graph tab: click "Extract Graph", verify "Entities:/Chunks:" output
  6. Compare tab: fill question, click "Compare Models", verify 2 Latency metrics
- Selectors derived from actual UI code: `st.button("📝 Summarize")`, `st.button("🔍 Extract Graph")`, `st.button("🔄 Compare Models")`, etc.
- Marked with `pytest.mark.integration` (requires live NIM API)
- Generous timeouts: 60s for chat/upload, 90s for summary/graph/compare

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- pyproject.toml contains `pytest-playwright>=0.5` ✓
- tasks.ps1 has `Invoke-Demo`, `demo` in ValidateSet, `playwright install chromium` in setup ✓
- tests/test_e2e_demo.py parses, contains `test_e2e_demo_flow` and `streamlit_server` ✓
- All 151 existing unit tests pass (no regressions) ✓

## Self-Check: PASSED

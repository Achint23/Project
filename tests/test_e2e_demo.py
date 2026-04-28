"""End-to-end Playwright test covering the full DocBot demo flow.

Validates: upload → chat → summary → graph → compare in a single browser session.
Requires: live NVIDIA NIM API (.env.local configured), sample PDFs in data/samples/.
"""

from __future__ import annotations

import re
import subprocess
import time
import urllib.request

import pytest
from playwright.sync_api import Page, expect

STREAMLIT_URL = "http://localhost:8501"
SERVER_TIMEOUT = 30

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def streamlit_server():
    """Start Streamlit server for E2E tests, kill after module completes."""
    proc = subprocess.Popen(
        ["uv", "run", "streamlit", "run", "app.py", "--server.headless", "true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(SERVER_TIMEOUT):
        try:
            resp = urllib.request.urlopen(
                f"{STREAMLIT_URL}/_stcore/health", timeout=2
            )
            if resp.status == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        proc.kill()
        pytest.fail("Streamlit server failed to start within timeout")
    yield proc
    proc.kill()
    proc.wait()


def test_e2e_demo_flow(streamlit_server, page: Page):
    """Full demo flow: load sample → chat → summarize → graph → compare."""
    page.goto(STREAMLIT_URL)
    page.wait_for_load_state("networkidle")

    # ── Step 1: Load a sample document ──────────────────────────────
    # render_sample_loader uses st.button("Load", key=f"sample_{name}")
    sample_button = page.get_by_role("button", name="Load").first
    expect(sample_button).to_be_visible(timeout=10000)
    sample_button.click()

    # Wait for processing (upload + extraction + embedding)
    # Success message pattern: "**name.pdf** indexed: N pages, N chunks."
    expect(
        page.locator("text=/indexed.*pages.*chunks/i")
    ).to_be_visible(timeout=60000)

    # ── Step 2: Verify document appears in sidebar ──────────────────
    sidebar = page.locator('[data-testid="stSidebar"]')
    expect(sidebar).to_contain_text(
        re.compile(r"\.pdf", re.IGNORECASE), timeout=10000
    )

    # ── Step 3: Chat tab — ask a question ───────────────────────────
    page.get_by_role("tab", name=re.compile("Chat")).click()
    page.wait_for_timeout(1000)

    chat_input = page.locator('textarea[data-testid="stChatInputTextArea"]')
    chat_input.fill("What is this document about?")
    chat_input.press("Enter")

    # Wait for assistant response
    messages = page.locator('[data-testid="stChatMessage"]')
    expect(messages.last).to_be_visible(timeout=60000)
    # Allow LLM time to stream the response
    page.wait_for_timeout(15000)
    response_text = messages.last.inner_text()
    assert len(response_text) > 10, f"Chat response too short: {response_text!r}"

    # ── Step 4: Summary tab ─────────────────────────────────────────
    page.get_by_role("tab", name=re.compile("Summary")).click()
    page.wait_for_timeout(1000)

    # render_summary_view uses st.button("📝 Summarize", key="summarize_btn")
    summarize_btn = page.get_by_role(
        "button", name=re.compile(r"Summarize", re.IGNORECASE)
    )
    expect(summarize_btn).to_be_visible(timeout=10000)
    summarize_btn.click()

    # Map-reduce summarization can be slow
    expect(
        page.locator("text=/Method:.*Chunks:/i")
    ).to_be_visible(timeout=90000)

    # ── Step 5: Graph tab ───────────────────────────────────────────
    page.get_by_role("tab", name=re.compile("Graph")).click()
    page.wait_for_timeout(1000)

    # render_graph_view uses st.button("🔍 Extract Graph", key="extract_btn")
    extract_btn = page.get_by_role(
        "button", name=re.compile(r"Extract Graph", re.IGNORECASE)
    )
    expect(extract_btn).to_be_visible(timeout=10000)
    extract_btn.click()

    # Graph extraction + dedup
    expect(
        page.locator("text=/Entities:.*Chunks:/i")
    ).to_be_visible(timeout=90000)

    # ── Step 6: Compare tab ─────────────────────────────────────────
    page.get_by_role("tab", name=re.compile("Compare")).click()
    page.wait_for_timeout(1000)

    # render_comparison uses st.text_input(..., key="compare_question")
    compare_input = page.locator('input[data-testid="stTextInput"]').last
    compare_input.fill("What is this document about?")

    # render_comparison uses st.button("🔄 Compare Models", key="compare_btn")
    compare_btn = page.get_by_role(
        "button", name=re.compile(r"Compare Models", re.IGNORECASE)
    )
    expect(compare_btn).to_be_visible(timeout=10000)
    compare_btn.click()

    # Parallel LLM calls — two columns rendered
    expect(
        page.locator("text=/Latency/i").first
    ).to_be_visible(timeout=90000)

    # Verify both model columns have content (two st.metric "Latency" labels)
    latency_metrics = page.locator("text=/Latency/i")
    assert latency_metrics.count() >= 2, (
        f"Expected 2 Latency metrics (both models), got {latency_metrics.count()}"
    )

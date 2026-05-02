"""Summary view partial — document summarization UI."""

from __future__ import annotations

import streamlit as st
import openai

from core.config import get_settings
from pipelines.summarize import SummaryResult, run_summarize
from routers.model_router import TaskType, route


def render_summary_view(vectorstore, nim_client) -> None:
    """Render the document summarization tab."""
    documents = st.session_state.get("documents", [])
    if not documents:
        st.info("Upload a document first to generate summaries.")
        return

    options = {doc["doc_id"]: doc["filename"] for doc in documents}
    selected_doc_id = st.selectbox(
        "Select document",
        options=list(options.keys()),
        format_func=lambda did: options[did],
        key="summary_doc_select",
    )

    if st.button("📝 Summarize", key="summarize_btn"):
        try:
            settings = get_settings()
            mode = st.session_state.get("model_routing_mode", "auto")
            route_reason = ""
            # Compute routing signals from selected document
            selected_doc = next((d for d in documents if d["doc_id"] == selected_doc_id), {})
            doc_chunk_count = selected_doc.get("chunk_count", 0)
            if mode == "small (route)":
                model = settings.nvidia_route_model
            elif mode == "large (direct)":
                model = settings.nvidia_model
            else:
                decision = route(TaskType.SUMMARY, settings.nvidia_model, settings.nvidia_route_model, chunk_count=doc_chunk_count)
                model = decision.model
                route_reason = decision.reason

            with st.status("Summarizing...", expanded=True) as status:
                result: SummaryResult = run_summarize(
                    selected_doc_id, vectorstore, nim_client, model=model
                )
                if result.error:
                    st.error(result.error)
                    status.update(label="Summarization failed", state="error")
                else:
                    status.update(label="Summary complete!", state="complete")
                st.caption(
                    f"Method: {result.method} | Chunks: {result.chunk_count}"
                )
                st.markdown(result.summary)
                st.caption(
                    f"🤖 {result.model_used or 'N/A'} | "
                    f"⏱️ {result.latency_ms:.0f}ms | "
                    f"📊 {result.prompt_tokens + result.completion_tokens} tokens"
                )
                if route_reason:
                    st.caption(f"🔀 {route_reason}")
        except openai.RateLimitError:
            st.error("Rate limit exceeded. Please wait a moment and try again.")
        except openai.AuthenticationError:
            st.error("Authentication failed. Check your NVIDIA API key.")
        except openai.APITimeoutError:
            st.error("Request timed out. The server may be overloaded — try again.")
        except openai.APIConnectionError:
            st.error("Connection error. Check your network and NVIDIA endpoint.")
        except openai.APIStatusError as exc:
            st.error(f"API error ({exc.status_code}): {exc.message}")

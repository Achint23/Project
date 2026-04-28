"""Summary view partial — document summarization UI."""

from __future__ import annotations

import streamlit as st
import openai

from pipelines.summarize import SummaryResult, run_summarize


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
            with st.status("Summarizing...", expanded=True) as status:
                result: SummaryResult = run_summarize(
                    selected_doc_id, vectorstore, nim_client
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

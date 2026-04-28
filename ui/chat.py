"""Chat UI with citation rendering, hallucination flags, and API error handling."""

from __future__ import annotations

import openai
import streamlit as st

from pipelines.query import QueryResult, run_query


def _init_chat():
    """Ensure session_state.chat_messages list exists."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


def _render_citations(citations: list[dict], hallucinated_ids: list[str]):
    """Render citation previews and hallucination warnings inside a chat message."""
    if not citations and not hallucinated_ids:
        return

    st.caption("📚 Sources:")
    for cite in citations:
        with st.expander(f"[{cite['chunk_id']}] — page {cite['page_num']}"):
            st.markdown(cite["text"])

    for hid in hallucinated_ids:
        st.warning(
            f"⚠️ **[{hid}]** — Citation not found in retrieved chunks (possibly hallucinated)"
        )


def render_chat(vectorstore, nim_client):
    """Render the Q&A chat interface with citation display and error handling."""
    _init_chat()

    st.subheader("💬 Ask a Question")

    # Replay chat history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "citations" in msg:
                _render_citations(msg["citations"], msg.get("hallucinated_ids", []))

    # Accept new input
    question = st.chat_input("Ask a question about your documents")
    if question:
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.chat_messages.append({"role": "user", "content": question})

        with st.chat_message("assistant"):
            try:
                result = run_query(question, vectorstore, nim_client)
            except openai.RateLimitError:
                err = "⚠️ NVIDIA API rate limit reached. Please wait a moment and try again."
                st.error(err)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": err}
                )
                return
            except openai.APITimeoutError:
                err = "⚠️ NVIDIA API request timed out. The model may be under heavy load — try again."
                st.error(err)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": err}
                )
                return
            except openai.AuthenticationError:
                err = "🔑 NVIDIA API authentication failed. Check your NVIDIA_API_KEY in .env.local."
                st.error(err)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": err}
                )
                return
            except openai.APIStatusError as e:
                err = f"⚠️ NVIDIA API error (HTTP {e.status_code}): {e.message}"
                st.error(err)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": err}
                )
                return
            except openai.APIConnectionError:
                err = "🌐 Could not connect to NVIDIA API. Check your network connection."
                st.error(err)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": err}
                )
                return

            st.markdown(result.answer)
            _render_citations(result.citations, result.hallucinated_ids)
            st.session_state.chat_messages.append(
                {
                    "role": "assistant",
                    "content": result.answer,
                    "citations": result.citations,
                    "hallucinated_ids": result.hallucinated_ids,
                }
            )

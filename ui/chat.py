"""Chat UI with citation rendering, hallucination flags, and API error handling."""

from __future__ import annotations

import openai
import streamlit as st

from core.config import get_settings
from pipelines.query import QueryResult, run_query
from routers.model_router import TaskType, route


def _resolve_model(task: TaskType, doc_length: int = 0, chunk_count: int = 0) -> tuple[str, str]:
    """Resolve model name and route reason from session routing mode.

    Returns (model_name, route_reason).
    """
    settings = get_settings()
    mode = st.session_state.get("model_routing_mode", "auto")
    if mode == "small (route)":
        return settings.nvidia_route_model, ""
    if mode == "large (direct)":
        return settings.nvidia_model, ""
    decision = route(task, settings.nvidia_model, settings.nvidia_route_model, doc_length=doc_length, chunk_count=chunk_count)
    return decision.model, decision.reason


def _init_chat():
    """Ensure session_state.chat_messages list exists."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


def _render_citations(citations: list[dict], hallucinated_ids: list[str]):
    """Render citation previews and hallucination warnings inside a chat message."""
    if not citations and not hallucinated_ids:
        return

    st.caption("📚 Sources:")
    for idx, cite in enumerate(citations, start=1):
        with st.expander(f"[{idx}] — page {cite['page_num']}"):
            st.markdown(cite["text"])

    for hid in hallucinated_ids:
        st.warning(
            f"⚠️ Citation not found in retrieved chunks (possibly hallucinated)"
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
                if msg.get("metadata"):
                    st.caption(msg["metadata"])
                if msg.get("route_reason"):
                    st.caption(f"🔀 {msg['route_reason']}")

    # Accept new input
    question = st.chat_input("Ask a question about your documents")
    if question:
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.chat_messages.append({"role": "user", "content": question})

        with st.chat_message("assistant"):
            try:
                # Compute routing signals from indexed documents
                documents = st.session_state.get("documents", [])
                total_chunks = sum(d.get("chunk_count", 0) for d in documents)
                model, route_reason = _resolve_model(TaskType.QA, doc_length=len(question), chunk_count=total_chunks)
                result = run_query(question, vectorstore, nim_client, model=model)
                result.route_reason = route_reason
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

            metadata_str = (
                f"🤖 {result.model_used or 'N/A'} | "
                f"⏱️ {result.latency_ms:.0f}ms | "
                f"📊 {result.prompt_tokens + result.completion_tokens} tokens"
            )
            st.caption(metadata_str)
            if result.route_reason:
                st.caption(f"🔀 {result.route_reason}")

            st.session_state.chat_messages.append(
                {
                    "role": "assistant",
                    "content": result.answer,
                    "citations": result.citations,
                    "hallucinated_ids": result.hallucinated_ids,
                    "metadata": metadata_str,
                    "route_reason": result.route_reason,
                }
            )

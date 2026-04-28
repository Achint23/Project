"""Side-by-side model comparison panel UI."""

from __future__ import annotations

import openai
import streamlit as st

from core.config import get_settings
from pipelines.compare import ComparisonResult, run_comparison


def render_comparison(vectorstore, nim_client) -> None:
    """Render the side-by-side model comparison tab."""
    documents = st.session_state.get("documents", [])
    if not documents:
        st.info("Upload a document first to compare models.")
        return

    question = st.text_input(
        "Ask a question to compare models", key="compare_question"
    )

    if st.button("🔄 Compare Models", key="compare_btn") and question.strip():
        st.info(
            "⚠️ **Concept demo, not benchmark.** Results may vary between runs "
            "due to model non-determinism and network conditions."
        )

        settings = get_settings()

        try:
            with st.spinner("Running parallel comparison..."):
                result: ComparisonResult = run_comparison(
                    question,
                    vectorstore,
                    nim_client,
                    large_model=settings.nvidia_model,
                    small_model=settings.nvidia_route_model,
                )

            col_large, col_small = st.columns(2)

            with col_large:
                st.subheader(f"🔵 {settings.nvidia_model}")
                r = result.result_large
                if r.answer:
                    st.metric("Latency", f"{r.latency_ms:.0f} ms")
                    st.metric("Tokens", r.prompt_tokens + r.completion_tokens)
                    st.markdown(r.answer)
                else:
                    st.error("Large model returned no answer.")

            with col_small:
                st.subheader(f"🟢 {settings.nvidia_route_model}")
                r = result.result_small
                if r.answer:
                    st.metric("Latency", f"{r.latency_ms:.0f} ms")
                    st.metric("Tokens", r.prompt_tokens + r.completion_tokens)
                    st.markdown(r.answer)
                else:
                    st.error("Route model returned no answer.")

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

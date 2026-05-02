"""Graph view partial — entity/relationship extraction and visualization UI."""

from __future__ import annotations

import streamlit as st
import pandas as pd
import openai

from core.config import get_settings
from pipelines.graph import GraphExtraction, GraphResult, run_graph_extraction
from routers.model_router import TaskType, route
from streamlit_agraph import agraph, Node, Edge, Config

_TYPE_COLORS = {
    "PERSON": "#4CAF50",
    "ORG": "#2196F3",
    "PROCESS": "#FF9800",
    "SYSTEM": "#9C27B0",
    "CONCEPT": "#607D8B",
    "DOCUMENT": "#795548",
    "ROLE": "#00BCD4",
}


def _render_tables(extraction: GraphExtraction) -> None:
    """Render extraction results as data tables in tabs."""
    ent_tab, rel_tab, proc_tab, dec_tab, rule_tab = st.tabs(
        ["Entities", "Relationships", "Process Steps", "Decision Points", "Business Rules"]
    )

    sections = [
        (ent_tab, extraction.entities),
        (rel_tab, extraction.relationships),
        (proc_tab, extraction.process_steps),
        (dec_tab, extraction.decision_points),
        (rule_tab, extraction.business_rules),
    ]
    for tab, items in sections:
        with tab:
            if items:
                data = [item.model_dump() for item in items]
                st.dataframe(pd.DataFrame(data))
            else:
                st.info("None found.")


def _render_agraph(extraction: GraphExtraction) -> None:
    """Render an interactive node-edge graph using streamlit-agraph."""
    if not extraction.entities:
        st.info("No entities to visualize.")
        return

    nodes = [
        Node(
            id=e.name,
            label=e.name,
            size=25,
            color=_TYPE_COLORS.get(e.type, "#999"),
            title=f"{e.type}: {e.description}",
        )
        for e in extraction.entities
    ]
    edges = [
        Edge(
            source=r.source,
            target=r.target,
            label=r.relation,
            title=r.description,
        )
        for r in extraction.relationships
    ]
    config = Config(
        width=750,
        height=500,
        directed=True,
        physics=True,
        hierarchical=False,
        groups={},
    )
    agraph(nodes=nodes, edges=edges, config=config)


def _render_process_mermaid(process_steps: list) -> None:
    """Render process steps as a mermaid flowchart."""
    if not process_steps:
        return

    lines = ["flowchart TD"]
    for step in process_steps:
        step_id = f"S{step.step_number}"
        label = step.name or step.description[:40]
        lines.append(f"    {step_id}[{label}]")

    for i in range(len(process_steps) - 1):
        src = f"S{process_steps[i].step_number}"
        tgt = f"S{process_steps[i + 1].step_number}"
        lines.append(f"    {src} --> {tgt}")

    mermaid_str = "\n".join(lines)
    st.markdown(f"```mermaid\n{mermaid_str}\n```")


def render_graph_view(vectorstore, nim_client) -> None:
    """Render the graph extraction tab."""
    documents = st.session_state.get("documents", [])
    if not documents:
        st.info("Upload a document first to extract graph data.")
        return

    options = {doc["doc_id"]: doc["filename"] for doc in documents}
    selected_doc_id = st.selectbox(
        "Select document",
        options=list(options.keys()),
        format_func=lambda did: options[did],
        key="graph_doc_select",
    )

    if st.button("🔍 Extract Graph", key="extract_btn"):
        try:
            settings = get_settings()
            mode = st.session_state.get("model_routing_mode", "auto")
            selected_doc = next((d for d in documents if d["doc_id"] == selected_doc_id), {})
            doc_chunk_count = selected_doc.get("chunk_count", 0)
            if mode == "small (route)":
                model = settings.nvidia_route_model
            elif mode == "large (direct)":
                model = settings.nvidia_model
            else:
                decision = route(TaskType.GRAPH_EXTRACT, settings.nvidia_model, settings.nvidia_route_model, chunk_count=doc_chunk_count)
                model = decision.model

            with st.status("Extracting graph data...", expanded=True) as status:
                result: GraphResult = run_graph_extraction(
                    selected_doc_id, vectorstore, nim_client, model=model
                )
                if result.error:
                    st.error(result.error)
                    status.update(label="Extraction failed", state="error")
                    return
                status.update(label="Extraction complete!", state="complete")
                st.caption(
                    f"Entities: {result.entity_count} | "
                    f"Chunks: {result.chunk_count} | "
                    f"Dedup merges: {result.dedup_merges} | "
                    f"Method: {result.method}"
                )
                st.caption(
                    f"🤖 {result.model_used or 'N/A'} | "
                    f"⏱️ {result.latency_ms:.0f}ms | "
                    f"📊 {result.prompt_tokens + result.completion_tokens} tokens"
                )

            table_tab, graph_tab, process_tab = st.tabs(
                ["📊 Table View", "🕸️ Graph View", "📋 Process Flow"]
            )
            with table_tab:
                _render_tables(result.extraction)
            with graph_tab:
                _render_agraph(result.extraction)
            with process_tab:
                _render_process_mermaid(result.extraction.process_steps)

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

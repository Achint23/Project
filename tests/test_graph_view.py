"""Unit tests for ui/graph_view.py."""

from unittest.mock import MagicMock, patch

import pytest

from pipelines.graph import (
    BusinessRule,
    DecisionPoint,
    Entity,
    GraphExtraction,
    GraphResult,
    ProcessStep,
    Relationship,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_extraction() -> GraphExtraction:
    return GraphExtraction(
        entities=[
            Entity(name="Alice", type="PERSON", description="A person"),
            Entity(name="Acme Corp", type="ORG", description="A company"),
        ],
        relationships=[
            Relationship(source="Alice", target="Acme Corp", relation="works_at", description="Employment"),
        ],
        process_steps=[
            ProcessStep(step_number=1, name="Start", description="Begin process", actors=["Alice"]),
            ProcessStep(step_number=2, name="End", description="Finish process", actors=[]),
        ],
        decision_points=[],
        business_rules=[],
    )


def _make_graph_result(
    error: str | None = None,
    extraction: GraphExtraction | None = None,
) -> GraphResult:
    ext = extraction or _make_extraction()
    return GraphResult(
        extraction=ext,
        doc_id="abc123",
        chunk_count=5,
        entity_count=len(ext.entities),
        dedup_merges=0,
        method="single_pass",
        error=error,
    )


def _docs_list():
    return [
        {"doc_id": "abc123", "filename": "test.pdf"},
        {"doc_id": "def456", "filename": "other.pdf"},
    ]


# ---------------------------------------------------------------------------
# Tests: render_graph_view
# ---------------------------------------------------------------------------

class TestRenderGraphViewNoDocuments:
    def test_shows_info_when_no_documents(self):
        with patch("ui.graph_view.st") as mock_st:
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = []
            from ui.graph_view import render_graph_view
            render_graph_view(MagicMock(), MagicMock())
            mock_st.info.assert_called_once_with(
                "Upload a document first to extract graph data."
            )


class TestRenderGraphViewError:
    def test_shows_error_on_failure(self):
        result = _make_graph_result(error="NIM extraction failed")
        with patch("ui.graph_view.st") as mock_st, \
             patch("ui.graph_view.run_graph_extraction", return_value=result), \
             patch("ui.graph_view.get_settings") as mock_settings, \
             patch("ui.graph_view.route") as mock_route:
            mock_settings.return_value = MagicMock(nvidia_model="large", nvidia_route_model="small")
            mock_route.return_value = MagicMock(model="large", reason="test")
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = _docs_list()
            mock_st.selectbox.return_value = "abc123"
            mock_st.button.return_value = True

            mock_status = MagicMock()
            mock_status.__enter__ = MagicMock(return_value=mock_status)
            mock_status.__exit__ = MagicMock(return_value=False)
            mock_st.status.return_value = mock_status

            from ui.graph_view import render_graph_view
            render_graph_view(MagicMock(), MagicMock())

            mock_st.error.assert_called_once_with("NIM extraction failed")


class TestRenderGraphViewApiErrors:
    @pytest.mark.parametrize("exc_class,expected_msg", [
        ("RateLimitError", "Rate limit exceeded"),
        ("AuthenticationError", "Authentication failed"),
        ("APIConnectionError", "Connection error"),
        ("APITimeoutError", "Request timed out"),
    ])
    def test_openai_exceptions_show_st_error(self, exc_class, expected_msg):
        import openai
        exc = getattr(openai, exc_class)(
            message="test", response=MagicMock(), body=None
        ) if exc_class not in ("APIConnectionError", "APITimeoutError") else (
            getattr(openai, exc_class)(request=MagicMock())
        )

        with patch("ui.graph_view.st") as mock_st, \
             patch("ui.graph_view.run_graph_extraction", side_effect=exc), \
             patch("ui.graph_view.get_settings") as mock_settings, \
             patch("ui.graph_view.route") as mock_route:
            mock_settings.return_value = MagicMock(nvidia_model="large", nvidia_route_model="small")
            mock_route.return_value = MagicMock(model="large", reason="test")
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = _docs_list()
            mock_st.selectbox.return_value = "abc123"
            mock_st.button.return_value = True

            mock_status = MagicMock()
            mock_status.__enter__ = MagicMock(return_value=mock_status)
            mock_status.__exit__ = MagicMock(return_value=False)
            mock_st.status.return_value = mock_status

            from ui.graph_view import render_graph_view
            render_graph_view(MagicMock(), MagicMock())

            assert mock_st.error.called
            call_args = mock_st.error.call_args[0][0]
            assert expected_msg in call_args


# ---------------------------------------------------------------------------
# Tests: _render_tables
# ---------------------------------------------------------------------------

class TestRenderTables:
    def test_renders_dataframes_for_populated_extraction(self):
        extraction = _make_extraction()
        with patch("ui.graph_view.st") as mock_st, \
             patch("ui.graph_view.pd") as mock_pd:
            # Mock tabs
            tab_mocks = [MagicMock() for _ in range(5)]
            for t in tab_mocks:
                t.__enter__ = MagicMock(return_value=t)
                t.__exit__ = MagicMock(return_value=False)
            mock_st.tabs.return_value = tab_mocks

            from ui.graph_view import _render_tables
            _render_tables(extraction)

            # Should have called st.dataframe for entities and relationships
            assert mock_st.dataframe.called

    def test_shows_info_for_empty_sections(self):
        extraction = GraphExtraction()  # all empty
        with patch("ui.graph_view.st") as mock_st, \
             patch("ui.graph_view.pd") as mock_pd:
            tab_mocks = [MagicMock() for _ in range(5)]
            for t in tab_mocks:
                t.__enter__ = MagicMock(return_value=t)
                t.__exit__ = MagicMock(return_value=False)
            mock_st.tabs.return_value = tab_mocks

            from ui.graph_view import _render_tables
            _render_tables(extraction)

            # All 5 sections empty -> 5 st.info calls
            assert mock_st.info.call_count == 5


# ---------------------------------------------------------------------------
# Tests: _render_agraph
# ---------------------------------------------------------------------------

class TestRenderAgraph:
    def test_shows_info_when_no_entities(self):
        extraction = GraphExtraction()
        with patch("ui.graph_view.st") as mock_st:
            from ui.graph_view import _render_agraph
            _render_agraph(extraction)
            mock_st.info.assert_called_once_with("No entities to visualize.")

    def test_calls_agraph_with_nodes_and_edges(self):
        extraction = _make_extraction()
        with patch("ui.graph_view.st"), \
             patch("ui.graph_view.agraph") as mock_agraph:
            from ui.graph_view import _render_agraph
            _render_agraph(extraction)
            mock_agraph.assert_called_once()
            args = mock_agraph.call_args
            assert len(args.kwargs["nodes"]) == 2
            assert len(args.kwargs["edges"]) == 1


# ---------------------------------------------------------------------------
# Tests: _render_process_mermaid
# ---------------------------------------------------------------------------

class TestRenderProcessMermaid:
    def test_no_steps_returns_nothing(self):
        with patch("ui.graph_view.st") as mock_st:
            from ui.graph_view import _render_process_mermaid
            _render_process_mermaid([])
            mock_st.markdown.assert_not_called()

    def test_renders_mermaid_with_steps(self):
        steps = [
            ProcessStep(step_number=1, name="Start", description="Begin", actors=[]),
            ProcessStep(step_number=2, name="End", description="Finish", actors=[]),
        ]
        with patch("ui.graph_view.st") as mock_st:
            from ui.graph_view import _render_process_mermaid
            _render_process_mermaid(steps)
            mock_st.markdown.assert_called_once()
            mermaid_content = mock_st.markdown.call_args[0][0]
            assert "flowchart TD" in mermaid_content
            assert "S1[Start]" in mermaid_content
            assert "S2[End]" in mermaid_content
            assert "S1 --> S2" in mermaid_content

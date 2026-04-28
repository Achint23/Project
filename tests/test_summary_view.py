"""Unit tests for ui/summary_view.py."""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from pipelines.summarize import SummaryResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_summary_result(
    summary: str = "Test summary.",
    doc_id: str = "abc123",
    chunk_count: int = 3,
    method: str = "direct",
    error: str | None = None,
) -> SummaryResult:
    return SummaryResult(
        summary=summary,
        doc_id=doc_id,
        chunk_count=chunk_count,
        method=method,
        error=error,
    )


def _docs_list():
    return [
        {"doc_id": "abc123", "filename": "test.pdf"},
        {"doc_id": "def456", "filename": "other.pdf"},
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRenderSummaryViewNoDocuments:
    def test_shows_info_when_no_documents(self):
        with patch("ui.summary_view.st") as mock_st:
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = []
            from ui.summary_view import render_summary_view
            render_summary_view(MagicMock(), MagicMock())
            mock_st.info.assert_called_once_with(
                "Upload a document first to generate summaries."
            )


class TestRenderSummaryViewSuccess:
    def test_successful_summarization(self):
        result = _make_summary_result()
        with patch("ui.summary_view.st") as mock_st, \
             patch("ui.summary_view.run_summarize", return_value=result), \
             patch("ui.summary_view.get_settings") as mock_settings, \
             patch("ui.summary_view.route") as mock_route:
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

            from ui.summary_view import render_summary_view
            render_summary_view(MagicMock(), MagicMock())

            mock_status.update.assert_called_with(
                label="Summary complete!", state="complete"
            )
            mock_st.markdown.assert_called_once_with("Test summary.")


class TestRenderSummaryViewError:
    def test_shows_error_on_failure(self):
        result = _make_summary_result(error="No chunks found for document.")
        with patch("ui.summary_view.st") as mock_st, \
             patch("ui.summary_view.run_summarize", return_value=result), \
             patch("ui.summary_view.get_settings") as mock_settings, \
             patch("ui.summary_view.route") as mock_route:
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

            from ui.summary_view import render_summary_view
            render_summary_view(MagicMock(), MagicMock())

            mock_st.error.assert_called_once_with("No chunks found for document.")
            mock_status.update.assert_called_with(
                label="Summarization failed", state="error"
            )


class TestRenderSummaryViewApiErrors:
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

        with patch("ui.summary_view.st") as mock_st, \
             patch("ui.summary_view.run_summarize", side_effect=exc), \
             patch("ui.summary_view.get_settings") as mock_settings, \
             patch("ui.summary_view.route") as mock_route:
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

            from ui.summary_view import render_summary_view
            render_summary_view(MagicMock(), MagicMock())

            assert mock_st.error.called
            call_args = mock_st.error.call_args[0][0]
            assert expected_msg in call_args

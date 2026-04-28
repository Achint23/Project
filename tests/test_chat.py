"""Unit tests for ui/chat.py."""

from unittest.mock import MagicMock, patch

import pytest

from pipelines.query import QueryResult


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

class _SessionState:
    """Minimal mock for st.session_state supporting attribute + containment."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __contains__(self, key):
        return key in self.__dict__


def _make_query_result(
    answer: str = "Test answer [abc123_chunk_0].",
    citations: list | None = None,
    hallucinated_ids: list | None = None,
) -> QueryResult:
    return QueryResult(
        answer=answer,
        citations=citations or [
            {"chunk_id": "abc123_chunk_0", "text": "Source text", "page_num": 1, "chunk_type": "text"},
        ],
        hallucinated_ids=hallucinated_ids or [],
    )


# ---------------------------------------------------------------------------
# _init_chat tests
# ---------------------------------------------------------------------------

class TestInitChat:
    def test_creates_chat_messages_if_missing(self):
        mock_state = _SessionState()
        with patch("ui.chat.st") as mock_st:
            mock_st.session_state = mock_state
            from ui.chat import _init_chat
            _init_chat()
            assert "chat_messages" in mock_state
            assert mock_state.chat_messages == []

    def test_preserves_existing_chat_messages(self):
        existing = [{"role": "user", "content": "hello"}]
        mock_state = _SessionState(chat_messages=existing)
        with patch("ui.chat.st") as mock_st:
            mock_st.session_state = mock_state
            from ui.chat import _init_chat
            _init_chat()
            assert mock_state.chat_messages is existing


# ---------------------------------------------------------------------------
# _render_citations tests
# ---------------------------------------------------------------------------

class TestRenderCitations:
    def test_no_output_when_empty(self):
        with patch("ui.chat.st") as mock_st:
            from ui.chat import _render_citations
            _render_citations([], [])
            mock_st.caption.assert_not_called()

    def test_renders_valid_citations(self):
        citations = [
            {"chunk_id": "abc123_chunk_0", "text": "Source text", "page_num": 1, "chunk_type": "text"},
        ]
        with patch("ui.chat.st") as mock_st:
            expander_ctx = MagicMock()
            mock_st.expander.return_value.__enter__ = MagicMock(return_value=expander_ctx)
            mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

            from ui.chat import _render_citations
            _render_citations(citations, [])

            mock_st.caption.assert_called_once_with("📚 Sources:")
            mock_st.expander.assert_called_once_with("[abc123_chunk_0] — page 1")

    def test_renders_hallucination_warnings(self):
        with patch("ui.chat.st") as mock_st:
            from ui.chat import _render_citations
            _render_citations([], ["fake_chunk_99"])

            mock_st.caption.assert_called_once_with("📚 Sources:")
            mock_st.warning.assert_called_once()
            warning_text = mock_st.warning.call_args[0][0]
            assert "fake_chunk_99" in warning_text
            assert "possibly hallucinated" in warning_text


# ---------------------------------------------------------------------------
# render_chat error handling tests
# ---------------------------------------------------------------------------

class TestRenderChatErrorHandling:
    """Test that openai exceptions are caught and rendered as st.error."""

    def _setup_mocks(self, mock_st, question="What is this?"):
        """Configure Streamlit mocks for a single chat turn."""
        mock_st.session_state = _SessionState(chat_messages=[])
        mock_st.chat_input.return_value = question
        # Mock chat_message context managers
        user_ctx = MagicMock()
        user_ctx.__enter__ = MagicMock(return_value=user_ctx)
        user_ctx.__exit__ = MagicMock(return_value=False)
        assistant_ctx = MagicMock()
        assistant_ctx.__enter__ = MagicMock(return_value=assistant_ctx)
        assistant_ctx.__exit__ = MagicMock(return_value=False)
        mock_st.chat_message.side_effect = [user_ctx, assistant_ctx]

    @patch("ui.chat.run_query")
    @patch("ui.chat.st")
    def test_rate_limit_error(self, mock_st, mock_run_query):
        import openai
        self._setup_mocks(mock_st)
        mock_run_query.side_effect = openai.RateLimitError(
            message="rate limited", response=MagicMock(status_code=429), body=None
        )

        from ui.chat import render_chat
        render_chat(MagicMock(), MagicMock())

        mock_st.error.assert_called_once()
        assert "rate limit" in mock_st.error.call_args[0][0].lower()

    @patch("ui.chat.run_query")
    @patch("ui.chat.st")
    def test_timeout_error(self, mock_st, mock_run_query):
        import openai
        self._setup_mocks(mock_st)
        mock_run_query.side_effect = openai.APITimeoutError(request=MagicMock())

        from ui.chat import render_chat
        render_chat(MagicMock(), MagicMock())

        mock_st.error.assert_called_once()
        assert "timed out" in mock_st.error.call_args[0][0].lower()

    @patch("ui.chat.run_query")
    @patch("ui.chat.st")
    def test_auth_error(self, mock_st, mock_run_query):
        import openai
        self._setup_mocks(mock_st)
        mock_run_query.side_effect = openai.AuthenticationError(
            message="bad key", response=MagicMock(status_code=401), body=None
        )

        from ui.chat import render_chat
        render_chat(MagicMock(), MagicMock())

        mock_st.error.assert_called_once()
        assert "authentication" in mock_st.error.call_args[0][0].lower()

    @patch("ui.chat.run_query")
    @patch("ui.chat.st")
    def test_connection_error(self, mock_st, mock_run_query):
        import openai
        self._setup_mocks(mock_st)
        mock_run_query.side_effect = openai.APIConnectionError(request=MagicMock())

        from ui.chat import render_chat
        render_chat(MagicMock(), MagicMock())

        mock_st.error.assert_called_once()
        assert "connect" in mock_st.error.call_args[0][0].lower()

    @patch("ui.chat.run_query")
    @patch("ui.chat.st")
    def test_api_status_error(self, mock_st, mock_run_query):
        import openai
        self._setup_mocks(mock_st)
        resp = MagicMock()
        resp.status_code = 503
        mock_run_query.side_effect = openai.APIStatusError(
            message="service unavailable", response=resp, body=None
        )

        from ui.chat import render_chat
        render_chat(MagicMock(), MagicMock())

        mock_st.error.assert_called_once()
        assert "503" in mock_st.error.call_args[0][0]

    @patch("ui.chat.run_query")
    @patch("ui.chat.st")
    def test_error_appended_to_history(self, mock_st, mock_run_query):
        import openai
        self._setup_mocks(mock_st)
        mock_run_query.side_effect = openai.APIConnectionError(request=MagicMock())

        from ui.chat import render_chat
        render_chat(MagicMock(), MagicMock())

        messages = mock_st.session_state.chat_messages
        assert len(messages) == 2  # user + assistant error
        assert messages[1]["role"] == "assistant"


# ---------------------------------------------------------------------------
# render_chat success path tests
# ---------------------------------------------------------------------------

class TestRenderChatSuccess:
    @patch("ui.chat.run_query")
    @patch("ui.chat.st")
    def test_successful_query_appends_to_history(self, mock_st, mock_run_query):
        mock_st.session_state = _SessionState(chat_messages=[])
        mock_st.chat_input.return_value = "What is this?"

        user_ctx = MagicMock()
        user_ctx.__enter__ = MagicMock(return_value=user_ctx)
        user_ctx.__exit__ = MagicMock(return_value=False)
        assistant_ctx = MagicMock()
        assistant_ctx.__enter__ = MagicMock(return_value=assistant_ctx)
        assistant_ctx.__exit__ = MagicMock(return_value=False)
        mock_st.chat_message.side_effect = [user_ctx, assistant_ctx]

        result = _make_query_result()
        mock_run_query.return_value = result

        from ui.chat import render_chat
        render_chat(MagicMock(), MagicMock())

        messages = mock_st.session_state.chat_messages
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == result.answer
        assert messages[1]["citations"] == result.citations

    @patch("ui.chat.run_query")
    @patch("ui.chat.st")
    def test_no_question_does_not_call_query(self, mock_st, mock_run_query):
        mock_st.session_state = _SessionState(chat_messages=[])
        mock_st.chat_input.return_value = None

        from ui.chat import render_chat
        render_chat(MagicMock(), MagicMock())

        mock_run_query.assert_not_called()

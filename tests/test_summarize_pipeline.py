"""Tests for the summarization pipeline."""

from unittest.mock import MagicMock, patch

import pytest

from pipelines.summarize import (
    SummaryResult,
    TOKEN_BUDGET,
    _count_tokens,
    run_summarize,
)


def _make_mock_chat(return_text: str = "Mock summary", prompt_tokens: int = 0, completion_tokens: int = 0, model: str = ""):
    """Create a mock chat response object."""
    msg = MagicMock()
    msg.content = return_text
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    if prompt_tokens or completion_tokens:
        response.usage.prompt_tokens = prompt_tokens
        response.usage.completion_tokens = completion_tokens
        response.usage.total_tokens = prompt_tokens + completion_tokens
    else:
        response.usage = None
    response.model = model or None
    return response


class TestCountTokens:
    def test_returns_positive_integer(self):
        result = _count_tokens("Hello world, this is a test.")
        assert isinstance(result, int)
        assert result > 0

    def test_empty_string(self):
        result = _count_tokens("")
        assert result == 0

    def test_longer_text_more_tokens(self):
        short = _count_tokens("Hi")
        long = _count_tokens("This is a much longer sentence with many words in it.")
        assert long > short


class TestRunSummarizeNoChunks:
    def test_returns_error_when_no_chunks(self):
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = []
        mock_nim = MagicMock()

        result = run_summarize("doc123", mock_vs, mock_nim)

        assert isinstance(result, SummaryResult)
        assert result.error is not None
        assert "No chunks" in result.error
        assert result.chunk_count == 0
        mock_nim.chat.assert_not_called()


class TestRunSummarizeDirectPath:
    @patch("pipelines.summarize._count_tokens", return_value=100)
    def test_uses_direct_when_under_budget(self, mock_tokens):
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = [
            {"text": "Short chunk one.", "chunk_id": "c1", "doc_id": "doc1", "page_num": 1, "chunk_type": "text"},
            {"text": "Short chunk two.", "chunk_id": "c2", "doc_id": "doc1", "page_num": 1, "chunk_type": "text"},
        ]
        mock_nim = MagicMock()
        mock_nim.chat.return_value = _make_mock_chat("Direct summary result")

        result = run_summarize("doc1", mock_vs, mock_nim)

        assert result.method == "direct"
        assert result.summary == "Direct summary result"
        assert result.chunk_count == 2
        assert result.error is None
        # Direct path: exactly 1 chat call (reduce prompt)
        assert mock_nim.chat.call_count == 1


class TestRunSummarizeMapReducePath:
    @patch("pipelines.summarize._count_tokens", return_value=TOKEN_BUDGET + 1000)
    def test_uses_map_reduce_when_over_budget(self, mock_tokens):
        chunks = [
            {"text": f"Chunk {i} text content.", "chunk_id": f"c{i}", "doc_id": "doc2", "page_num": i, "chunk_type": "text"}
            for i in range(5)
        ]
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = chunks
        mock_nim = MagicMock()
        mock_nim.chat.return_value = _make_mock_chat("Map-reduce summary")

        result = run_summarize("doc2", mock_vs, mock_nim)

        assert result.method == "map_reduce"
        assert result.summary == "Map-reduce summary"
        assert result.chunk_count == 5
        assert result.error is None
        # Map-reduce: 5 map calls + 1 reduce call = 6 total
        assert mock_nim.chat.call_count == 6


class TestRunSummarizeErrorHandling:
    def test_returns_error_on_exception(self):
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = [
            {"text": "Some text.", "chunk_id": "c1", "doc_id": "doc3", "page_num": 1, "chunk_type": "text"},
        ]
        mock_nim = MagicMock()
        mock_nim.chat.side_effect = RuntimeError("API connection failed")

        result = run_summarize("doc3", mock_vs, mock_nim)

        assert isinstance(result, SummaryResult)
        assert result.error is not None
        assert "API connection failed" in result.error
        assert result.summary == ""


# ---------------------------------------------------------------------------
# Metadata extraction tests
# ---------------------------------------------------------------------------

class TestRunSummarizeMetadata:
    @patch("pipelines.summarize._count_tokens", return_value=100)
    def test_run_summarize_returns_metadata(self, mock_tokens):
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = [
            {"text": "Short chunk.", "chunk_id": "c1", "doc_id": "doc1", "page_num": 1, "chunk_type": "text"},
        ]
        mock_nim = MagicMock()
        mock_nim.chat.return_value = _make_mock_chat(
            "Summary.", prompt_tokens=80, completion_tokens=40, model="test-model"
        )

        result = run_summarize("doc1", mock_vs, mock_nim)

        assert result.model_used == "test-model"
        assert result.prompt_tokens == 80
        assert result.completion_tokens == 40
        assert result.latency_ms > 0

    @patch("pipelines.summarize._count_tokens", return_value=100)
    def test_run_summarize_with_explicit_model(self, mock_tokens):
        mock_vs = MagicMock()
        mock_vs.get_all_by_doc.return_value = [
            {"text": "Short chunk.", "chunk_id": "c1", "doc_id": "doc1", "page_num": 1, "chunk_type": "text"},
        ]
        mock_nim = MagicMock()
        mock_nim.chat.return_value = _make_mock_chat(
            "Summary.", prompt_tokens=10, completion_tokens=5, model="explicit-model"
        )

        run_summarize("doc1", mock_vs, mock_nim, model="explicit-model")

        call_kwargs = mock_nim.chat.call_args[1]
        assert call_kwargs["model"] == "explicit-model"
